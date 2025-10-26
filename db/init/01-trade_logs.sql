CREATE TABLE IF NOT EXISTS trade_logs (
    ts timestamptz NOT NULL,
    signal_id text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    side text NOT NULL,
    lots double precision NOT NULL,
    model_version text NOT NULL,
    PRIMARY KEY (signal_id, ts)
);
SELECT create_hypertable('trade_logs', 'ts', if_not_exists => true);

CREATE TABLE IF NOT EXISTS fills (
    ts timestamptz NOT NULL,
    signal_id text NOT NULL,
    order_id bigint,
    status text NOT NULL,
    price double precision,
    slippage double precision,
    message text
);
SELECT create_hypertable('fills', 'ts', if_not_exists => true);
