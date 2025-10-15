import os
import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine, text
from typing import List
from .features_sql import LATEST_WINDOW_SQL

router = APIRouter()

DB_URL = os.environ.get("DATABASE_URL")
MODEL_PATH = os.environ.get("MODEL_PATH", "/models/rf_m1.pkl")
engine = create_engine(DB_URL, pool_pre_ping=True, future=True)

_model_cache = None


def load_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = joblib.load(MODEL_PATH)
    return _model_cache


@router.get("/predict_batch")
def predict_batch(symbols: str = Query(..., min_length=3), lookback: int = 180):
    mdl = load_model()
    features = mdl["features"]

    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms:
        raise HTTPException(status_code=400, detail="no symbols provided")

    results = []
    with engine.connect() as conn:
        for sym in syms:
            df = pd.read_sql(text(LATEST_WINDOW_SQL), conn, params={"symbol": sym, "lookback": lookback})
            if df.empty:
                results.append({"symbol": sym, "error": "no data"})
                continue
            X = df[[
                "close","volume","spread","rsi",
                "macd","macd_signal","macd_hist","atr",
                "ma60","ret_1"
            ]].fillna(0)
            X = X[features]
            proba = mdl["model"].predict_proba(X.iloc[[-1]])[0,1]
            label = int(proba >= float(os.environ.get("THRESHOLD", 0.55)))
            results.append({
                "symbol": sym,
                "ts": df["ts"].iloc[-1].isoformat(),
                "proba_up": round(float(proba), 4),
                "label": label,
            })

    return {"ok": True, "results": results}
