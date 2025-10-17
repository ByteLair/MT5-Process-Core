# api/app/ingest.py
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
import os
from datetime import datetime
from prometheus_client import Counter

API_KEY = os.getenv("API_KEY", "supersecretkey")
ENGINE  = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True, future=True)

router = APIRouter(tags=["ingest"])

class Candle(BaseModel):
    ts: datetime
    symbol: str
    timeframe: str = Field(pattern="^(M1|M5|M15|M30|H1|H4|D1)$")
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None

class CandleBatch(BaseModel):
    items: list[Candle]

def auth(x_api_key: str | None):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")

INGEST_INSERTED_TOTAL = Counter(
    "ingest_candles_inserted_total",
    "Total de candles inseridos via /ingest"
)

@router.post("/ingest")
def ingest(data: Candle | CandleBatch, x_api_key: str | None = Header(None)):
    auth(x_api_key)
    
    # Convert single candle to list for unified processing
    candles = data.items if isinstance(data, CandleBatch) else [data]
    
    sql = text("""
      INSERT INTO market_data
        (ts, symbol, timeframe, open, high, low, close, volume)
      VALUES (:ts, :symbol, :timeframe, :open, :high, :low, :close, :volume)
      ON CONFLICT (symbol, timeframe, ts) DO NOTHING
    """)
    with ENGINE.begin() as conn:
        inserted = 0
        for candle in candles:
            result = conn.execute(sql, candle.model_dump())
            inserted += result.rowcount
    if inserted:
        INGEST_INSERTED_TOTAL.inc(inserted)
    return {"ok": True, "inserted": inserted}
