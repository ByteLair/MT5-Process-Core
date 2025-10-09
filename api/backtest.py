# api/app/backtest.py
import os
import pandas as pd
from fastapi import APIRouter, Query, HTTPException
from sqlalchemy import create_engine

router = APIRouter(tags=["ml"])

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://trader:trader123@db:5432/mt5_trading")
engine = create_engine(DB_URL)

@router.get("/backtest")
def backtest(symbol: str = Query(...), timeframe: str = Query("M1")):
    # Sinais salvos
    sig = pd.read_sql("""
        SELECT ts, label, prob_up
        FROM public.model_signals
        WHERE symbol=%(s)s AND timeframe=%(tf)s
        ORDER BY ts
    """, engine, params={"s": symbol, "tf": timeframe})
    if sig.empty:
        raise HTTPException(404, "Sem sinais salvos para esse filtro.")

    # Preços (para retorno futuro de 5 barras)
    px = pd.read_sql("""
        SELECT ts, close
        FROM public.market_data
        WHERE symbol=%(s)s AND timeframe=%(tf)s
        ORDER BY ts
    """, engine, params={"s": symbol, "tf": timeframe})

    df = sig.merge(px, on="ts", how="left").sort_values("ts").reset_index(drop=True)
    df["close_fwd5"] = df["close"].shift(-5)
    df["fwd_ret_5"] = (df["close_fwd5"] - df["close"]) / df["close"]
    df["truth"] = (df["fwd_ret_5"] > 0).astype(int)

    eval_df = df.dropna(subset=["truth"])
    if eval_df.empty:
        raise HTTPException(400, "Ainda não há barras futuras suficientes para avaliar.")

    acc = float((eval_df["label"] == eval_df["truth"]).mean())
    tp = int(((eval_df["label"] == 1) & (eval_df["truth"] == 1)).sum())
    fp = int(((eval_df["label"] == 1) & (eval_df["truth"] == 0)).sum())
    tn = int(((eval_df["label"] == 0) & (eval_df["truth"] == 0)).sum())
    fn = int(((eval_df["label"] == 0) & (eval_df["truth"] == 1)).sum())

    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec  = tp / (tp + fn) if (tp + fn) else 0.0
    f1   = (2*prec*rec)/(prec+rec) if (prec+rec) else 0.0

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "n_eval": int(len(eval_df)),
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1
    }
