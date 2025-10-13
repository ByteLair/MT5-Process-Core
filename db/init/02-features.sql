CREATE OR REPLACE VIEW public.features_m1 AS
SELECT
  md.symbol,
  md.timeframe,
  md.ts,
  md.close,
  md.volume,
  md.spread,
  md.rsi,
  md.macd,
  md.macd_signal,
  md.macd_hist,
  md.atr,
  lag(md.close, 1) OVER (PARTITION BY md.symbol, md.timeframe ORDER BY md.ts) AS close_t1,
  (md.close - lag(md.close,1) OVER (PARTITION BY md.symbol, md.timeframe ORDER BY md.ts)) AS ret_1,
  avg(md.close) OVER (
    PARTITION BY md.symbol, md.timeframe
    ORDER BY md.ts ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
  ) AS ma60
FROM public.market_data md
WHERE md.timeframe = 'M1';

CREATE OR REPLACE VIEW public.labels_m1 AS
SELECT
  symbol, timeframe, ts,
  lead(close, 5) OVER (PARTITION BY symbol, timeframe ORDER BY ts) AS close_t5,
  (lead(close,5) OVER (PARTITION BY symbol, timeframe ORDER BY ts) - close) / NULLIF(close,0) AS fwd_ret_5
FROM public.market_data
WHERE timeframe='M1';

CREATE OR REPLACE VIEW public.trainset_m1 AS
SELECT
  f.symbol, f.ts,
  f.close, f.volume, f.spread, f.rsi,
  f.macd, f.macd_signal, f.macd_hist, f.atr,
  f.ma60, f.ret_1,
  l.fwd_ret_5
FROM public.features_m1 f
JOIN public.labels_m1 l
  ON f.symbol=l.symbol AND f.timeframe='M1' AND l.timeframe='M1' AND f.ts=l.ts
WHERE f.ma60 IS NOT NULL AND f.ret_1 IS NOT NULL;
