#!/bin/bash
###############################################################################
# Monitor do Downloader
# 
# Verifica progresso e envia alertas se necessário
# Pode ser executado via cron a cada 15 minutos
###############################################################################

CHECKPOINT_FILE="/var/lib/docker/volumes/downloader_data/_data/checkpoint.json"
ALERT_EMAIL="admin@example.com"  # Configurar email

# Verificar se container está rodando
if ! docker ps | grep -q dukascopy_downloader; then
    echo "❌ ALERTA: Container dukascopy_downloader não está rodando!"
    # Tentar reiniciar
    docker-compose -f docker/docker-compose.downloader.yml up -d dukascopy_downloader
    exit 1
fi

# Verificar checkpoint
if [ -f "$CHECKPOINT_FILE" ]; then
    LAST_DATE=$(docker exec dukascopy_downloader cat /app/data/checkpoint.json 2>/dev/null | jq -r '.last_date')
    UPDATED_AT=$(docker exec dukascopy_downloader cat /app/data/checkpoint.json 2>/dev/null | jq -r '.updated_at')
    
    echo "✅ Container rodando"
    echo "📅 Última data processada: $LAST_DATE"
    echo "🕒 Última atualização: $UPDATED_AT"
    
    # Verificar se está travado (sem atualização há mais de 15 minutos)
    LAST_UPDATE_TIMESTAMP=$(date -d "$UPDATED_AT" +%s 2>/dev/null || echo 0)
    NOW=$(date +%s)
    DIFF=$((NOW - LAST_UPDATE_TIMESTAMP))
    
    if [ $DIFF -gt 900 ]; then  # 15 minutos
        echo "⚠️ ALERTA: Checkpoint não atualiza há $(($DIFF / 60)) minutos!"
        echo "🔄 Reiniciando container..."
        docker-compose -f docker/docker-compose.downloader.yml restart dukascopy_downloader
    fi
else
    echo "⚠️ Checkpoint ainda não foi criado (container iniciou recentemente)"
fi

# Mostrar uso de memória
MEM_USAGE=$(docker stats dukascopy_downloader --no-stream --format "{{.MemUsage}}")
echo "💾 Uso de memória: $MEM_USAGE"
