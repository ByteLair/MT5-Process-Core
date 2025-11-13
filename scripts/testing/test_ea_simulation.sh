#!/bin/bash
# Script para simular envio de candles pelo EA (útil para testes)

API_URL="${API_URL:-http://localhost:18001}"
API_KEY="${API_KEY:-supersecretkey}"
SYMBOL="${SYMBOL:-EURUSD}"
TIMEFRAME="${TIMEFRAME:-M1}"

echo "🧪 SIMULADOR DE EA - Teste de Ingestão"
echo "======================================"
echo "API URL: $API_URL"
echo "Symbol: $SYMBOL"
echo "Timeframe: $TIMEFRAME"
echo ""

# Função para gerar timestamp ISO 8601
get_timestamp() {
    date -u -d "$1 minutes ago" +"%Y-%m-%dT%H:%M:00Z"
}

# Função para gerar preço aleatório próximo a um valor base
generate_price() {
    local base=$1
    local variation=$(awk -v seed=$RANDOM 'BEGIN{srand(seed); print rand()*0.001-0.0005}')
    echo "$base + $variation" | bc -l | xargs printf "%.5f"
}

# Simula 10 candles dos últimos 10 minutos
echo "📤 Enviando 10 candles de teste..."
echo ""

BASE_PRICE=1.0850
SUCCESS=0
FAILED=0

for i in {9..0}; do
    TIMESTAMP=$(get_timestamp $i)
    OPEN=$(generate_price $BASE_PRICE)
    HIGH=$(generate_price $(echo "$OPEN + 0.0005" | bc -l))
    LOW=$(generate_price $(echo "$OPEN - 0.0003" | bc -l))
    CLOSE=$(generate_price $OPEN)
    VOLUME=$((RANDOM % 1000 + 500))

    JSON=$(cat <<EOF
{
  "ts": "$TIMESTAMP",
  "symbol": "$SYMBOL",
  "timeframe": "$TIMEFRAME",
  "open": $OPEN,
  "high": $HIGH,
  "low": $LOW,
  "close": $CLOSE,
  "volume": $VOLUME
}
EOF
)

    echo "🕐 $TIMESTAMP | Close: $CLOSE | Vol: $VOLUME"

    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/ingest" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$JSON")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)

    if [ "$HTTP_CODE" = "200" ]; then
        echo "  ✅ Enviado com sucesso"
        ((SUCCESS++))
    else
        echo "  ❌ Falha (HTTP $HTTP_CODE): $BODY"
        ((FAILED++))
    fi
    echo ""

    # Pequeno delay para não sobrecarregar
    sleep 0.2
done

echo "======================================"
echo "📊 Resumo:"
echo "  ✅ Sucesso: $SUCCESS"
echo "  ❌ Falhas:  $FAILED"
echo ""
echo "🔍 Verificando no banco de dados..."
docker-compose exec -T db psql -U trader -d mt5_trading -c \
    "SELECT COUNT(*) as novos_registros
     FROM market_data
     WHERE ts > NOW() - INTERVAL '15 minutes'
     AND symbol = '$SYMBOL';"

echo ""
echo "📋 Últimos 5 registros inseridos:"
docker-compose exec -T db psql -U trader -d mt5_trading -c \
    "SELECT ts, symbol, timeframe, close, volume
     FROM market_data
     WHERE symbol = '$SYMBOL'
     ORDER BY ts DESC
     LIMIT 5;"
