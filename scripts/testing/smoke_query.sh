#!/usr/bin/env bash
set -euo pipefail
API=${API_URL:-http://localhost:8001}
KEY=${API_KEY:-changeme}
curl -s -H "X-API-Key: $KEY" "$API/health" | jq .
curl -s -H "X-API-Key: $KEY" "$API/predict?symbol=EURUSD" | jq .
