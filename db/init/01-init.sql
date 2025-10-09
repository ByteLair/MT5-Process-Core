-- init-scripts/01_init.sql
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Exemplo de tabela base (ajuste nomes/colunas conforme seu ingest)
CREATE TABLE IF NOT EXISTS candles_m1 (
    ts        TIMESTAMPTZ      NOT NULL,
    symbol    TEXT             NOT NULL,
    open      DOUBLE PRECISION NOT NULL,
    high      DOUBLE PRECISION NOT NULL,
    low       DOUBLE PRECISION NOT NULL,
    close     DOUBLE PRECISION NOT NULL,
    volume    DOUBLE PRECISION NOT NULL,
    CONSTRAINT pk_candles_m1 PRIMARY KEY (symbol, ts)
);

SELECT create_hypertable('candles_m1', by_range('ts'), if_not_exists => TRUE);

-- Índices úteis
CREATE INDEX IF NOT EXISTS idx_candles_m1_ts    ON candles_m1 (ts DESC);
CREATE INDEX IF NOT EXISTS idx_candles_m1_symts ON candles_m1 (symbol, ts DESC);

-- Política de compressão (opcional)
ALTER TABLE candles_m1 SET (
  timescaledb.compress = TRUE
);
SELECT add_compression_policy('candles_m1', INTERVAL '3 days');

-- Política de retenção (opcional)
-- SELECT add_retention_policy('candles_m1', INTERVAL '365 days');
