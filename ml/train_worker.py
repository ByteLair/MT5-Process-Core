import os, joblib, pandas as pd, psycopg2
from sklearn.ensemble import RandomForestClassifier

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME","mt5_trading"),
    user=os.getenv("DB_USER","trader"),
    password=os.getenv("DB_PASS","trader123"),
    host=os.getenv("DB_HOST","db"),
)
sql = """
SELECT f.mean_close, f.volatility, f.pct_change, l.label
FROM features_h1 f
JOIN labels_h1  l
    ON f.symbol = l.symbol AND f.ts = l.ts
WHERE l.label IS NOT NULL
    AND f.mean_close IS NOT NULL
    AND f.pct_change IS NOT NULL;
"""
df = pd.read_sql(sql, conn)
if df.empty:
    print("[ML] Nenhum dado disponível para treinamento (views vazias). Abortando.")
    raise SystemExit(1)

# criar label binário a partir de fwd_ret_5 (ex.: positivo -> 1)
df = df.dropna()
df['label'] = (df['fwd_ret_5'] > 0).astype(int)

X = df[['mean_close','volatility','pct_change']]
y = df['label']
model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
model.fit(X, y)
os.makedirs("/models", exist_ok=True)
joblib.dump(model, "/models/rf_m1.pkl")
print("saved:/models/rf_m1.pkl")
