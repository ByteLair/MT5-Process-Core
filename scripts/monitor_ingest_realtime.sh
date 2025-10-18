#!/bin/bash
# Script de monitoramento em tempo real da ingestão de dados

clear
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         MONITOR DE INGESTÃO MT5 - TEMPO REAL                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Pressione Ctrl+C para sair"
echo ""

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

while true; do
    # Move cursor para o topo
    tput cup 5 0
    
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}⏰ $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Total de registros
    TOTAL=$(docker-compose exec -T db psql -U trader -d mt5_trading -t -c \
        "SELECT COUNT(*) FROM market_data;" 2>/dev/null | tr -d ' ')
    echo -e "${GREEN}📊 Total de registros: ${TOTAL}${NC}"
    echo ""
    
    # Registros nos últimos períodos
    echo -e "${YELLOW}📈 Novos registros:${NC}"
    LAST_1MIN=$(docker-compose exec -T db psql -U trader -d mt5_trading -t -c \
        "SELECT COUNT(*) FROM market_data WHERE ts > NOW() - INTERVAL '1 minute';" 2>/dev/null | tr -d ' ')
    LAST_5MIN=$(docker-compose exec -T db psql -U trader -d mt5_trading -t -c \
        "SELECT COUNT(*) FROM market_data WHERE ts > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')
    LAST_10MIN=$(docker-compose exec -T db psql -U trader -d mt5_trading -t -c \
        "SELECT COUNT(*) FROM market_data WHERE ts > NOW() - INTERVAL '10 minutes';" 2>/dev/null | tr -d ' ')
    
    echo -e "  └─ Último 1 minuto:  ${LAST_1MIN}"
    echo -e "  └─ Últimos 5 minutos: ${LAST_5MIN}"
    echo -e "  └─ Últimos 10 minutos: ${LAST_10MIN}"
    echo ""
    
    # Últimos 5 registros
    echo -e "${YELLOW}🔍 Últimos 5 registros:${NC}"
    docker-compose exec -T db psql -U trader -d mt5_trading -t -c \
        "SELECT 
            TO_CHAR(ts, 'HH24:MI:SS') as hora,
            symbol,
            timeframe as tf,
            ROUND(close::numeric, 5) as close,
            volume
         FROM market_data 
         ORDER BY ts DESC 
         LIMIT 5;" 2>/dev/null
    
    echo ""
    echo -e "${YELLOW}📡 Últimas requisições POST na API:${NC}"
    docker-compose logs --tail=20 api 2>/dev/null | grep "POST /ingest" | tail -5 || echo "  Nenhuma requisição POST encontrada"
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "Atualizando em 5 segundos... (Ctrl+C para sair)"
    
    sleep 5
done
