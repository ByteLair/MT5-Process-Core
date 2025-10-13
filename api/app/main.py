# api/app/main.py
from __future__ import annotations

import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ---- Config ---------------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://trader:trader123@db:5432/mt5_trading",
)
API_TITLE = os.getenv("API_TITLE", "MT5 Trading DB API")
API_VERSION = os.getenv("API_VERSION", "1.2.0")

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

# ---- App ------------------------------------------------------------------

app = FastAPI(title=API_TITLE, version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOW_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Schemas --------------------------------------------------------------

class CandleIn(BaseModel):
    ts: datetime
    symbol: str = Field(..., max_length=15)
    timeframe: str = Field(..., max_length=5)
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    spread: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = Field(None, alias="macd_signal")
    macd_hist: Optional[float] = Field(None, alias="macd_hist")
    atr: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None

    class Config:
        populate_by_name = True

# ---- Helpers --------------------------------------------------------------

UPSERT_SQL = text(
    """
INSERT INTO public.market_data (
  ts, symbol, timeframe, open, high, low, close, volume,
  spread, bid, ask, rsi, macd, macd_signal, macd_hist, atr,
  bb_upper, bb_middle, bb_lower
) VALUES (
  :ts, :symbol, :timeframe, :open, :high, :low, :close, :volume,
  :spread, :bid, :ask, :rsi, :macd, :macd_signal, :macd_hist, :atr,
  :bb_upper, :bb_middle, :bb_lower
)
ON CONFLICT (symbol, timeframe, ts) DO UPDATE SET
  open=COALESCE(EXCLUDED.open, market_data.open),
  high=COALESCE(EXCLUDED.high, market_data.high),
  low=COALESCE(EXCLUDED.low, market_data.low),
  close=COALESCE(EXCLUDED.close, market_data.close),
  volume=COALESCE(EXCLUDED.volume, market_data.volume),
  spread=COALESCE(EXCLUDED.spread, market_data.spread),
  bid=COALESCE(EXCLUDED.bid, market_data.bid),
  ask=COALESCE(EXCLUDED.ask, market_data.ask),
  rsi=COALESCE(EXCLUDED.rsi, market_data.rsi),
  macd=COALESCE(EXCLUDED.macd, market_data.macd),
  macd_signal=COALESCE(EXCLUDED.macd_signal, market_data.macd_signal),
  macd_hist=COALESCE(EXCLUDED.macd_hist, market_data.macd_hist),
  atr=COALESCE(EXCLUDED.atr, market_data.atr),
  bb_upper=COALESCE(EXCLUDED.bb_upper, market_data.bb_upper),
  bb_middle=COALESCE(EXCLUDED.bb_middle, market_data.bb_middle),
  bb_lower=COALESCE(EXCLUDED.bb_lower, market_data.bb_lower)
"""
)

# ---- Core endpoints -------------------------------------------------------

@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.post("/ingest")
def ingest(c: CandleIn):
    with engine.begin() as conn:
        conn.execute(UPSERT_SQL, c.model_dump(by_alias=True))
    return {"ok": True}

@app.post("/ingest_batch")
def ingest_batch(items: List[CandleIn]):
    if not items:
        raise HTTPException(status_code=400, detail="empty payload")
    payload = [i.model_dump(by_alias=True) for i in items]
    with engine.begin() as conn:
        conn.execute(UPSERT_SQL, payload)
    return {"ok": True, "count": len(items)}

@app.post("/ingest_raw")
def ingest_raw(payload: dict = Body(...)):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
INSERT INTO public.market_data_raw (source, payload)
VALUES (:source, :payload::jsonb)
"""
            ),
            {"source": "api/ingest_raw", "payload": payload},
        )
    return {"ok": True}

@app.get("/latest")
def latest(
    symbol: str = Query(..., min_length=3, max_length=15),
    timeframe: str = Query("M1", max_length=5),
    limit: int = Query(100, ge=1, le=5000),
):
    sql = text(
        """
SELECT ts, symbol, timeframe, open, high, low, close, volume, spread, bid, ask
FROM public.market_data
WHERE symbol = :symbol AND timeframe = :tf
ORDER BY ts DESC
LIMIT :lim
"""
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"symbol": symbol, "tf": timeframe, "lim": limit}).mappings().all()
    return {"ok": True, "data": list(rows)}

@app.get("/symbols")
def symbols(timeframe: Optional[str] = Query(None, max_length=5)):
    base = """
SELECT DISTINCT symbol, timeframe
FROM public.market_data
"""
    if timeframe:
        base += "WHERE timeframe = :tf "
    base += "ORDER BY symbol, timeframe"
    with engine.connect() as conn:
        rows = conn.execute(text(base), {"tf": timeframe} if timeframe else {}).mappings().all()
    return {"ok": True, "data": list(rows)}

# ---- IA routers -----------------------------------------------------------

# Estes módulos precisam existir no projeto:
# - api/app/predict.py
# - api/app/predict_batch.py
# - api/app/metrics.py
try:
    from .predict import router as predict_router
    app.include_router(predict_router)
except Exception as e:
    # mantém a API funcional mesmo sem o arquivo durante migrações
    print(f"[warn] predict router not loaded: {e}")

try:
    from .predict_batch import router as predict_batch_router
    app.include_router(predict_batch_router)
except Exception as e:
    print(f"[warn] predict_batch router not loaded: {e}")

try:
    from .metrics import router as metrics_router
    app.include_router(metrics_router)
except Exception as e:
    print(f"[warn] metrics router not loaded: {e}")

# ---- Root -----------------------------------------------------------------

@app.get("/")
def root():
    return {"name": API_TITLE, "version": API_VERSION}
