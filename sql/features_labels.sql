CREATE MATERIALIZED VIEW IF NOT EXISTS features_m1 AS
SELECT
  time_bucket('1 minute', time) AS bucket,
  symbol,
  AVG(close) AS mean_close,
  MAX(high)-MIN(low) AS volatility,
  (close - LAG(close) OVER (PARTITION BY symbol ORDER BY time))
    / NULLIF(LAG(close) OVER (PARTITION BY symbol ORDER BY time),0) AS pct_change
FROM market_data
GROUP BY bucket, symbol;

CREATE MATERIALIZED VIEW IF NOT EXISTS labels_m1 AS
SELECT
  f.bucket,
  f.symbol,
  CASE WHEN LEAD(f.mean_close) OVER (PARTITION BY f.symbol ORDER BY f.bucket) > f.mean_close
       THEN 1 ELSE 0 END AS label
FROM features_m1 f;
