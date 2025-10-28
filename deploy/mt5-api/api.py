import os
import time
import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional, Dict
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2
from psycopg2 import pool, OperationalError, DatabaseError
from psycopg2.extras import execute_values

# Load env
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "mt5_data")
DB_USER = os.getenv("DB_USER", "mt5user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
LOG_FILE = os.getenv("LOG_FILE", "/var/log/mt5_api.log")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "http://192.168.15.19")

# Logging
logger = logging.getLogger("mt5_api")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)

app = FastAPI(title="MT5 Ingest API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple models
class Tick(BaseModel):
    symbol: str = Field(..., min_length=1)
    time: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None


class BulkTicks(BaseModel):
    ticks: List[Tick]


# DB pool
db_pool: Optional[pool.ThreadedConnectionPool] = None


def startup_pool():
    global db_pool
    if db_pool:
        return
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        1, int(os.getenv("DB_MAX_CONN", "20")),
        user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, database=DB_NAME,
    )


@app.on_event("startup")
def startup():
    startup_pool()
    logger.info("startup complete")


def get_conn():
    if not db_pool:
        raise RuntimeError("DB pool not initialized")
    return db_pool.getconn()


def put_conn(conn):
    if db_pool and conn:
        db_pool.putconn(conn)


def db_retry(max_retries=3, base_delay=0.05):
    def outer(f):
        def inner(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return f(*args, **kwargs)
                except (OperationalError, DatabaseError) as e:
                    last_exc = e
                    logger.warning("DB operation failed (attempt %d): %s", attempt, e)
                    time.sleep(base_delay * attempt)
            logger.error("DB operation failed after retries: %s", last_exc)
            raise last_exc
        return inner
    return outer


@db_retry(max_retries=3)
def insert_ticks_bulk(ticks: List[Tick]) -> int:
    if not ticks:
        return 0
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        rows = []
        for t in ticks:
            ts = datetime.fromtimestamp(t.time, tz=timezone.utc).isoformat()
            rows.append((ts, t.symbol, t.bid, t.ask, t.last, t.volume))
        sql = "INSERT INTO ticks (time, symbol, bid, ask, last, volume) VALUES %s"
        execute_values(cur, sql, rows, page_size=1000)
        conn.commit()
        cur.close()
        return len(rows)
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("bulk insert failed")
        raise
    finally:
        if conn:
            put_conn(conn)


@db_retry(max_retries=3)
def insert_tick(t: Tick):
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        ts = datetime.fromtimestamp(t.time, tz=timezone.utc).isoformat()
        cur.execute(
            "INSERT INTO ticks (time, symbol, bid, ask, last, volume) VALUES (%s, %s, %s, %s, %s, %s)",
            (ts, t.symbol, t.bid, t.ask, t.last, t.volume),
        )
        conn.commit()
        cur.close()
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("single insert failed")
        raise
    finally:
        if conn:
            put_conn(conn)


@app.post("/tick/bulk")
async def post_bulk(bulk: BulkTicks, request: Request):
    try:
        inserted = insert_ticks_bulk(bulk.ticks)
        return {"status": "success", "inserted": inserted}
    except Exception:
        raise HTTPException(status_code=500, detail="insert failed")


@app.post("/tick")
async def post_tick(tick: Tick):
    try:
        insert_tick(tick)
        return {"status": "success", "inserted": 1}
    except Exception:
        raise HTTPException(status_code=500, detail="insert failed")


@app.get("/health")
async def health():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        put_conn(conn)
        return {"status": "ok"}
    except Exception:
        logger.exception("health check failed")
        raise HTTPException(status_code=503, detail="db unavailable")


@app.get("/stats")
async def stats():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM ticks")
        total = cur.fetchone()[0]
        cur.execute("SELECT max(time) FROM ticks")
        last = cur.fetchone()[0]
        cur.execute("SELECT symbol, count(*) FROM ticks GROUP BY symbol ORDER BY count DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close()
        put_conn(conn)
        return {"total_ticks": total, "last_tick_time": str(last), "ticks_per_symbol": {r[0]: r[1] for r in rows}}
    except Exception:
        logger.exception("stats failed")
        raise HTTPException(status_code=500, detail="stats failed")
