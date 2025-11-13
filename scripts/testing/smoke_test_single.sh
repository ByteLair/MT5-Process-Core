#!/usr/bin/env bash
set -euo pipefail
API_KEY="${API_KEY:-supersecretkey}"


curl -sS -X POST "http://localhost:8001/ingest" \
-H "Content-Type: application/json" \
-H "X-API-Key: $API_KEY" \
-d '{
"ts": "2025-10-05T22:00:00",
"symbol": "EURUSD",
"timeframe": "M1",
"open": 1.1000,
"high": 1.1010,
"low": 1.0995,
"close": 1.1005,
"volume": 1234,
"spread": 0.0002,
"indicators": {"rsi": 57.2, "ma_fast": 1.1003},
"meta": {"source": "smoke"}
}' | jq .
