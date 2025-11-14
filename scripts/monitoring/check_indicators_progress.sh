#!/bin/bash
# Monitor progresso do cálculo de indicadores M1

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   📊 MONITORAMENTO - CÁLCULO DE INDICADORES M1              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

while true; do
    clear
    echo "🔄 Atualizado em: $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Status do processo
    echo "📌 Status do Processo:"
    docker exec mt5_api ps aux | grep -E "calculate_all_indicators" | grep -v grep || echo "   ⚠️  Processo não está rodando"
    echo ""
    
    # Progresso no banco
    echo "📈 Progresso no Banco de Dados:"
    docker exec mt5_db psql -U trader -d mt5_trading -t -A -F'|' -c "
        SELECT 
            timeframe,
            COUNT(*) as total,
            COUNT(rsi) as com_indicadores,
            ROUND(100.0 * COUNT(rsi) / COUNT(*), 2) as percentual,
            CASE 
                WHEN COUNT(rsi) = 0 THEN 'Iniciando...'
                WHEN COUNT(rsi) < COUNT(*) THEN 'Em progresso ⏳'
                ELSE 'Concluído ✅'
            END as status
        FROM market_data 
        WHERE symbol='EURUSD' 
        GROUP BY timeframe
        ORDER BY timeframe;
    " | while IFS='|' read -r tf total com_ind pct status; do
        printf "   %-5s │ %10s candles │ %10s com indicadores │ %6s%% │ %s\n" "$tf" "$total" "$com_ind" "$pct" "$status"
    done
    echo ""
    
    # Estimativa de tempo
    echo "⏱️  Estimativa:"
    CURRENT=$(docker exec mt5_db psql -U trader -d mt5_trading -t -A -c "SELECT COUNT(rsi) FROM market_data WHERE symbol='EURUSD' AND timeframe='M1';")
    TOTAL=1877965
    if [ "$CURRENT" -gt 0 ]; then
        PERCENT=$(echo "scale=2; $CURRENT * 100 / $TOTAL" | bc)
        REMAINING=$((TOTAL - CURRENT))
        # Assumindo ~200 registros/segundo
        SECONDS_LEFT=$((REMAINING / 200))
        MINUTES_LEFT=$((SECONDS_LEFT / 60))
        echo "   Progresso: $CURRENT / $TOTAL candles ($PERCENT%)"
        echo "   Restante: $REMAINING candles (~$MINUTES_LEFT minutos)"
        
        # Barra de progresso
        BARS=$((CURRENT * 50 / TOTAL))
        printf "   ["
        printf "%${BARS}s" | tr ' ' '█'
        printf "%$((50-BARS))s" | tr ' ' '░'
        printf "] $PERCENT%%\n"
    else
        echo "   Aguardando início do processamento..."
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Pressione Ctrl+C para sair | Atualiza a cada 30 segundos"
    
    sleep 30
done
