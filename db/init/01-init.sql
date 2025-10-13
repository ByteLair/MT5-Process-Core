CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS public.market_data(
  symbol    TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  ts        TIMESTAMPTZ NOT NULL,
  open      DOUBLE PRECISION,
  high      DOUBLE PRECISION,
  low       DOUBLE PRECISION,
  close     DOUBLE PRECISION,
  volume    DOUBLE PRECISION,
  spread    DOUBLE PRECISION,
  rsi       DOUBLE PRECISION,
  macd      DOUBLE PRECISION,
  macd_signal DOUBLE PRECISION,
  macd_hist DOUBLE PRECISION,
  atr       DOUBLE PRECISION,
  bb_upper  DOUBLE PRECISION,
  bb_middle DOUBLE PRECISION,
  bb_lower  DOUBLE PRECISION,
  PRIMARY KEY(symbol, timeframe, ts)
);

SELECT create_hypertable('public.market_data','ts', if_not_exists=>TRUE);
ALTER TABLE public.market_data
  SET (timescaledb.compress=true, timescaledb.compress_segmentby='symbol,timeframe');
SELECT add_compression_policy('public.market_data', INTERVAL '7 days');
SELECT add_retention_policy('public.market_data', INTERVAL '90 days');

CREATE OR REPLACE VIEW public.market_data_latest AS
SELECT DISTINCT ON (symbol, timeframe)
  symbol, timeframe, ts, open, high, low, close, volume, spread
FROM public.market_data
ORDER BY symbol, timeframe, ts DESC;
