#!/bin/bash
echo "=== MONITOR MT5 DATA COLLECTOR ==="
echo "Hora: $(date)"

# Verificar total de registros
echo -n "📊 Total no banco: "
docker compose exec postgres psql -U trader -d mt5_trading -t -c "SELECT COUNT(*) FROM market_data;"

# Verificar último registro
echo "🕐 Último registro:"
docker compose exec postgres psql -U trader -d mt5_trading -t -c "SELECT symbol, timeframe, timestamp, trading_signal, confidence_score FROM market_data ORDER BY timestamp DESC LIMIT 1;"

# Verificar saúde da API
echo "❤️  Status API:"
curl -s http://localhost:8001/health | jq '.status'

echo "================================"
