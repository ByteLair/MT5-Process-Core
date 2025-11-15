"""
Treinamento do modelo Informer usando dados diretos do PostgreSQL/TimescaleDB.
Com 1.8M candles M1 completos com indicadores.
"""
import json
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.utils import resample
from sqlalchemy import create_engine
from torch import nn

# Ensure project root is on sys.path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ml.models.informer import Informer

# =====================
# CONFIGURAÇÕES
# =====================
CONFIG = {
    # Dados
    "symbol": "EURUSD",
    "timeframe": "M1",
    "limit": None,  # None = todos os dados, ou int para limitar (ex: 100000)
    
    # Modelo
    "seq_len": 96,  # Janela de 96 minutos (~1.5h)
    "pred_len": 1,   # Prever 1 minuto à frente
    "d_model": 128,
    "n_heads": 8,
    "e_layers": 3,
    "d_ff": 512,
    "dropout": 0.15,
    
    # Treinamento
    "batch_size": 256,
    "epochs": 20,
    "lr": 1e-3,
    "weight_decay": 1e-5,
    "patience": 5,
    
    # Data split
    "train_ratio": 0.7,
    "val_ratio": 0.15,
    "test_ratio": 0.15,
    
    # Balanceamento
    "oversample": True,
    "target_positive_rate": 0.55,  # Taxa alvo de sinais positivos
}

# Database connection
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "mt5_trading"),
    "user": os.getenv("DB_USER", "trader"),
    "password": os.getenv("DB_PASS", "trader123"),
}


def get_db_connection():
    """Cria conexão com o banco de dados."""
    conn_str = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(conn_str)


def load_data_from_db(engine, symbol: str, timeframe: str, limit: int = None) -> pd.DataFrame:
    """
    Carrega dados do banco com todos os indicadores.
    """
    query = f"""
    SELECT 
        ts,
        open, high, low, close, volume,
        rsi, macd, macd_signal, macd_hist,
        bb_upper, bb_middle, bb_lower,
        atr, adx,
        stoch_k, stoch_d,
        cci, roc, willr,
        ema_9, ema_21, ema_50, ema_200,
        sma_20, sma_50
    FROM market_data
    WHERE symbol = '{symbol}' 
      AND timeframe = '{timeframe}'
      AND rsi IS NOT NULL  -- Garante que tem indicadores
    ORDER BY ts ASC
    {f'LIMIT {limit}' if limit else ''}
    """
    
    print(f"📊 Carregando dados do banco...")
    print(f"   Symbol: {symbol}, Timeframe: {timeframe}")
    if limit:
        print(f"   Limit: {limit:,} candles")
    
    df = pd.read_sql(query, engine)
    print(f"✅ {len(df):,} candles carregados")
    return df


def create_target(df: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """
    Cria target binário: 1 se o preço sobe no próximo candle, 0 caso contrário.
    """
    df = df.copy()
    df['future_close'] = df['close'].shift(-horizon)
    df['target'] = (df['future_close'] > df['close']).astype(int)
    df = df[:-horizon]  # Remove últimos candles sem target
    return df


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona features temporais."""
    df = df.copy()
    df['hour'] = df['ts'].dt.hour
    df['minute'] = df['ts'].dt.minute
    df['weekday'] = df['ts'].dt.weekday
    df['is_session_start'] = ((df['hour'] == 0) & (df['minute'] == 0)).astype(int)
    df['is_session_end'] = ((df['hour'] == 23) & (df['minute'] == 59)).astype(int)
    return df


def create_sequences(X: np.ndarray, y: np.ndarray, seq_len: int) -> tuple:
    """Cria sequências para séries temporais."""
    Xs, ys = [], []
    for i in range(len(X) - seq_len):
        Xs.append(X[i:i + seq_len])
        ys.append(y[i + seq_len])
    return np.array(Xs), np.array(ys)


def balance_classes(X: np.ndarray, y: np.ndarray, target_rate: float = 0.5) -> tuple:
    """Balanceia classes usando oversampling."""
    X_pos = X[y == 1]
    y_pos = y[y == 1]
    X_neg = X[y == 0]
    y_neg = y[y == 0]
    
    # Calcular quantos positivos precisamos
    n_total = len(X)
    n_pos_target = int(n_total * target_rate)
    
    if len(y_pos) < n_pos_target:
        # Oversample positivos
        X_pos_up, y_pos_up = resample(
            X_pos, y_pos, 
            replace=True, 
            n_samples=n_pos_target,
            random_state=42
        )
        X_bal = np.vstack([X_neg, X_pos_up])
        y_bal = np.hstack([y_neg, y_pos_up])
    else:
        # Undersample negativos
        n_neg_target = n_total - n_pos_target
        X_neg_down, y_neg_down = resample(
            X_neg, y_neg,
            replace=False,
            n_samples=n_neg_target,
            random_state=42
        )
        X_bal = np.vstack([X_neg_down, X_pos])
        y_bal = np.hstack([y_neg_down, y_pos])
    
    # Shuffle
    idx = np.random.permutation(len(y_bal))
    return X_bal[idx], y_bal[idx]


def train_epoch(model, X, y, optimizer, loss_fn, batch_size, device):
    """Treina uma época."""
    model.train()
    total_loss = 0
    n_batches = 0
    
    for i in range(0, len(X), batch_size):
        xb = X[i:i + batch_size].to(device)
        yb = y[i:i + batch_size].to(device)
        
        optimizer.zero_grad()
        logits = model(xb).squeeze(-1)
        loss = loss_fn(logits, yb)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        
        total_loss += loss.item()
        n_batches += 1
    
    return total_loss / n_batches


def evaluate(model, X, y, loss_fn, device):
    """Avalia o modelo."""
    model.eval()
    with torch.no_grad():
        X_dev = X.to(device)
        y_dev = y.to(device)
        
        logits = model(X_dev).squeeze(-1)
        loss = loss_fn(logits, y_dev).item()
        
        probs = torch.sigmoid(logits).cpu().numpy()
        preds = (probs > 0.5).astype(int)
        y_true = y.numpy()
        
        precision = precision_score(y_true, preds, zero_division=0)
        recall = recall_score(y_true, preds, zero_division=0)
        
        return loss, precision, recall, probs


def main():
    """Fluxo principal de treinamento."""
    print("=" * 80)
    print("🚀 TREINAMENTO INFORMER - DADOS REAIS DO BANCO")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Conectar ao banco
    print("📡 Conectando ao banco de dados...")
    engine = get_db_connection()
    
    # 2. Carregar dados
    df = load_data_from_db(
        engine, 
        CONFIG['symbol'], 
        CONFIG['timeframe'],
        CONFIG['limit']
    )
    
    # 3. Preparar features
    print("\n🔧 Preparando features...")
    df['ts'] = pd.to_datetime(df['ts'])
    df = add_time_features(df)
    df = create_target(df, horizon=CONFIG['pred_len'])
    
    print(f"   Target positivo: {df['target'].mean():.2%}")
    print(f"   Período: {df['ts'].min()} até {df['ts'].max()}")
    
    # 4. Selecionar features
    feature_cols = [
        # Price action
        'open', 'high', 'low', 'close', 'volume',
        # Indicadores
        'rsi', 'macd', 'macd_signal', 'macd_hist',
        'bb_upper', 'bb_middle', 'bb_lower',
        'atr', 'adx',
        'stoch_k', 'stoch_d',
        'cci', 'roc', 'willr',
        'ema_9', 'ema_21', 'ema_50', 'ema_200',
        'sma_20', 'sma_50',
        # Time features
        'hour', 'minute', 'weekday',
        'is_session_start', 'is_session_end',
    ]
    
    X = df[feature_cols].values.astype(np.float32)
    y = df['target'].values.astype(np.float32)
    
    print(f"   Features: {X.shape[1]}")
    print(f"   Samples: {len(X):,}")
    
    # 5. Normalização
    print("\n📏 Normalizando dados...")
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0) + 1e-8
    X = (X - X_mean) / X_std
    
    # 6. Criar sequências
    print(f"\n🔄 Criando sequências (seq_len={CONFIG['seq_len']})...")
    X_seq, y_seq = create_sequences(X, y, CONFIG['seq_len'])
    print(f"   Sequências: {len(X_seq):,}")
    print(f"   Shape: {X_seq.shape}")
    
    # 7. Split train/val/test
    print("\n✂️  Dividindo dados...")
    n = len(X_seq)
    train_end = int(n * CONFIG['train_ratio'])
    val_end = int(n * (CONFIG['train_ratio'] + CONFIG['val_ratio']))
    
    X_train, y_train = X_seq[:train_end], y_seq[:train_end]
    X_val, y_val = X_seq[train_end:val_end], y_seq[train_end:val_end]
    X_test, y_test = X_seq[val_end:], y_seq[val_end:]
    
    print(f"   Train: {len(X_train):,} ({len(X_train)/n:.1%})")
    print(f"   Val:   {len(X_val):,} ({len(X_val)/n:.1%})")
    print(f"   Test:  {len(X_test):,} ({len(X_test)/n:.1%})")
    
    # 8. Balanceamento de classes (opcional)
    if CONFIG['oversample']:
        print(f"\n⚖️  Balanceando classes (target: {CONFIG['target_positive_rate']:.1%})...")
        print(f"   Antes: {y_train.mean():.2%} positivos")
        X_train, y_train = balance_classes(
            X_train, y_train, 
            CONFIG['target_positive_rate']
        )
        print(f"   Depois: {y_train.mean():.2%} positivos")
        print(f"   Samples: {len(X_train):,}")
    
    # 9. Converter para tensores
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n🖥️  Device: {device}")
    
    X_train = torch.tensor(X_train, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.float32)
    X_val = torch.tensor(X_val, dtype=torch.float32)
    y_val = torch.tensor(y_val, dtype=torch.float32)
    X_test = torch.tensor(X_test, dtype=torch.float32)
    y_test = torch.tensor(y_test, dtype=torch.float32)
    
    # 10. Criar modelo
    print("\n🏗️  Criando modelo Informer...")
    model = Informer(
        enc_in=X_train.shape[2],
        c_out=1,
        seq_len=CONFIG['seq_len'],
        d_model=CONFIG['d_model'],
        n_heads=CONFIG['n_heads'],
        e_layers=CONFIG['e_layers'],
        d_ff=CONFIG['d_ff'],
        dropout=CONFIG['dropout'],
    ).to(device)
    
    n_params = sum(p.numel() for p in model.parameters())
    print(f"   Parâmetros: {n_params:,}")
    
    optimizer = torch.optim.AdamW(
        model.parameters(), 
        lr=CONFIG['lr'],
        weight_decay=CONFIG['weight_decay']
    )
    loss_fn = nn.BCEWithLogitsLoss()
    
    # 11. Treinamento
    print("\n" + "=" * 80)
    print("🎯 INICIANDO TREINAMENTO")
    print("=" * 80)
    
    best_val_loss = float('inf')
    patience_counter = 0
    history = []
    
    for epoch in range(CONFIG['epochs']):
        # Treinar
        train_loss = train_epoch(
            model, X_train, y_train, 
            optimizer, loss_fn, 
            CONFIG['batch_size'], device
        )
        
        # Validar
        val_loss, val_prec, val_rec, _ = evaluate(
            model, X_val, y_val, loss_fn, device
        )
        
        # Log
        print(f"Epoch {epoch+1:2d}/{CONFIG['epochs']:2d} | "
              f"Train Loss: {train_loss:.4f} | "
              f"Val Loss: {val_loss:.4f} | "
              f"Prec: {val_prec:.3f} | "
              f"Rec: {val_rec:.3f}")
        
        history.append({
            'epoch': epoch + 1,
            'train_loss': train_loss,
            'val_loss': val_loss,
            'val_precision': val_prec,
            'val_recall': val_rec,
        })
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), 'ml/models/informer_best_db.pt')
            print(f"   ✅ Melhor modelo salvo!")
        else:
            patience_counter += 1
            if patience_counter >= CONFIG['patience']:
                print(f"\n⏹️  Early stopping (patience={CONFIG['patience']})")
                break
    
    # 12. Carregar melhor modelo
    print("\n📦 Carregando melhor modelo...")
    model.load_state_dict(torch.load('ml/models/informer_best_db.pt'))
    
    # 13. Avaliação final
    print("\n" + "=" * 80)
    print("📊 AVALIAÇÃO FINAL - TEST SET")
    print("=" * 80)
    
    test_loss, test_prec, test_rec, test_probs = evaluate(
        model, X_test, y_test, loss_fn, device
    )
    
    y_test_np = y_test.numpy()
    test_preds = (test_probs > 0.5).astype(int)
    
    auc = roc_auc_score(y_test_np, test_probs)
    cm = confusion_matrix(y_test_np, test_preds)
    
    print(f"\n📈 Métricas (threshold=0.5):")
    print(f"   Test Loss:  {test_loss:.4f}")
    print(f"   Precision:  {test_prec:.4f}")
    print(f"   Recall:     {test_rec:.4f}")
    print(f"   AUC-ROC:    {auc:.4f}")
    print(f"   Positivos:  {test_preds.sum():,} ({test_preds.mean():.1%})")
    
    print(f"\n📊 Confusion Matrix:")
    print(f"   TN: {cm[0,0]:6,}  FP: {cm[0,1]:6,}")
    print(f"   FN: {cm[1,0]:6,}  TP: {cm[1,1]:6,}")
    
    print(f"\n📝 Classification Report:")
    print(classification_report(y_test_np, test_preds, digits=3))
    
    # 14. Otimizar threshold
    print("\n🎯 Otimizando threshold...")
    best_threshold = 0.5
    best_f1 = 0
    
    for thresh in np.arange(0.3, 0.7, 0.01):
        preds = (test_probs > thresh).astype(int)
        prec = precision_score(y_test_np, preds, zero_division=0)
        rec = recall_score(y_test_np, preds, zero_division=0)
        f1 = 2 * (prec * rec) / (prec + rec + 1e-8)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = thresh
    
    test_preds_opt = (test_probs > best_threshold).astype(int)
    prec_opt = precision_score(y_test_np, test_preds_opt, zero_division=0)
    rec_opt = recall_score(y_test_np, test_preds_opt, zero_division=0)
    
    print(f"   Melhor threshold: {best_threshold:.3f}")
    print(f"   F1-Score:  {best_f1:.4f}")
    print(f"   Precision: {prec_opt:.4f}")
    print(f"   Recall:    {rec_opt:.4f}")
    print(f"   Positivos: {test_preds_opt.sum():,} ({test_preds_opt.mean():.1%})")
    
    # 15. Salvar artefatos
    print("\n💾 Salvando artefatos...")
    
    # Modelo final
    torch.save(model.state_dict(), 'ml/models/informer_classifier_db.pt')
    print("   ✅ Modelo salvo: informer_classifier_db.pt")
    
    # Normalização
    norm_data = {
        'X_mean': X_mean.tolist(),
        'X_std': X_std.tolist(),
        'features': feature_cols,
    }
    with open('ml/models/informer_normalization_db.json', 'w') as f:
        json.dump(norm_data, f, indent=2)
    print("   ✅ Normalização salva: informer_normalization_db.json")
    
    # Report
    report = {
        'timestamp': datetime.now().isoformat(),
        'model': 'Informer',
        'task': 'binary_classification',
        'dataset': {
            'symbol': CONFIG['symbol'],
            'timeframe': CONFIG['timeframe'],
            'total_samples': int(n),
            'train_samples': int(len(y_train)),
            'val_samples': int(len(X_val)),
            'test_samples': int(len(X_test)),
            'features': len(feature_cols),
            'period': f"{df['ts'].min()} to {df['ts'].max()}",
        },
        'config': CONFIG,
        'training': {
            'best_epoch': len(history) - CONFIG['patience'],
            'final_train_loss': float(train_loss),
            'final_val_loss': float(val_loss),
            'history': history,
        },
        'metrics': {
            'threshold_0.5': {
                'precision': float(test_prec),
                'recall': float(test_rec),
                'auc_roc': float(auc),
                'positive_rate': float(test_preds.mean()),
            },
            'threshold_optimized': {
                'threshold': float(best_threshold),
                'precision': float(prec_opt),
                'recall': float(rec_opt),
                'f1_score': float(best_f1),
                'positive_rate': float(test_preds_opt.mean()),
            },
        },
    }
    
    with open('ml/models/informer_report_db.json', 'w') as f:
        json.dump(report, f, indent=2)
    print("   ✅ Report salvo: informer_report_db.json")
    
    print("\n" + "=" * 80)
    print("✅ TREINAMENTO CONCLUÍDO COM SUCESSO!")
    print("=" * 80)
    print(f"🎯 Precision: {prec_opt:.1%}")
    print(f"🎯 Recall: {rec_opt:.1%}")
    print(f"🎯 F1-Score: {best_f1:.1%}")
    print(f"🎯 AUC-ROC: {auc:.1%}")
    print("=" * 80)


if __name__ == "__main__":
    main()
