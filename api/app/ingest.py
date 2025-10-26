# api/app/ingest.py
import json
import logging
import os
import sys
import time
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field
from sqlalchemy import text


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

API_KEY = os.getenv("API_KEY", "supersecretkey")
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

        sql = text(
            """
            INSERT INTO market_data
                (ts, symbol, timeframe, open, high, low, close, volume, bid, ask, spread,
                 rsi, macd, macd_signal, macd_hist, atr, bb_upper, bb_middle, bb_lower)
            VALUES (:ts, :symbol, :timeframe, :open, :high, :low, :close, :volume, :bid, :ask, :spread,
                    :rsi, :macd, :macd_signal, :macd_hist, :atr, :bb_upper, :bb_middle, :bb_lower)
            ON CONFLICT (symbol, timeframe, ts) DO NOTHING
            """
        )
        details = []
        with ENGINE.begin() as conn:
            inserted = 0
            for candle in candles:
                # Calcular bucket e preparar params de insert mantendo o ts original para logs
                ts_original = candle.ts
                ts_bucket = _bucket_start(ts_original, candle.timeframe)
                params = candle.model_dump()
                params["ts"] = ts_bucket
                result = conn.execute(sql, params)
                if result.rowcount == 0:
                    # Duplicate detected
                    status = "duplicate"
                    INGEST_DUPLICATES_TOTAL.labels(
                        symbol=candle.symbol, timeframe=candle.timeframe
                    ).inc()
                else:
                    status = "inserted"
                    inserted += result.rowcount
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
        # Record auth failure
        INGEST_REQUESTS_TOTAL.labels(method="POST", status=str(e.status_code)).inc()
        raise
    except Exception as e:
        # Record other errors
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


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

        sql = text(
            """
            INSERT INTO market_data
                (ts, symbol, timeframe, open, high, low, close, volume, bid, ask, spread,
                 rsi, macd, macd_signal, macd_hist, atr, bb_upper, bb_middle, bb_lower)
            VALUES (:ts, :symbol, :timeframe, :open, :high, :low, :close, :volume, :bid, :ask, :spread,
                    :rsi, :macd, :macd_signal, :macd_hist, :atr, :bb_upper, :bb_middle, :bb_lower)
            ON CONFLICT (symbol, timeframe, ts) DO NOTHING
            """
        )
        details = []
        with ENGINE.begin() as conn:
            inserted = 0
            for candle in candles:
                ts_original = candle.ts
                ts_bucket = _bucket_start(ts_original, candle.timeframe)
                params = candle.model_dump()
                params["ts"] = ts_bucket
                result = conn.execute(sql, params)
                if result.rowcount == 0:
                    status = "duplicate"
                    INGEST_DUPLICATES_TOTAL.labels(
                        symbol=candle.symbol,
                        timeframe=candle.timeframe,
                    ).inc()
                else:
                    status = "inserted"
                    inserted += result.rowcount
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
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))


class TickWrapper(BaseModel):
    """Wrapper para compatibilidade com EA que envia {"ticks": [...]}"""

    ticks: list[dict]


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
        INGEST_REQUESTS_TOTAL.labels(method="POST", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))
