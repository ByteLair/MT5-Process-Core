# api/app/ingest.py
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
import os
import time
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge

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

# Prometheus metrics
INGEST_INSERTED_TOTAL = Counter(
    "ingest_candles_inserted_total",
    "Total de candles inseridos via /ingest"
)

INGEST_REQUESTS_TOTAL = Counter(
    "ingest_requests_total",
    "Total de requisições ao endpoint /ingest",
    ["method", "status"]
)

INGEST_DUPLICATES_TOTAL = Counter(
    "ingest_duplicates_total",
    "Total de candles duplicados (ignorados)",
    ["symbol", "timeframe"]
)

INGEST_LATENCY = Histogram(
    "ingest_latency_seconds",
    "Latência do processamento de ingest",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

INGEST_BATCH_SIZE = Histogram(
    "ingest_batch_size",
    "Tamanho dos batches recebidos",
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
)

@router.post("/ingest")
def ingest(data: Candle | CandleBatch, x_api_key: str | None = Header(None)):
    start_time = time.time()
    
    try:
        auth(x_api_key)
        
        # Convert single candle to list for unified processing
        candles = data.items if isinstance(data, CandleBatch) else [data]
        batch_size = len(candles)
        INGEST_BATCH_SIZE.observe(batch_size)
        
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
                if result.rowcount == 0:
                    # Duplicate detected
                    INGEST_DUPLICATES_TOTAL.labels(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe
                    ).inc()
                else:
                    inserted += result.rowcount
        
        if inserted:
            INGEST_INSERTED_TOTAL.inc(inserted)
        
        # Record success
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="200").inc()
        INGEST_LATENCY.observe(time.time() - start_time)
        
        return {"ok": True, "inserted": inserted, "received": batch_size, "duplicates": batch_size - inserted}
        
    except HTTPException as e:
        # Record auth failure
        INGEST_REQUESTS_TOTAL.labels(method="POST", status=str(e.status_code)).inc()
        raise
    except Exception as e:
        # Record other errors
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))
