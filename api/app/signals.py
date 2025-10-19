# api/app/signals.py
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_KEY = os.getenv("API_KEY", "supersecretkey")
from db import engine as ENGINE

router = APIRouter(prefix="/signals", tags=["signals"])

def auth(x_api_key: str | None):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

@router.get("/next")
def next_signal(
    account_id: str = Query(...),
    symbols: str = Query(..., description="CSV ex.: EURUSD,GBPUSD"),
    timeframe: str = Query(...),
    x_api_key: str | None = Header(None),
):
    auth(x_api_key)
    symbols_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbols_list:
        return {"signals": []}

    sql = text("""
        WITH cand AS (
          SELECT id, ts, account_id, symbol, timeframe, side, confidence,
                 sl_pips, tp_pips, ttl_sec, meta
          FROM public.signals_queue
          WHERE status='PENDING'
            AND (account_id IS NULL OR account_id=:account_id)
            AND symbol = ANY(:symbols)
            AND timeframe = :timeframe
            AND (now() - ts) <= (ttl_sec || ' seconds')::interval
          ORDER BY ts DESC
          LIMIT 1
        ),
        mark AS (
          UPDATE public.signals_queue q
             SET status='SENT'
            FROM cand c
           WHERE q.id=c.id
          RETURNING q.id
        )
        SELECT c.*
        FROM cand c;
    """)
    params = {"account_id": account_id, "symbols": symbols_list, "timeframe": timeframe}
    with ENGINE.connect() as conn:
        row = conn.execute(sql, params).mappings().first()
    if not row:
        return {"signals": []}
    payload = {
        "id": row["id"],
        "symbol": row["symbol"],
        "timeframe": row["timeframe"],
        "side": row["side"],
        "confidence": row["confidence"],
        "ttl_sec": row["ttl_sec"],
        "sl_pips": row["sl_pips"],
        "tp_pips": row["tp_pips"],
        "meta": row["meta"],
    }
    return {"signals": [payload]}

class AckIn(BaseModel):
    id: str
    status: str      # FILLED | REJECTED
    symbol: str
    side: str
    mt5_ticket: int | None = None
    price: float | None = None
    ts_exec: str | None = None
    account_id: str | None = None

@router.post("/ack")
def ack_signal(ack: AckIn, x_api_key: str | None = Header(None)):
    auth(x_api_key)
    with ENGINE.begin() as conn:
        conn.execute(text("""
          INSERT INTO public.signals_ack
            (id, account_id, symbol, side, mt5_ticket, price, status, ts_exec)
          VALUES (:id, :account_id, :symbol, :side, :mt5_ticket, :price, :status, :ts_exec)
        """), ack.model_dump())
        conn.execute(text("""
          UPDATE public.signals_queue
             SET status='ACKED'
           WHERE id=:id AND status IN ('PENDING','SENT')
        """), {"id": ack.id})
    return {"ok": True}
