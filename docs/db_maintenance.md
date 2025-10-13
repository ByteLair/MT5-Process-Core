# docs/db_maintenance.md
- After bulk loads: `VACUUM ANALYZE public.market_data;`
- Ensure index on (symbol,timeframe,ts DESC).
- Timescale compression/retention already configured; validate jobs.
