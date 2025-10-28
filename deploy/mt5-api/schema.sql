-- schema.sql
-- Use: psql -d mt5_data -U mt5user -f schema.sql

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Main ticks table
CREATE TABLE IF NOT EXISTS ticks (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    bid DOUBLE PRECISION,
    ask DOUBLE PRECISION,
    last DOUBLE PRECISION,
    volume BIGINT
);

-- Convert to hypertable
SELECT create_hypertable('ticks', 'time', if_not_exists => TRUE, migrate_data => TRUE);

-- Index for fast symbol + time queries
CREATE INDEX IF NOT EXISTS idx_ticks_symbol_time ON ticks (symbol, time DESC);

-- BRIN index for very large time ranges (low maintenance, good for append)
CREATE INDEX IF NOT EXISTS idx_ticks_time_brin ON ticks USING BRIN (time);

-- Set chunk time interval to 1 day (tune depending on load)
SELECT set_chunk_time_interval('ticks', INTERVAL '1 day');

-- Compression
ALTER TABLE ticks SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'symbol'
);

-- Compress chunks older than 7 days
SELECT add_compression_policy('ticks', INTERVAL '7 days');

-- Retention: drop chunks older than 90 days
SELECT add_retention_policy('ticks', INTERVAL '90 days');

-- Continuous aggregate (OHLC 1 minute)
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlc_1min
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 minute', time) AS bucket,
  symbol,
  first(last, time) AS open,
  max(last) AS high,
  min(last) AS low,
  last(last, time) AS close,
  sum(volume) AS volume,
  count(*) AS ticks
FROM ticks
GROUP BY bucket, symbol
WITH NO DATA;

CREATE INDEX IF NOT EXISTS idx_ohlc_1min_symbol_bucket ON ohlc_1min (symbol, bucket DESC);
