import json
import os
import sys
from itertools import product

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.utils import resample
from torch import nn

try:
    # Optional performance utilities
    from ml.utils.perf import cpu_count, fast_read_csv, tune_environment, tune_torch_threads

    # Só configura se estiver executando diretamente (não durante import de testes)
    if __name__ == "__main__":
        tune_environment()
        tune_torch_threads()
        print(f"✓ Performance utils carregados. CPUs detectados: {cpu_count()}")
        # Log configuração de threads do ambiente
        print(f"✓ OMP_NUM_THREADS: {os.getenv('OMP_NUM_THREADS', 'não definido')}")
        print(f"✓ MKL_NUM_THREADS: {os.getenv('MKL_NUM_THREADS', 'não definido')}")
        print(f"✓ PYTORCH_NUM_THREADS: {os.getenv('PYTORCH_NUM_THREADS', 'não definido')}")
        print(f"✓ PyTorch threads: {torch.get_num_threads()}")
        print(f"✓ PyTorch interop threads: {torch.get_num_interop_threads()}")
except Exception as e:
    fast_read_csv = None  # type: ignore
    if __name__ == "__main__":
        print(f"⚠ Performance utils não disponíveis: {e}")

# Ensure project root is on sys.path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ml.models.informer import Informer


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona features técnicas ao dataframe de mercado.
    """
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["bb_ma20"] = df["close"].rolling(window=20).mean()
    df["bb_std20"] = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_ma20"] + 2 * df["bb_std20"]
    df["bb_lower"] = df["bb_ma20"] - 2 * df["bb_std20"]
    df["volatility_10"] = df["close"].rolling(window=10).std()
    df["volatility_20"] = df["close"].rolling(window=20).std()
    for lag in [1, 2, 3, 5, 10]:
        df[f"close_lag_{lag}"] = df["close"].shift(lag)
        df[f"volume_lag_{lag}"] = df["volume"].shift(lag)
    df["hour"] = pd.to_datetime(df["ts"]).dt.hour
    df["weekday"] = pd.to_datetime(df["ts"]).dt.weekday
    return df


def create_sequences(x: np.ndarray, y: np.ndarray, seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Cria sequências para modelos de séries temporais.
    Args:
        x: array de features
        y: array de targets
        seq_len: tamanho da janela
    Returns:
        tuple: (xs, ys) arrays de entrada e saída
    """
    xs, ys = [], []
    for i in range(len(x) - seq_len):
        xs.append(x[i : i + seq_len])
        ys.append(y[i + seq_len])
    return np.array(xs), np.array(ys)


# Grid de hiperparâmetros
PARAM_GRID = {
    "seq_len": [32, 64, 128],
    "d_model": [64, 128, 256],
    "e_layers": [2, 3, 4],
    "dropout": [0.1, 0.2, 0.3],
    "lr": [1e-3, 5e-4],
}

import multiprocessing as mp

from joblib import Parallel, delayed


def evaluate_config(
    X: np.ndarray,
    y: np.ndarray,
    seq_len: int,
    d_model: int,
    e_layers: int,
    dropout: float,
    lr: float,
):
    """
    Avalia uma configuração de hiperparâmetros.
    Configura threads do PyTorch para evitar oversubscription em ambiente paralelo.
    """
    # Dentro de cada worker, limitar threads para evitar contenção
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    print(
        f"\n=== Treinando: seq_len={seq_len}, d_model={d_model}, e_layers={e_layers}, dropout={dropout}, lr={lr} ==="
    )
    X_seq, y_seq = create_sequences(X, y, seq_len)
    n = len(X_seq)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)
    X_train, y_train = X_seq[:train_end], y_seq[:train_end]
    X_val, y_val = X_seq[train_end:val_end], y_seq[train_end:val_end]
    X_test, y_test = X_seq[val_end:], y_seq[val_end:]
    X_train = torch.tensor(X_train, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.float32)
    X_val = torch.tensor(X_val, dtype=torch.float32)
    y_val = torch.tensor(y_val, dtype=torch.float32)
    X_test = torch.tensor(X_test, dtype=torch.float32)
    y_test = torch.tensor(y_test, dtype=torch.float32)
    model = Informer(
        enc_in=X_train.shape[2],
        c_out=1,
        seq_len=seq_len,
        d_model=d_model,
        n_heads=4,
        e_layers=e_layers,
        d_ff=d_model * 2,
        dropout=dropout,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    loss_fn = nn.BCEWithLogitsLoss()
    best_val_loss = float("inf")
    patience = 2
    patience_counter = 0
    # Batch size menor por worker quando rodando em paralelo
    # Cada worker processa uma config; batch pequeno evita contenção de memória
    batch_size = int(os.getenv("BATCH_SIZE", "32"))
    for epoch in range(6):
        model.train()
        train_loss = 0
        for i in range(0, len(X_train), batch_size):
            xb = X_train[i : i + batch_size]
            yb = y_train[i : i + batch_size]
            optimizer.zero_grad()
            logits = model(xb).squeeze(-1)
            loss = loss_fn(logits, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        model.eval()
        with torch.no_grad():
            val_logits = model(X_val).squeeze(-1)
            val_loss = loss_fn(val_logits, y_val).item()
            val_probs = torch.sigmoid(val_logits).numpy()
            val_preds = (val_probs > 0.5).astype(int)
            val_precision = precision_score(y_val.numpy(), val_preds, zero_division=0)
            val_recall = recall_score(y_val.numpy(), val_preds, zero_division=0)
        print(
            f"Epoch {epoch+1}/6 | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Prec: {val_precision:.3f} | Rec: {val_recall:.3f}"
        )
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"✓ Early stopping na época {epoch+1}")
                break
    with torch.no_grad():
        test_logits = model(X_test).squeeze(-1)
        test_probs = torch.sigmoid(test_logits).numpy()
    test_preds_05 = (test_probs > 0.5).astype(int)
    y_test_np = y_test.numpy()
    precision_05 = precision_score(y_test_np, test_preds_05, zero_division=0)
    recall_05 = recall_score(y_test_np, test_preds_05, zero_division=0)
    auc = roc_auc_score(y_test_np, test_probs)
    print(f"Test Precision: {precision_05:.4f} | Recall: {recall_05:.4f} | AUC: {auc:.4f}")
    return {
        "seq_len": seq_len,
        "d_model": d_model,
        "e_layers": e_layers,
        "dropout": dropout,
        "lr": lr,
        "precision": float(precision_05),
        "recall": float(recall_05),
        "auc_roc": float(auc),
    }


def main():
    """Executa grid search de hiperparâmetros para o modelo Informer."""
    DATA_PATH = "ml/data/training_dataset.csv"
    TARGET_COL = "target_ret_1"

    # Carregar dados
    if callable(fast_read_csv):
        try:
            df = fast_read_csv(DATA_PATH)
        except Exception:
            df = pd.read_csv(DATA_PATH)
    else:
        df = pd.read_csv(DATA_PATH)

    df = add_features(df)
    df = df.dropna().reset_index(drop=True)
    drop_cols = ["ts"]
    numeric_cols = [c for c in df.select_dtypes(include=[np.number]).columns if c not in drop_cols]
    features = [c for c in numeric_cols if c != TARGET_COL]
    X = df[features].to_numpy()
    y_continuous = df[TARGET_COL].to_numpy(dtype=np.float32)
    y = (y_continuous > 0).astype(np.float32)

    # Oversample positivos
    X_pos = X[y == 1]
    y_pos = y[y == 1]
    X_neg = X[y == 0]
    y_neg = y[y == 0]
    X_pos_upsampled, y_pos_upsampled = resample(
        X_pos, y_pos, replace=True, n_samples=len(y_neg), random_state=42
    )
    X_bal = np.vstack([X_neg, X_pos_upsampled])
    y_bal = np.hstack([y_neg, y_pos_upsampled])
    idx = np.random.permutation(len(y_bal))
    X, y = X_bal[idx], y_bal[idx]

    # Normalização
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0) + 1e-8
    X = (X - X_mean) / X_std

    # Grid search
    param_list = list(
        product(
            PARAM_GRID["seq_len"],
            PARAM_GRID["d_model"],
            PARAM_GRID["e_layers"],
            PARAM_GRID["dropout"],
            PARAM_GRID["lr"],
        )
    )

    # Determinar número de jobs baseado em CPUs disponíveis
    n_jobs = int(os.getenv("N_JOBS", "-1"))
    if n_jobs == -1:
        n_jobs = mp.cpu_count()
        print(f"✓ Usando todos os {n_jobs} cores disponíveis para grid search")
    else:
        print(f"✓ Usando {n_jobs} cores para grid search (configurado via N_JOBS)")

    # Parallelize across CPU cores usando processes
    # prefer="processes" é crucial para contornar GIL do Python e utilizar todos os cores
    print(f"✓ Total de {len(param_list)} configurações a testar")
    print("✓ Iniciando grid search paralelo...")
    results = Parallel(n_jobs=n_jobs, prefer="processes", verbose=10)(
        delayed(evaluate_config)(X, y, *cfg) for cfg in param_list
    )

    print(f"\n{'='*80}")
    print(f"✓ Grid search concluído! {len(results)} configurações testadas.")
    print(f"{'='*80}")

    # Salvar resultados
    with open("ml/models/informer_gridsearch_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("✓ Resultados salvos em ml/models/informer_gridsearch_results.json")

    # Mostrar top 3 configurações
    sorted_results = sorted(results, key=lambda x: x.get("auc_roc", 0), reverse=True)
    print("\n🏆 Top 3 configurações por AUC-ROC:")
    for i, res in enumerate(sorted_results[:3], 1):
        print(
            f"{i}. seq_len={res['seq_len']}, d_model={res['d_model']}, "
            f"e_layers={res['e_layers']}, dropout={res['dropout']:.1f}, "
            f"lr={res['lr']:.0e} → AUC={res['auc_roc']:.4f}, "
            f"Prec={res['precision']:.4f}, Rec={res['recall']:.4f}"
        )


if __name__ == "__main__":
    main()
