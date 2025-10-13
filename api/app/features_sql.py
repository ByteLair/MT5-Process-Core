from textwrap import dedent


FEATURES_SQL = dedent(
"""
SELECT
symbol, timeframe, ts,
close, volume, spread, rsi,
macd, macd_signal, macd_hist, atr,
avg(close) OVER (
PARTITION BY symbol, timeframe
ORDER BY ts ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
) AS ma60,
(close - lag(close,1) OVER (PARTITION BY symbol, timeframe ORDER BY ts)) AS ret_1
FROM public.market_data
WHERE timeframe='M1' AND symbol = :symbol
AND ts >= now() - interval '120 minutes'
ORDER BY ts
LIMIT 2000
"""
)


LATEST_WINDOW_SQL = dedent(
"""
SELECT * FROM (
SELECT ts, close, volume, spread, rsi,
macd, macd_signal, macd_hist, atr,
avg(close) OVER (
PARTITION BY symbol, timeframe
ORDER BY ts ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
) AS ma60,
(close - lag(close,1) OVER (PARTITION BY symbol, timeframe ORDER BY ts)) AS ret_1
FROM public.market_data
WHERE timeframe='M1' AND symbol=:symbol
ORDER BY ts DESC
LIMIT :lookback
) sub
ORDER BY ts
"""
)