#!/usr/bin/env bash
set -euo pipefail
API_KEY="${API_KEY:-supersecretkey}"


curl -sS -X POST "http://localhost:8001/ingest/bulk" \
-H "Content-Type: application/json" \
-H "X-API-Key: $API_KEY" \
-d '{
"items": [
{"ts": "2025-10-05T22:00:00Z", "symbol": "BTCUSD", "timeframe": "M1", "open": 60000, "high": 60100, "low": 59900, "close": 60050, "volume": 10.5},
{"ts": "2025-10-05T22:01:00Z", "symbol": "BTCUSD", "timeframe": "M1", "open": 60050, "high": 60200, "low": 60000, "close": 60120, "volume": 11.1}
]
}' | jq .
