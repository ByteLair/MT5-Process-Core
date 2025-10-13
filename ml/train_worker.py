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
FROM features_m1 f
JOIN labels_m1 l USING (bucket,symbol)
WHERE l.label IS NOT NULL;
"""
df = pd.read_sql(sql, conn)
X = df[['mean_close','volatility','pct_change']]
y = df['label']
model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
model.fit(X, y)
os.makedirs("/models", exist_ok=True)
joblib.dump(model, "/models/rf_m1.pkl")
print("saved:/models/rf_m1.pkl")
