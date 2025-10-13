CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS public.market_data(
  ts timestamptz NOT NULL,
  symbol text NOT NULL,
  timeframe text NOT NULL,
  open double precision,
  high double precision,
  low double precision,
  close double precision,
  volume double precision,
  spread double precision,
  bid double precision,
  ask double precision,
  rsi double precision,
  macd double precision,
  macd_signal double precision,
  macd_hist double precision,
  atr double precision,
  bb_upper double precision,
  bb_middle double precision,
  bb_lower double precision,
  PRIMARY KEY (symbol, timeframe, ts)
);

SELECT create_hypertable('public.market_data','ts', if_not_exists => TRUE);

ALTER TABLE public.market_data
  SET (timescaledb.compress = TRUE,
       timescaledb.compress_segmentby = 'symbol,timeframe');

SELECT add_compression_policy('public.market_data', INTERVAL '7 days');
SELECT add_retention_policy('public.market_data',   INTERVAL '90 days');

CREATE TABLE IF NOT EXISTS public.market_data_raw(
  received_at timestamptz NOT NULL DEFAULT now(),
  source text NOT NULL,
  payload jsonb NOT NULL
);
SELECT create_hypertable('public.market_data_raw','received_at', if_not_exists=>TRUE);
