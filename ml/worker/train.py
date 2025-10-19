import os, joblib, pandas as pd, logging
from sqlalchemy import create_engine


# Configuração de logging estruturado
LOG_DIR = os.environ.get("LOG_DIR", "/app/logs/ml/")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "train.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

DB_URL = os.environ["DATABASE_URL"]
MODELS_DIR = os.environ.get("MODELS_DIR", "./models")
os.makedirs(MODELS_DIR, exist_ok=True)
engine = create_engine(DB_URL, pool_pre_ping=True, future=True)

df = pd.read_sql("""
 SELECT * FROM public.trainset_m1
 WHERE ts >= now() - interval '60 days'
 ORDER BY ts
""", engine)

if df.empty:
    logging.error("dataset vazio: popula market_data primeiro")
    raise SystemExit("dataset vazio: popula market_data primeiro")

X = df[[
    "close","volume","spread","rsi","macd","macd_signal","macd_hist","atr","ma60","ret_1"
]].fillna(0)
y = (df["fwd_ret_5"] > 0).astype(int)

from sklearn.ensemble import RandomForestClassifier
m = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
m.fit(X, y)

path = os.path.join(MODELS_DIR, "rf_m1.pkl")
joblib.dump(m, path)
logging.info(f"modelo salvo: {path}")
print(f"modelo salvo: {path}")
