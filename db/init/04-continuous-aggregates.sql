-- Continuous Aggregates para timeframes maiores
-- Automatiza agregação de M1 para M5, M15, M30, H1, H4, D1
-- TimescaleDB atualiza essas views automaticamente de forma incremental

-- M5 (5 minutos)
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_m5
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('5 minutes', ts) AS ts,
  symbol,
  'M5' AS timeframe,
  (array_agg(open ORDER BY ts ASC))[1] AS open,
  MAX(high) AS high,
  MIN(low) AS low,
  (array_agg(close ORDER BY ts DESC))[1] AS close,
  SUM(volume) AS volume,
  AVG(spread) AS spread,
  AVG(bid) AS bid,
  AVG(ask) AS ask,
  AVG(rsi) AS rsi,
  AVG(macd) AS macd,
  AVG(macd_signal) AS macd_signal,
  AVG(macd_hist) AS macd_hist,
  AVG(atr) AS atr,
  AVG(bb_upper) AS bb_upper,
  AVG(bb_middle) AS bb_middle,
  AVG(bb_lower) AS bb_lower
FROM market_data
WHERE timeframe = 'M1'
GROUP BY time_bucket('5 minutes', ts), symbol
WITH NO DATA;

-- Política de refresh automática (a cada 1 minuto, processa últimas 10 mins)
SELECT add_continuous_aggregate_policy('market_data_m5',
  start_offset => INTERVAL '10 minutes',
  end_offset => INTERVAL '1 minute',
  schedule_interval => INTERVAL '1 minute',
  if_not_exists => TRUE
);

-- M15 (15 minutos)
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_m15
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('15 minutes', ts) AS ts,
  symbol,
  'M15' AS timeframe,
  (array_agg(open ORDER BY ts ASC))[1] AS open,
  MAX(high) AS high,
  MIN(low) AS low,
  (array_agg(close ORDER BY ts DESC))[1] AS close,
  SUM(volume) AS volume,
  AVG(spread) AS spread,
  AVG(bid) AS bid,
  AVG(ask) AS ask,
  AVG(rsi) AS rsi,
  AVG(macd) AS macd,
  AVG(macd_signal) AS macd_signal,
  AVG(macd_hist) AS macd_hist,
  AVG(atr) AS atr,
  AVG(bb_upper) AS bb_upper,
  AVG(bb_middle) AS bb_middle,
  AVG(bb_lower) AS bb_lower
FROM market_data
WHERE timeframe = 'M1'
GROUP BY time_bucket('15 minutes', ts), symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('market_data_m15',
  start_offset => INTERVAL '30 minutes',
  end_offset => INTERVAL '1 minute',
  schedule_interval => INTERVAL '5 minutes',
  if_not_exists => TRUE
);

-- M30 (30 minutos)
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_m30
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('30 minutes', ts) AS ts,
  symbol,
  'M30' AS timeframe,
  (array_agg(open ORDER BY ts ASC))[1] AS open,
  MAX(high) AS high,
  MIN(low) AS low,
  (array_agg(close ORDER BY ts DESC))[1] AS close,
  SUM(volume) AS volume,
  AVG(spread) AS spread,
  AVG(bid) AS bid,
  AVG(ask) AS ask,
  AVG(rsi) AS rsi,
  AVG(macd) AS macd,
  AVG(macd_signal) AS macd_signal,
  AVG(macd_hist) AS macd_hist,
  AVG(atr) AS atr,
  AVG(bb_upper) AS bb_upper,
  AVG(bb_middle) AS bb_middle,
  AVG(bb_lower) AS bb_lower
FROM market_data
WHERE timeframe = 'M1'
GROUP BY time_bucket('30 minutes', ts), symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('market_data_m30',
  start_offset => INTERVAL '1 hour',
  end_offset => INTERVAL '1 minute',
  schedule_interval => INTERVAL '10 minutes',
  if_not_exists => TRUE
);

-- H1 (1 hora)
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_h1
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', ts) AS ts,
  symbol,
  'H1' AS timeframe,
  (array_agg(open ORDER BY ts ASC))[1] AS open,
  MAX(high) AS high,
  MIN(low) AS low,
  (array_agg(close ORDER BY ts DESC))[1] AS close,
  SUM(volume) AS volume,
  AVG(spread) AS spread,
  AVG(bid) AS bid,
  AVG(ask) AS ask,
  AVG(rsi) AS rsi,
  AVG(macd) AS macd,
  AVG(macd_signal) AS macd_signal,
  AVG(macd_hist) AS macd_hist,
  AVG(atr) AS atr,
  AVG(bb_upper) AS bb_upper,
  AVG(bb_middle) AS bb_middle,
  AVG(bb_lower) AS bb_lower
FROM market_data
WHERE timeframe = 'M1'
GROUP BY time_bucket('1 hour', ts), symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('market_data_h1',
  start_offset => INTERVAL '2 hours',
  end_offset => INTERVAL '5 minutes',
  schedule_interval => INTERVAL '15 minutes',
  if_not_exists => TRUE
);

-- H4 (4 horas)
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_h4
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('4 hours', ts) AS ts,
  symbol,
  'H4' AS timeframe,
  (array_agg(open ORDER BY ts ASC))[1] AS open,
  MAX(high) AS high,
  MIN(low) AS low,
  (array_agg(close ORDER BY ts DESC))[1] AS close,
  SUM(volume) AS volume,
  AVG(spread) AS spread,
  AVG(bid) AS bid,
  AVG(ask) AS ask,
  AVG(rsi) AS rsi,
  AVG(macd) AS macd,
  AVG(macd_signal) AS macd_signal,
  AVG(macd_hist) AS macd_hist,
  AVG(atr) AS atr,
  AVG(bb_upper) AS bb_upper,
  AVG(bb_middle) AS bb_middle,
  AVG(bb_lower) AS bb_lower
FROM market_data
WHERE timeframe = 'M1'
GROUP BY time_bucket('4 hours', ts), symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('market_data_h4',
  start_offset => INTERVAL '8 hours',
  end_offset => INTERVAL '10 minutes',
  schedule_interval => INTERVAL '30 minutes',
  if_not_exists => TRUE
);

-- D1 (1 dia)
CREATE MATERIALIZED VIEW IF NOT EXISTS market_data_d1
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 day', ts) AS ts,
  symbol,
  'D1' AS timeframe,
  (array_agg(open ORDER BY ts ASC))[1] AS open,
  MAX(high) AS high,
  MIN(low) AS low,
  (array_agg(close ORDER BY ts DESC))[1] AS close,
  SUM(volume) AS volume,
  AVG(spread) AS spread,
  AVG(bid) AS bid,
  AVG(ask) AS ask,
  AVG(rsi) AS rsi,
  AVG(macd) AS macd,
  AVG(macd_signal) AS macd_signal,
  AVG(macd_hist) AS macd_hist,
  AVG(atr) AS atr,
  AVG(bb_upper) AS bb_upper,
  AVG(bb_middle) AS bb_middle,
  AVG(bb_lower) AS bb_lower
FROM market_data
WHERE timeframe = 'M1'
GROUP BY time_bucket('1 day', ts), symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy('market_data_d1',
  start_offset => INTERVAL '2 days',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour',
  if_not_exists => TRUE
);

-- Refresh inicial das views (executar após popular market_data com M1)
-- CALL refresh_continuous_aggregate('market_data_m5', NULL, NULL);
-- CALL refresh_continuous_aggregate('market_data_m15', NULL, NULL);
-- CALL refresh_continuous_aggregate('market_data_m30', NULL, NULL);
-- CALL refresh_continuous_aggregate('market_data_h1', NULL, NULL);
-- CALL refresh_continuous_aggregate('market_data_h4', NULL, NULL);
-- CALL refresh_continuous_aggregate('market_data_d1', NULL, NULL);
