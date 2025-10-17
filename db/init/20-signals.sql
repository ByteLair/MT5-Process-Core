CREATE TABLE IF NOT EXISTS public.signals_queue (
  id         TEXT PRIMARY KEY,
  ts         TIMESTAMPTZ NOT NULL DEFAULT now(),
  account_id TEXT,
  symbol     TEXT NOT NULL,
  timeframe  TEXT NOT NULL,
  side       TEXT NOT NULL CHECK (side IN ('BUY','SELL','CLOSE','NONE')),
  confidence DOUBLE PRECISION,
  sl_pips    INT,
  tp_pips    INT,
  ttl_sec    INT NOT NULL DEFAULT 90,
  status     TEXT NOT NULL DEFAULT 'PENDING',
  meta       JSONB
);
CREATE INDEX IF NOT EXISTS ix_sigq_sym_tf_ts ON public.signals_queue(symbol,timeframe,ts DESC);

CREATE TABLE IF NOT EXISTS public.signals_ack (
  id          TEXT NOT NULL,
  acked_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  account_id  TEXT,
  symbol      TEXT,
  side        TEXT,
  mt5_ticket  BIGINT,
  price       DOUBLE PRECISION,
  status      TEXT NOT NULL,
  ts_exec     TIMESTAMPTZ,
  PRIMARY KEY (id, acked_at)
);