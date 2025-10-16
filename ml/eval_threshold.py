# ml/eval_threshold.py
import os, psycopg2, pandas as pd, numpy as np
conn = psycopg2.connect(dbname=os.getenv("DB_NAME","mt5_trading"),
                        user=os.getenv("DB_USER","trader"),
                        password=os.getenv("DB_PASS","trader123"),
                        host=os.getenv("DB_HOST","db"))
sql = """
SELECT f.mean_close, f.volatility, f.pct_change, l.fwd_ret_5
FROM features_h1 f
JOIN labels_h1  l ON f.symbol=l.symbol AND f.ts=l.ts
WHERE f.mean_close IS NOT NULL AND f.pct_change IS NOT NULL AND l.fwd_ret_5 IS NOT NULL
ORDER BY f.ts
"""
df = pd.read_sql(sql, conn).dropna()
y = (df["fwd_ret_5"] > 0).astype(int).values

import joblib
m = joblib.load("/models/latest_model.pkl")
X = df[["mean_close","volatility","pct_change"]].values
p = m.predict_proba(X)[:,1]

def metrics(thr):
    pred = np.where(p>=thr,1, np.where((1-p)>=thr,0, -1))  # -1 = flat
    mask = pred!=-1
    if mask.sum()==0: return thr,0,0,0
    from sklearn.metrics import precision_score, recall_score, f1_score
    return thr, precision_score(y[mask], pred[mask]), recall_score(y[mask], pred[mask]), f1_score(y[mask], pred[mask])

ths = np.round(np.linspace(0.50, 0.80, 31),2)
res = [metrics(t) for t in ths]
best = max(res, key=lambda r: r[3])  # maior F1
print("threshold,f1,precision,recall")
for r in res: print(f"{r[0]:.2f},{r[3]:.4f},{r[1]:.4f},{r[2]:.4f}")
print("best:", best)
