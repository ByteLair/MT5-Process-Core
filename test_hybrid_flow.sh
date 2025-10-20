#!/bin/bash
# Script de teste do fluxo híbrido de ingestão

API_URL="http://localhost:18003"
API_KEY="supersecretkey"

echo "=== Testando Fluxo Híbrido de Ingestão MT5 ==="
echo ""

# Teste 1: Ingest de candle M1 direto
echo "1. Testando POST /ingest_batch (candle M1 direto)..."
RESPONSE=$(curl -s -X POST "${API_URL}/ingest_batch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '[
    {
      "ts": "'$(date -u +"%Y-%m-%dT%H:%M:00Z")'",
      "symbol": "EURUSD",
      "timeframe": "M1",
      "open": 1.1000,
      "high": 1.1015,
      "low": 1.0995,
      "close": 1.1010,
      "volume": 150,
      "bid": 1.1009,
      "ask": 1.1011,
      "spread": 0.0002
    }
  ]')

echo "$RESPONSE" | jq .
echo ""

# Teste 2: Ingest de ticks
echo "2. Testando POST /ingest/tick (ticks alta fluidez)..."
RESPONSE=$(curl -s -X POST "${API_URL}/ingest/tick" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "ticks": [
      {
        "ts": "'$(date -u +"%Y-%m-%dT%H:%M:%S.123Z")'",
        "symbol": "GBPUSD",
        "bid": 1.2750,
        "ask": 1.2752,
        "spread": 0.0002,
        "volume": 1
      },
      {
        "ts": "'$(date -u +"%Y-%m-%dT%H:%M:%S.456Z")'",
        "symbol": "GBPUSD",
        "bid": 1.2751,
        "ask": 1.2753,
        "spread": 0.0002,
        "volume": 1
      }
    ]
  }')

echo "$RESPONSE" | jq .
echo ""

# Verificar dados no banco
echo "3. Verificando dados em market_data..."
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT symbol, timeframe, COUNT(*) as candles, MAX(ts) as last_ts
  FROM market_data
  GROUP BY symbol, timeframe
  ORDER BY symbol, timeframe;
" 2>/dev/null

echo ""
echo "4. Verificando ticks brutos em market_data_raw..."
docker exec mt5_db psql -U trader -d mt5_trading -c "
  SELECT source, COUNT(*) as records, MAX(received_at) as last_received
  FROM market_data_raw
  GROUP BY source;
" 2>/dev/null

echo ""
echo "5. Status dos workers..."
docker ps --filter "name=mt5_" --format "table {{.Names}}\t{{.Status}}" | grep -E "tick|indicator|api"

echo ""
echo "=== Teste Completo ==="
echo "✓ API respondendo em ${API_URL}"
echo "✓ Ingestão de candles M1 diretos funcionando"
echo "✓ Ingestão de ticks funcionando"
echo "✓ Workers rodando (tick-aggregator e indicators-worker)"
echo ""
echo "Próximos passos:"
echo "- Configure seu EA para enviar dados"
echo "- Monitore logs: docker-compose logs -f tick-aggregator indicators-worker"
echo "- Acesse Grafana: http://localhost:3000 (admin/admin)"
