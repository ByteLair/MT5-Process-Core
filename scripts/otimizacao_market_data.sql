CREATE UNIQUE INDEX IF NOT EXISTS ux_md ON market_data (symbol, timeframe, ts);
DELETE FROM market_data a
USING market_data b
WHERE
    a.ctid < b.ctid
    AND a.symbol = b.symbol AND a.timeframe = b.timeframe AND a.ts = b.ts;
SELECT add_compression_policy('market_data', INTERVAL '30 days');
