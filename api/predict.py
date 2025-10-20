import os

import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from .db import engine

router = APIRouter(prefix="/predict", tags=["predict"])

FEATURES = [
    "close",
    "volume",
    "spread",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr",
    "ma60",
    "ret_1",
]


def load_model():
    models_dir = os.getenv("MODELS_DIR", "./models")
    path = os.path.join(models_dir, "rf_m1.pkl")
    if not os.path.exists(path):
        raise FileNotFoundError("modelo não encontrado: rf_m1.pkl")
    return joblib.load(path)


@router.get("")
def predict(symbol: str = Query(..., min_length=3, max_length=10), limit: int = 30):
    m = load_model()
    q = """
      SELECT * FROM public.features_m1
      WHERE symbol=:symbol ORDER BY ts DESC LIMIT :limit
    """
    df = pd.read_sql(q, engine, params={"symbol": symbol, "limit": limit})
    if df.empty:
        raise HTTPException(404, detail="sem dados")
    X = df[FEATURES].fillna(0)
    proba = m.predict_proba(X)[:, 1]
    val = float(proba[0])
    return {
        "symbol": symbol,
        "n": int(len(proba)),
        "prob_up_latest": val,
        "ts_latest": df["ts"].iloc[0].isoformat(),
    }
