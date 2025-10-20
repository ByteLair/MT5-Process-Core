import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # =============================================================
    # Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
    # All rights reserved. | Todos os direitos reservados.
    # Private License: This code is the exclusive property of Felipe Petracco Carmo.
    # Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
    # Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
    # Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
    # =============================================================
)
logger = logging.getLogger(__name__)

# Robust import of the shared SQLAlchemy engine
try:
    from ..db import engine as ENGINE  # type: ignore
except Exception:
    try:
        from db import engine as ENGINE  # type: ignore
    except Exception:
        # Last resort: build engine from env
        from sqlalchemy import create_engine

        DATABASE_URL = os.getenv(
            "DATABASE_URL", "postgresql+psycopg://trader:trader123@db:5432/mt5_trading"
        )
        ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
        logger.info(f"Created ENGINE from DATABASE_URL: {DATABASE_URL}")

STATE_KEY = "tick_agg_last_received_at"


def _ensure_state_table(conn) -> None:
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS public.aggregator_state (
              key text PRIMARY KEY,
              value text NOT NULL
            )
            """
        )
    )


def _get_last_received_at(conn) -> datetime:
    res = conn.execute(
        text("SELECT value FROM public.aggregator_state WHERE key=:k"),
        {"k": STATE_KEY},
    ).fetchone()
    if res and res[0]:
        try:
            return datetime.fromisoformat(res[0])
        except Exception:
            pass
    # default: start of epoch UTC
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


def _set_last_received_at(conn, dt: datetime) -> None:
    conn.execute(
        text(
            """
            INSERT INTO public.aggregator_state(key, value)
            VALUES (:k, :v)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """
        ),
        {"k": STATE_KEY, "v": dt.isoformat()},
    )


def aggregate_ticks_to_m1() -> dict:
    """Aggregates ticks from market_data_raw into M1 candles and upserts into market_data.
    Returns a small summary dict.
    """
    now = datetime.now(timezone.utc)
    with ENGINE.begin() as conn:
        _ensure_state_table(conn)
        last = _get_last_received_at(conn)

        # Aggregate ticks from JSONB into M1 OHLCV using SQL
        # mid price = (bid+ask)/2 fallback to bid/ask when missing
        inserted = 0
        updated = 0

        agg_sql = text(
            """
            WITH rows AS (
              SELECT
                (t.tick->>'symbol')::text AS symbol,
                (t.tick->>'ts')::timestamptz AS ts,
                (t.tick->>'bid')::double precision AS bid,
                (t.tick->>'ask')::double precision AS ask,
                (t.tick->>'spread')::double precision AS spread,
                (t.tick->>'volume')::double precision AS volume
              FROM public.market_data_raw r
              CROSS JOIN LATERAL jsonb_array_elements(r.payload->'ticks') t(tick)
              WHERE r.received_at > :last AND r.received_at <= :upto
            ), m AS (
              SELECT
                date_trunc('minute', ts) AS ts_bucket,
                symbol,
                (ARRAY_AGG(COALESCE((bid+ask)/2.0, bid, ask) ORDER BY ts ASC))[1] AS open,
                MAX(COALESCE((bid+ask)/2.0, bid, ask)) AS high,
                MIN(COALESCE((bid+ask)/2.0, bid, ask)) AS low,
                (ARRAY_AGG(COALESCE((bid+ask)/2.0, bid, ask) ORDER BY ts DESC))[1] AS close,
                SUM(COALESCE(volume, 0)) AS volume,
                AVG(spread) AS spread
              FROM rows
              WHERE ts IS NOT NULL AND symbol IS NOT NULL
              GROUP BY 1,2
            )
            INSERT INTO public.market_data
              (ts, symbol, timeframe, open, high, low, close, volume, spread)
            SELECT ts_bucket, symbol, 'M1', open, high, low, close, volume, spread
            FROM m
            ON CONFLICT (symbol, timeframe, ts) DO UPDATE SET
              open = EXCLUDED.open,
              high = EXCLUDED.high,
              low = EXCLUDED.low,
              close = EXCLUDED.close,
              volume = EXCLUDED.volume,
              spread = EXCLUDED.spread
            RETURNING (xmax = 0) AS inserted
            """
        )

        res = conn.execute(agg_sql, {"last": last, "upto": now}).fetchall()
        for r in res:
            if r[0]:
                inserted += 1
            else:
                updated += 1

        _set_last_received_at(conn, now)

        return {
            "inserted": inserted,
            "updated": updated,
            "from": last.isoformat(),
            "to": now.isoformat(),
        }


_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    _shutdown_requested = True


def run_loop(interval_sec: int = 5):
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    logger.info(f"Tick Aggregator started with interval={interval_sec}s")

    while not _shutdown_requested:
        try:
            summary = aggregate_ticks_to_m1()
            logger.info(f"Aggregated ticks: {summary}")
        except Exception as e:
            logger.error(f"Error aggregating ticks: {e}", exc_info=True)

        # Sleep in smaller increments to respond faster to shutdown
        for _ in range(interval_sec):
            if _shutdown_requested:
                break
            time.sleep(1)

    logger.info("Tick Aggregator stopped gracefully")
    sys.exit(0)
