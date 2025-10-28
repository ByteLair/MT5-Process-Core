# api/app/ingest.py
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import execute_values
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError


# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Robust import of the shared SQLAlchemy engine
try:
    from db import engine as ENGINE  # type: ignore
except Exception:  # pragma: no cover - fallback for different loaders
    try:
        from api.db import engine as ENGINE  # type: ignore
    except Exception:
        from ..db import engine as ENGINE  # type: ignore

API_KEY = os.getenv("API_KEY", "mt5_a8f5c3e1-4d2b-4a9e-8c7f-1b3e5d7a9c2f")
DISABLE_TICK_INGEST = os.getenv("DISABLE_TICK_INGEST", "true").lower() in {"1", "true", "yes"}

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
    bid: float | None = None
    ask: float | None = None
    spread: float | None = None
    # Indicadores opcionais
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    atr: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None


class CandleBatch(BaseModel):
    items: list[Candle]


def auth(x_api_key: str | None):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="unauthorized")


def _bucket_start(ts: datetime, timeframe: str) -> datetime:
    """Retorna o início do bucket de tempo conforme timeframe (M1,M5,M15,M30,H1,H4,D1).
    Garante deduplicação por janela (ex.: mesmo minuto para M1).
    """
    tf = timeframe.upper()
    # Preserva tzinfo (UTC recomendado)
    if tf == "D1":
        return ts.replace(hour=0, minute=0, second=0, microsecond=0)
    if tf == "H4":
        hour_bucket = (ts.hour // 4) * 4
        return ts.replace(hour=hour_bucket, minute=0, second=0, microsecond=0)
    if tf == "H1":
        return ts.replace(minute=0, second=0, microsecond=0)
    # Minutos
    minute_map = {"M1": 1, "M5": 5, "M15": 15, "M30": 30}
    if tf in minute_map:
        step = minute_map[tf]
        minute_bucket = (ts.minute // step) * step
        return ts.replace(minute=minute_bucket, second=0, microsecond=0)
    # Fallback: zera segundos
    return ts.replace(second=0, microsecond=0)


# Columns that are allowed to be inserted into market_data. Keep in sync with DB/migrations.
ALLOWED_MARKET_DATA_COLUMNS = [
    "ts",
    "symbol",
    "timeframe",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "bid",
    "ask",
    "spread",
    # indicators
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "atr",
    "bb_upper",
    "bb_middle",
    "bb_lower",
]


def _build_insert_for_params(params: dict) -> tuple[str, dict]:
    """Build dynamic INSERT SQL for the keys present in params that are allowed.

    Returns (sql_text, filtered_params)
    """
    # keep only allowed keys
    keys = [k for k in params.keys() if k in ALLOWED_MARKET_DATA_COLUMNS]
    if not keys:
        raise ValueError("no valid fields to insert")

    cols = ", ".join(keys)
    placeholders = ", ".join([f":{k}" for k in keys])
    sql = f"INSERT INTO market_data ({cols}) VALUES ({placeholders}) ON CONFLICT (symbol, timeframe, ts) DO NOTHING"
    # Build filtered params dict with only keys used in SQL
    filtered = {k: params[k] for k in keys}
    return sql, filtered


# Prometheus metrics
INGEST_INSERTED_TOTAL = Counter(
    "ingest_candles_inserted_total",
    "Total de candles inseridos via /ingest",
    # =============================================================
    # Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
    # All rights reserved. | Todos os direitos reservados.
    # Private License: This code is the exclusive property of Felipe Petracco Carmo.
    # Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
    # Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
    # Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
    # =============================================================
)

INGEST_REQUESTS_TOTAL = Counter(
    "ingest_requests_total",
    "Total de requisições ao endpoint /ingest",
    ["method", "status"],
)

INGEST_DUPLICATES_TOTAL = Counter(
    "ingest_duplicates_total",
    "Total de candles duplicados (ignorados)",
    ["symbol", "timeframe"],
)

INGEST_LATENCY = Histogram(
    "ingest_latency_seconds",
    "Latência do processamento de ingest",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

INGEST_BATCH_SIZE = Histogram(
    "ingest_batch_size",
    "Tamanho dos batches recebidos",
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000],
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

        # We'll build INSERTs dynamically per-candle with only the keys present to avoid
        # referencing DB columns that may not exist. Use _build_insert_for_params to
        # create SQL and a filtered params dict (safe against injection via allowed list).
        details = []
        with ENGINE.begin() as conn:
            inserted = 0
            for candle in candles:
                # Calcular bucket e preparar params de insert mantendo o ts original para logs
                ts_original = candle.ts
                ts_bucket = _bucket_start(ts_original, candle.timeframe)
                params = candle.model_dump()
                params["ts"] = ts_bucket

                try:
                    sql_text, filtered = _build_insert_for_params(params)
                    result = conn.execute(text(sql_text), filtered)
                except (SQLAlchemyError, ValueError) as e:
                    # Structured JSON error for DB/insert problems
                    logging.exception("ingest db error")
                    INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
                    return JSONResponse(status_code=500, content={"error": "db_insert_failed", "detail": str(e)})

                # SQLAlchemy result.rowcount may be None depending on DB driver; treat None as unknown
                rowcount = getattr(result, "rowcount", None)
                if rowcount == 0:
                    # Duplicate detected
                    status = "duplicate"
                    INGEST_DUPLICATES_TOTAL.labels(
                        symbol=candle.symbol, timeframe=candle.timeframe
                    ).inc()
                else:
                    status = "inserted"
                    if isinstance(rowcount, int):
                        inserted += rowcount
                    else:
                        inserted += 1

                info = {
                    "symbol": candle.symbol,
                    "timeframe": candle.timeframe,
                    "ts_original": ts_original.isoformat(),
                    "ts_bucket": ts_bucket.isoformat(),
                    "status": status,
                }
                logging.info("ingest_item", extra={"ingest": info})
                details.append(info)

        if inserted:
            INGEST_INSERTED_TOTAL.inc(inserted)

        # Record success
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="200").inc()
        INGEST_LATENCY.observe(time.time() - start_time)

        return {
            "ok": True,
            "inserted": inserted,
            "received": batch_size,
            "duplicates": batch_size - inserted,
            "details": details,
        }

    except HTTPException as e:
        # Record auth / explicit HTTP failure
        INGEST_REQUESTS_TOTAL.labels(method="POST", status=str(e.status_code)).inc()
        raise
    except Exception as e:
        logging.exception("unexpected ingest error")
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
        return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "unexpected error"})


@router.post("/ingest_batch")
def ingest_batch(candles: list[Candle], x_api_key: str | None = Header(None)):
    """
    Compat route: accepts a pure JSON array of Candle objects.
    Mirrors /ingest behavior but the request body is an array instead of {"items": [...]}.
    """
    start_time = time.time()
    try:
        auth(x_api_key)

        batch_size = len(candles)
        INGEST_BATCH_SIZE.observe(batch_size)

        # Use the same dynamic insert strategy as /ingest: only insert allowed keys present in each payload.
        details = []
        with ENGINE.begin() as conn:
            inserted = 0
            for candle in candles:
                ts_original = candle.ts
                ts_bucket = _bucket_start(ts_original, candle.timeframe)
                params = candle.model_dump()
                params["ts"] = ts_bucket

                try:
                    sql_text, filtered = _build_insert_for_params(params)
                    result = conn.execute(text(sql_text), filtered)
                except (SQLAlchemyError, ValueError) as e:
                    logging.exception("ingest_batch db error")
                    INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
                    return JSONResponse(status_code=500, content={"error": "db_insert_failed", "detail": str(e)})

                rowcount = getattr(result, "rowcount", None)
                if rowcount == 0:
                    status = "duplicate"
                    INGEST_DUPLICATES_TOTAL.labels(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe,
                    ).inc()
                else:
                    status = "inserted"
                    if isinstance(rowcount, int):
                        inserted += rowcount
                    else:
                        inserted += 1

                info = {
                    "symbol": candle.symbol,
                    "timeframe": candle.timeframe,
                    "ts_original": ts_original.isoformat(),
                    "ts_bucket": ts_bucket.isoformat(),
                    "status": status,
                }
                logging.info("ingest_item", extra={"ingest": info})
                details.append(info)

        if inserted:
            INGEST_INSERTED_TOTAL.inc(inserted)

        INGEST_REQUESTS_TOTAL.labels(method="POST", status="200").inc()
        INGEST_LATENCY.observe(time.time() - start_time)
        return {
            "ok": True,
            "inserted": inserted,
            "received": batch_size,
            "duplicates": batch_size - inserted,
            "details": details,
        }
    except HTTPException:
        # Auth or other explicit HTTP errors bubble up unchanged
        raise
    except Exception as e:
        logging.exception("unexpected ingest_batch error")
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
        return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "unexpected error"})


class TickWrapper(BaseModel):
    """Wrapper para compatibilidade com EA que envia {"ticks": [...]}"""

    ticks: list[dict]


# New models for tick ingestion
class Tick(BaseModel):
    symbol: str = Field(..., min_length=1)
    time: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    volume: Optional[int] = None


class BulkTickPayload(BaseModel):
    ticks: List[Tick]


_mt5_logger = logging.getLogger("mt5_api_ticks")
_mt5_logger.setLevel(logging.INFO)
try:
    fh = logging.handlers.RotatingFileHandler("/var/log/mt5_api.log", maxBytes=10 * 1024 * 1024, backupCount=5)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _mt5_logger.addHandler(fh)
except Exception:
    logging.exception("could not create mt5_api.log handler")


@router.post("/ingest/tick")
def ingest_tick(data: TickWrapper, x_api_key: str | None = Header(None)):
    """
    Endpoint para ingestão de ticks em lote. Aceita corpo {"ticks": [...]}
    e persiste o JSON bruto em market_data_raw para posterior processamento.
    """
    start_time = time.time()
    try:
        auth(x_api_key)

        # Se ticks estiverem desabilitados por política, retornar 410
        if DISABLE_TICK_INGEST:
            raise HTTPException(status_code=410, detail="Tick ingestion disabled. Use /ingest with timeframe='M1'.")

        # Para consistência, computamos bucket de minuto por tick (sem persistir ainda em market_data)
        details = []
        for t in data.ticks:
            ts_str = t.get("ts")
            symbol = t.get("symbol")
            try:
                # Parse ts se vier em string ISO8601
                ts = (
                    datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    if isinstance(ts_str, str)
                    else ts_str
                )
            except Exception:
                ts = None
            ts_bucket = None
            if isinstance(ts, datetime):
                # Bucket de minuto (padrão adquirido), independentemente de timeframe aqui
                ts_bucket = ts.replace(second=0, microsecond=0)
            info = {
                "symbol": symbol,
                "ts_original": ts_str,
                "ts_bucket": ts_bucket.isoformat() if ts_bucket else None,
                "status": "received",
            }
            logging.info("ingest_tick_item", extra={"ingest_tick": info})
            details.append(info)

        payload = {"ticks": data.ticks}
        sql = text(
            """
            INSERT INTO market_data_raw (source, payload)
            VALUES (:source, CAST(:payload AS jsonb))
            """
        )
        with ENGINE.begin() as conn:
            conn.execute(sql, {"source": "ea_tick", "payload": json.dumps(payload)})

        INGEST_REQUESTS_TOTAL.labels(method="POST", status="200").inc()
        INGEST_LATENCY.observe(time.time() - start_time)
        return {"ok": True, "received": len(data.ticks), "details": details}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("unexpected ingest_tick error")
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
        return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "unexpected error"})



@router.post("/tick/bulk")
def tick_bulk(body: BulkTickPayload, x_api_key: str | None = Header(None)):
    """Recebe múltiplos ticks em um JSON: {"ticks": [{...}, ...]} - usa insert em batch via psycopg2.execute_values
    Retorna {status: success, inserted: N}
    """
    start = time.time()
    try:
        auth(x_api_key)
        ticks = body.ticks
        if not ticks:
            raise HTTPException(status_code=400, detail="empty payload")

        # Prepare rows (time -> timestamptz)
        rows = []
        for t in ticks:
            try:
                ts = datetime.fromtimestamp(t.time, tz=timezone.utc)
            except Exception:
                raise HTTPException(status_code=400, detail=f"invalid time for symbol {t.symbol}")
            rows.append((ts.isoformat(), t.symbol, t.bid, t.ask, t.last, t.volume))

        # Use raw connection from SQLAlchemy engine to access psycopg2.execute_values
        raw = ENGINE.raw_connection()
        try:
            cur = raw.cursor()
            sql = "INSERT INTO ticks (time, symbol, bid, ask, last, volume) VALUES %s"
            execute_values(cur, sql, rows, page_size=1000)
            inserted = cur.rowcount if cur.rowcount and cur.rowcount > 0 else len(rows)
            raw.commit()
            cur.close()
        finally:
            try:
                raw.close()
            except Exception:
                pass

        _mt5_logger.info("bulk inserted %d ticks in %.3fs", inserted, time.time() - start)
        return {"status": "success", "inserted": inserted}
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("tick_bulk failed")
        raise HTTPException(status_code=500, detail="internal error")


@router.post("/tick")
def tick_single(tick: Tick, x_api_key: str | None = Header(None)):
    try:
        auth(x_api_key)
        try:
            ts = datetime.fromtimestamp(tick.time, tz=timezone.utc)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid time")

        with ENGINE.begin() as conn:
            conn.execute(
                text("INSERT INTO ticks (time, symbol, bid, ask, last, volume) VALUES (:time, :symbol, :bid, :ask, :last, :volume)"),
                {
                    "time": ts.isoformat(),
                    "symbol": tick.symbol,
                    "bid": tick.bid,
                    "ask": tick.ask,
                    "last": tick.last,
                    "volume": tick.volume,
                },
            )

        _mt5_logger.info("inserted tick %s@%s", tick.symbol, ts.isoformat())
        return {"status": "success", "inserted": 1}
    except HTTPException:
        raise
    except Exception:
        logging.exception("tick_single failed")
        raise HTTPException(status_code=500, detail="internal error")


@router.get("/stats")
def tick_stats(x_api_key: str | None = Header(None)):
    try:
        auth(x_api_key)
        with ENGINE.begin() as conn:
            total = conn.execute(text("SELECT count(*) FROM ticks")).scalar()
            last_time = conn.execute(text("SELECT max(time) FROM ticks")).scalar()
            rows = conn.execute(text("SELECT symbol, count(*) FROM ticks GROUP BY symbol ORDER BY count DESC LIMIT 100")).all()

        ticks_per_symbol = {r[0]: r[1] for r in rows}
        return {"total_ticks": int(total or 0), "last_tick_time": str(last_time) if last_time else None, "ticks_per_symbol": ticks_per_symbol}
    except HTTPException:
        raise
    except Exception:
        logging.exception("tick_stats failed")
        raise HTTPException(status_code=500, detail="internal error")
