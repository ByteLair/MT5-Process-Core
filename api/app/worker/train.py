import os
import sys
import joblib
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.ensemble import RandomForestClassifier

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DB_URL = os.environ.get("DATABASE_URL")
MODEL_DIR = os.environ.get("MODEL_DIR", "/models")
MODEL_PATH = os.path.join(MODEL_DIR, os.environ.get("MODEL_FILE", "rf_m1.pkl"))

os.makedirs(MODEL_DIR, exist_ok=True)
from db import engine

SQL = """
SELECT * FROM public.trainset_m1
WHERE ts >= now() - interval '60 days'
ORDER BY ts;
"""

print("[train] carregando dataset...")
with engine.connect() as conn:
    df = pd.read_sql(text(SQL), conn)

print(f"[train] {len(df)} linhas carregadas")

if df.empty:
    raise SystemExit("[train] Nenhum dado disponível para treino.")

X = df[[
    "close", "volume", "spread", "rsi",
    "macd", "macd_signal", "macd_hist", "atr",
    "ma60", "ret_1"
]].fillna(0)

y = (df["fwd_ret_5"] > 0).astype(int)

m = RandomForestClassifier(
    n_estimators=300, max_depth=None, random_state=42, n_jobs=-1
)
m.fit(X, y)

joblib.dump({"model": m, "features": list(X.columns)}, MODEL_PATH)
print(f"[train] modelo salvo em {MODEL_PATH}")
