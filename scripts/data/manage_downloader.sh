#!/bin/bash
# Gerenciador do downloader Dukascopy
# Uso: ./manage_downloader.sh [start|stop|restart|logs|status]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker/docker-compose.downloader.yml"

ACTION=${1:-start}

case $ACTION in
    start)
        echo "🚀 Iniciando Dukascopy Downloader..."
        echo ""
        
        # Build da imagem
        echo "🔨 Construindo imagem..."
        docker build -f "$PROJECT_ROOT/docker/Dockerfile.downloader" -t mt5-downloader:latest "$PROJECT_ROOT"
        
        echo ""
        echo "📦 Iniciando container..."
        docker-compose -f "$COMPOSE_FILE" up -d
        
        echo ""
        echo "✅ Downloader iniciado!"
        echo ""
        echo "📝 Para ver logs:"
        echo "   $0 logs"
        echo ""
        echo "📊 Para ver status:"
        echo "   $0 status"
        ;;
    
    stop)
        echo "⏹️  Parando Dukascopy Downloader..."
        docker-compose -f "$COMPOSE_FILE" stop
        echo "✅ Downloader parado!"
        ;;
    
    restart)
        echo "🔄 Reiniciando Dukascopy Downloader..."
        docker-compose -f "$COMPOSE_FILE" restart
        echo "✅ Downloader reiniciado!"
        ;;
    
    logs)
        echo "📋 Logs do Dukascopy Downloader (Ctrl+C para sair):"
        echo ""
        docker-compose -f "$COMPOSE_FILE" logs -f --tail=100
        ;;
    
    status)
        echo "📊 Status do Dukascopy Downloader:"
        echo ""
        docker-compose -f "$COMPOSE_FILE" ps
        echo ""
        
        # Verificar se está rodando
        if docker ps | grep -q dukascopy_downloader; then
            echo "✅ Container RODANDO"
            echo ""
            
            # Mostrar últimas linhas do log
            echo "📋 Últimas 10 linhas do log:"
            docker logs dukascopy_downloader --tail 10
            echo ""
            
            # Verificar checkpoint
            echo "🔍 Progresso (checkpoint):"
            docker exec dukascopy_downloader cat /app/data/checkpoint.json 2>/dev/null || echo "   Checkpoint ainda não criado"
            echo ""
            
            # Verificar dados no banco
            echo "📊 Dados no PostgreSQL:"
            docker exec mt5_db psql -U trader -d mt5_trading -c "
                SELECT timeframe, COUNT(*) as candles 
                FROM market_data 
                WHERE symbol = 'EURUSD' 
                  AND timeframe IN ('H1', 'H4', 'D1')
                GROUP BY timeframe 
                ORDER BY timeframe;
            " 2>/dev/null || echo "   Banco ainda sem dados"
        else
            echo "⏹️  Container NÃO está rodando"
            echo ""
            echo "💡 Para iniciar:"
            echo "   $0 start"
        fi
        ;;
    
    *)
        echo "Uso: $0 [start|stop|restart|logs|status]"
        echo ""
        echo "Comandos:"
        echo "  start   - Inicia o downloader"
        echo "  stop    - Para o downloader"
        echo "  restart - Reinicia o downloader"
        echo "  logs    - Mostra logs em tempo real"
        echo "  status  - Mostra status e progresso"
        exit 1
        ;;
esac
