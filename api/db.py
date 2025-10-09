import os
from typing import List, Mapping, Any
import asyncpg
import orjson

# DSN a partir do .env (ou defaults sensatos)
DB_DSN = "postgresql://{user}:{pwd}@{host}:{port}/{db}".format(
    user=os.getenv("POSTGRES_USER", "postgres"),
    pwd=os.getenv("POSTGRES_PASSWORD", "postgres"),
    host=os.getenv("POSTGRES_HOST", "mt5_db"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    db=os.getenv("POSTGRES_DB", "trading"),
)

POOL_MIN = int(os.getenv("DB_POOL_MIN", "2"))
POOL_MAX = int(os.getenv("DB_POOL_MAX", "12"))

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Cria (lazy) e retorna o pool de conexões."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=DB_DSN,
            min_size=POOL_MIN,
            max_size=POOL_MAX,
            timeout=10,
        )
    return _pool


async def insert_batch(rows: List[Mapping[str, Any]]):
    """
    Insere (UPSERT) um lote de registros em 'market_data' usando jsonb_to_recordset.
    IMPORTANTE: o parâmetro $1 precisa ser JSON (texto) — por isso usamos orjson.dumps.
    """
    if not rows:
        return

    pool = await get_pool()

    sql = """
    INSERT INTO market_data
      (ts, symbol, timeframe, open, high, low, close, volume, spread, meta)
    SELECT x.ts, x.symbol, x.timeframe, x.open, x.high, x.low, x.close, x.volume, x.spread, x.meta::jsonb
    FROM jsonb_to_recordset($1::jsonb) AS x(
      ts timestamptz,
      symbol text,
      timeframe text,
      open double precision,
      high double precision,
      low double precision,
      close double precision,
      volume bigint,
      spread double precision,
      meta jsonb
    )
    ON CONFLICT (symbol, timeframe, ts) DO UPDATE SET
      open   = EXCLUDED.open,
      high   = EXCLUDED.high,
      low    = EXCLUDED.low,
      close  = EXCLUDED.close,
      volume = EXCLUDED.volume,
      spread = EXCLUDED.spread,
      meta   = COALESCE(market_data.meta, '{}'::jsonb) || COALESCE(EXCLUDED.meta, '{}'::jsonb);
    """

    # <-- HOTFIX: garantir que $1 seja JSON real (texto), não lista Python
    data_json_text = orjson.dumps([dict(r) for r in rows]).decode("utf-8")

    async with pool.acquire() as conn:
        await conn.execute(sql, data_json_text)
