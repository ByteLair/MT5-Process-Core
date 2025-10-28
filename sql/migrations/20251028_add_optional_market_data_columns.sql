-- Migration: add optional price and indicator columns to market_data
-- Apply in staging first, then production after verification.

ALTER TABLE IF EXISTS public.market_data
  ADD COLUMN IF NOT EXISTS bid numeric(18,8),
  ADD COLUMN IF NOT EXISTS ask numeric(18,8),
  ADD COLUMN IF NOT EXISTS spread numeric(18,8),
  ADD COLUMN IF NOT EXISTS rsi numeric(10,4),
  ADD COLUMN IF NOT EXISTS macd numeric(10,4),
  ADD COLUMN IF NOT EXISTS macd_signal numeric(10,4),
  ADD COLUMN IF NOT EXISTS macd_hist numeric(10,4),
  ADD COLUMN IF NOT EXISTS atr numeric(10,4),
  ADD COLUMN IF NOT EXISTS bb_upper numeric(18,8),
  ADD COLUMN IF NOT EXISTS bb_middle numeric(18,8),
  ADD COLUMN IF NOT EXISTS bb_lower numeric(18,8);

-- NOTE: For Timescale hypertables the ALTER TABLE is fine; indexes/constraints may be added later if needed.
