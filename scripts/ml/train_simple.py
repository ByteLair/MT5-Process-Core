"""
Script simplificado de treinamento do Informer usando dados do banco.
Roda dentro do container mt5_api.
"""
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sqlalchemy import create_engine
import joblib

print("=" * 80)
print("🚀 TREINAMENTO MODELO ML - DADOS REAIS")
print("=" * 80)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Configuração
CONFIG = {
    "symbol": "EURUSD",
    "timeframe": "M1",
    "limit": 200000,  # Usar 200k candles para começar (mais rápido)
    "test_size": 0.2,
    "random_state": 42,
}

# Database
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "db"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "mt5_trading"),
    "user": os.getenv("DB_USER", "trader"),
    "password": os.getenv("DB_PASS", "trader123"),
}

def get_db_connection():
    """Cria conexão com o banco."""
    conn_str = (
        f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(conn_str)

def load_data_from_db(engine, symbol: str, timeframe: str, limit: int = None) -> pd.DataFrame:
    """Carrega dados do banco com todos os indicadores."""
    query = f"""
    SELECT 
        ts,
        open, high, low, close, volume,
        rsi, macd, macd_signal, macd_hist,
        bb_upper, bb_middle, bb_lower,
        atr
    FROM market_data
    WHERE symbol = '{symbol}' 
      AND timeframe = '{timeframe}'
      AND rsi IS NOT NULL
    ORDER BY ts ASC
    {f'LIMIT {limit}' if limit else ''}
    """
    
    print(f"📊 Carregando dados do banco...")
    print(f"   Symbol: {symbol}, Timeframe: {timeframe}")
    if limit:
        print(f"   Limit: {limit:,} candles")
    
    df = pd.read_sql(query, engine)
    print(f"✅ {len(df):,} candles carregados\n")
    return df

def create_target(df: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    """
    Cria target binário: 1 se preço sobe nos próximos N candles, 0 caso contrário.
    """
    df = df.copy()
    df['future_close'] = df['close'].shift(-horizon)
    df['price_change_pct'] = ((df['future_close'] - df['close']) / df['close']) * 100
    
    # Target: 1 se preço sobe mais que 0.01% (10 pips no EURUSD)
    df['target'] = (df['price_change_pct'] > 0.01).astype(int)
    
    # Remove últimos candles sem target
    df = df[:-horizon].copy()
    
    return df

def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona features temporais."""
    df = df.copy()
    df['ts'] = pd.to_datetime(df['ts'])
    df['hour'] = df['ts'].dt.hour
    df['minute'] = df['ts'].dt.minute
    df['weekday'] = df['ts'].dt.weekday
    
    # Sessions
    df['is_asian'] = ((df['hour'] >= 0) & (df['hour'] < 8)).astype(int)
    df['is_london'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
    df['is_ny'] = ((df['hour'] >= 13) & (df['hour'] < 22)).astype(int)
    
    return df

print("📡 Conectando ao banco de dados...")
engine = get_db_connection()

# Carregar dados
df = load_data_from_db(engine, CONFIG['symbol'], CONFIG['timeframe'], CONFIG['limit'])

# Preparar features
print("🔧 Preparando features...")
df = add_time_features(df)
df = create_target(df, horizon=5)

print(f"   Target positivo: {df['target'].mean():.2%}")
print(f"   Período: {df['ts'].min()} até {df['ts'].max()}\n")

# Selecionar features
feature_cols = [
    # Price action
    'open', 'high', 'low', 'close', 'volume',
    # Indicadores
    'rsi', 'macd', 'macd_signal', 'macd_hist',
    'bb_upper', 'bb_middle', 'bb_lower',
    'atr',
    # Time features
    'hour', 'minute', 'weekday',
    'is_asian', 'is_london', 'is_ny',
]

X = df[feature_cols].fillna(0).values
y = df['target'].values

print(f"📏 Shape dos dados:")
print(f"   Features: {X.shape[1]}")
print(f"   Samples: {X.shape[0]:,}\n")

# Split
print("✂️  Dividindo dados...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, 
    test_size=CONFIG['test_size'],
    random_state=CONFIG['random_state'],
    stratify=y
)

print(f"   Train: {len(X_train):,} samples")
print(f"   Test:  {len(X_test):,} samples\n")

# Treinamento
print("=" * 80)
print("🎯 TREINANDO RANDOM FOREST CLASSIFIER")
print("=" * 80)

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    min_samples_split=50,
    min_samples_leaf=20,
    max_features='sqrt',
    random_state=CONFIG['random_state'],
    n_jobs=-1,
    verbose=1
)

print("Iniciando treinamento...\n")
model.fit(X_train, y_train)

# Avaliação
print("\n" + "=" * 80)
print("📊 AVALIAÇÃO - TEST SET")
print("=" * 80 + "\n")

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

# Métricas
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

print(f"📈 Métricas:")
print(f"   Precision: {precision:.4f}")
print(f"   Recall:    {recall:.4f}")
print(f"   AUC-ROC:   {auc:.4f}")
print(f"   Positivos: {y_pred.sum():,} ({y_pred.mean():.1%})\n")

print(f"📊 Confusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(f"   TN: {cm[0,0]:6,}  FP: {cm[0,1]:6,}")
print(f"   FN: {cm[1,0]:6,}  TP: {cm[1,1]:6,}\n")

print("📝 Classification Report:")
print(classification_report(y_test, y_pred, digits=3))

# Feature importance
feature_importance = pd.DataFrame({
    'feature': feature_cols,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("\n🔝 Top 10 Features Mais Importantes:")
for idx, row in feature_importance.head(10).iterrows():
    print(f"   {row['feature']:20s}: {row['importance']:.4f}")

# Salvar modelo
print("\n💾 Salvando modelo...")
model_path = '/tmp/random_forest_model.joblib'
joblib.dump(model, model_path)
print(f"   ✅ Modelo salvo: {model_path}")

# Salvar report
report = {
    'timestamp': datetime.now().isoformat(),
    'model': 'RandomForestClassifier',
    'dataset': {
        'symbol': CONFIG['symbol'],
        'timeframe': CONFIG['timeframe'],
        'total_samples': int(len(X)),
        'train_samples': int(len(X_train)),
        'test_samples': int(len(X_test)),
        'features': len(feature_cols),
    },
    'metrics': {
        'precision': float(precision),
        'recall': float(recall),
        'auc_roc': float(auc),
        'positive_rate': float(y_pred.mean()),
    },
    'feature_importance': feature_importance.head(20).to_dict('records'),
}

report_path = '/tmp/model_report.json'
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)
print(f"   ✅ Report salvo: {report_path}")

print("\n" + "=" * 80)
print("✅ TREINAMENTO CONCLUÍDO COM SUCESSO!")
print("=" * 80)
print(f"🎯 Precision: {precision:.1%}")
print(f"🎯 Recall: {recall:.1%}")
print(f"🎯 AUC-ROC: {auc:.1%}")
print("=" * 80)
