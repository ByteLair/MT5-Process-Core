#!/bin/bash
###############################################################################
# System Stability Improvements Script
# 
# Este script aplica melhorias críticas de estabilidade:
# 1. Limpeza de disco (imagens órfãs, logs antigos)
# 2. Configuração de health checks
# 3. Limites de recursos
# 4. Backup automático
# 5. Monitoramento aprimorado
#
# Uso: sudo ./system_stability_improvements.sh [--dry-run]
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DRY_RUN=false

if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 Modo DRY-RUN ativado (apenas simula, não executa)"
fi

cd "$PROJECT_ROOT"

###############################################################################
# 1. Limpeza de Disco
###############################################################################
echo "=================================================="
echo "📦 1. LIMPEZA DE DISCO"
echo "=================================================="

echo "📊 Espaço atual:"
df -h / | grep -E 'Filesystem|/dev/'

echo -e "\n🗑️ Limpando imagens Docker órfãs..."
if [ "$DRY_RUN" = false ]; then
    docker image prune -f
    echo "✅ Imagens órfãs removidas"
else
    docker images -f "dangling=true" -q
    echo "[DRY-RUN] Comandos que seriam executados: docker image prune -f"
fi

echo -e "\n🗑️ Limpando containers parados..."
if [ "$DRY_RUN" = false ]; then
    docker container prune -f
    echo "✅ Containers parados removidos"
else
    docker ps -a --filter "status=exited" -q
    echo "[DRY-RUN] Comando: docker container prune -f"
fi

echo -e "\n🗑️ Limpando volumes não utilizados..."
if [ "$DRY_RUN" = false ]; then
    docker volume prune -f
    echo "✅ Volumes não utilizados removidos"
else
    docker volume ls -qf dangling=true
    echo "[DRY-RUN] Comando: docker volume prune -f"
fi

echo -e "\n🗑️ Limpando logs antigos (>30 dias)..."
if [ "$DRY_RUN" = false ]; then
    find logs/ -type f -name "*.log" -mtime +30 -delete 2>/dev/null || true
    echo "✅ Logs antigos removidos"
else
    find logs/ -type f -name "*.log" -mtime +30 2>/dev/null || echo "Nenhum log antigo"
    echo "[DRY-RUN] Comando: find logs/ -type f -name '*.log' -mtime +30 -delete"
fi

echo -e "\n📊 Espaço após limpeza:"
df -h / | grep -E 'Filesystem|/dev/'

###############################################################################
# 2. Melhorar docker-compose.downloader.yml
###############################################################################
echo -e "\n=================================================="
echo "🐳 2. MELHORANDO DOCKER-COMPOSE DO DOWNLOADER"
echo "=================================================="

DOWNLOADER_COMPOSE="docker/docker-compose.downloader.yml"

if [ -f "$DOWNLOADER_COMPOSE" ]; then
    echo "📝 Adicionando health check, limites de recursos e log rotation..."
    
    if [ "$DRY_RUN" = false ]; then
        # Backup do arquivo original
        cp "$DOWNLOADER_COMPOSE" "${DOWNLOADER_COMPOSE}.bak"
        
        # Criar versão melhorada
        cat > "$DOWNLOADER_COMPOSE" << 'EOF'
version: '3.8'

services:
  dukascopy_downloader:
    build:
      context: ..
      dockerfile: docker/Dockerfile.downloader
    image: mt5-downloader:latest
    container_name: dukascopy_downloader
    restart: unless-stopped
    
    volumes:
      - downloader_data:/app/data
    
    environment:
      - DB_HOST=mt5_db
      - DB_PORT=5432
      - DB_NAME=mt5_trading
      - DB_USER=trader
      - DB_PASSWORD=${DB_PASSWORD}
      - PYTHONUNBUFFERED=1
    
    # Health check: verifica se checkpoint está sendo atualizado
    healthcheck:
      test: |
        python3 -c "
        import json, os
        from datetime import datetime, timedelta
        try:
            with open('/app/data/checkpoint.json') as f:
                data = json.load(f)
                updated = datetime.fromisoformat(data['updated_at'])
                if datetime.now() - updated > timedelta(minutes=10):
                    exit(1)
        except:
            # Primeiro minuto, ainda não criou checkpoint
            if os.path.exists('/app/data/checkpoint.json'):
                exit(1)
        exit(0)
        "
      interval: 5m
      timeout: 10s
      retries: 3
      start_period: 2m
    
    # Limites de recursos
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: "512m"
        reservations:
          cpus: "0.5"
          memory: "256m"
    
    # Log rotation
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"
    
    networks:
      - default

networks:
  default:
    external: true
    name: mt5-process-core_default

volumes:
  downloader_data:
    driver: local
EOF
        echo "✅ docker-compose.downloader.yml atualizado (backup em .bak)"
    else
        echo "[DRY-RUN] Seria criado docker-compose.downloader.yml com:"
        echo "  - healthcheck (checkpoint não pode ficar >10min parado)"
        echo "  - limits: 1 CPU, 512MB RAM"
        echo "  - logging: max-size 50m, max-file 5"
    fi
else
    echo "⚠️ Arquivo $DOWNLOADER_COMPOSE não encontrado"
fi

###############################################################################
# 3. Script de Backup Automático
###############################################################################
echo -e "\n=================================================="
echo "💾 3. CONFIGURANDO BACKUP AUTOMÁTICO"
echo "=================================================="

BACKUP_SCRIPT="scripts/maintenance/backup_database.sh"

echo "📝 Criando script de backup..."
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$(dirname "$BACKUP_SCRIPT")"
    
    cat > "$BACKUP_SCRIPT" << 'EOF'
#!/bin/bash
###############################################################################
# Backup Automático do PostgreSQL
# 
# Cria backup compactado do banco mt5_trading
# Mantém últimos 7 backups diários
###############################################################################

BACKUP_DIR="/home/lair/MT5-Process-Core/backups"
DB_NAME="mt5_trading"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/mt5_trading_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "💾 Iniciando backup do banco $DB_NAME..."
docker exec mt5_db pg_dump -U trader -d "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup concluído: $BACKUP_FILE ($SIZE)"
    
    # Manter apenas últimos 7 backups
    echo "🗑️ Limpando backups antigos (mantém 7)..."
    ls -t "$BACKUP_DIR"/mt5_trading_*.sql.gz | tail -n +8 | xargs -r rm
    
    echo "📊 Backups disponíveis:"
    ls -lh "$BACKUP_DIR"/mt5_trading_*.sql.gz | tail -7
else
    echo "❌ Erro no backup!"
    exit 1
fi
EOF
    
    chmod +x "$BACKUP_SCRIPT"
    echo "✅ Script de backup criado: $BACKUP_SCRIPT"
    
    # Adicionar ao crontab
    echo -e "\n📅 Adicionando ao crontab (diário às 03:00)..."
    CRON_JOB="0 3 * * * $PROJECT_ROOT/$BACKUP_SCRIPT >> $PROJECT_ROOT/logs/backup.log 2>&1"
    
    # Verifica se já existe
    if crontab -l 2>/dev/null | grep -q "backup_database.sh"; then
        echo "⚠️ Já existe entrada no crontab"
    else
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "✅ Crontab configurado"
    fi
else
    echo "[DRY-RUN] Seria criado $BACKUP_SCRIPT"
    echo "[DRY-RUN] Seria adicionado ao crontab: 0 3 * * * backup_database.sh"
fi

###############################################################################
# 4. Script de Monitoramento do Downloader
###############################################################################
echo -e "\n=================================================="
echo "📊 4. CRIANDO MONITORAMENTO DO DOWNLOADER"
echo "=================================================="

MONITOR_SCRIPT="scripts/maintenance/monitor_downloader.sh"

echo "📝 Criando script de monitoramento..."
if [ "$DRY_RUN" = false ]; then
    cat > "$MONITOR_SCRIPT" << 'EOF'
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
EOF
    
    chmod +x "$MONITOR_SCRIPT"
    echo "✅ Script de monitoramento criado: $MONITOR_SCRIPT"
    
    # Adicionar ao crontab
    CRON_JOB="*/15 * * * * $PROJECT_ROOT/$MONITOR_SCRIPT >> $PROJECT_ROOT/logs/downloader_monitor.log 2>&1"
    
    if crontab -l 2>/dev/null | grep -q "monitor_downloader.sh"; then
        echo "⚠️ Já existe entrada no crontab"
    else
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "✅ Monitoramento configurado (a cada 15 minutos)"
    fi
else
    echo "[DRY-RUN] Seria criado $MONITOR_SCRIPT"
    echo "[DRY-RUN] Seria executado a cada 15 minutos via cron"
fi

###############################################################################
# 5. Configurar Alertas do Prometheus
###############################################################################
echo -e "\n=================================================="
echo "🚨 5. CONFIGURANDO ALERTAS DO PROMETHEUS"
echo "=================================================="

ALERT_RULES="prometheus_rules/downloader_alerts.yml"

echo "📝 Criando regras de alerta..."
if [ "$DRY_RUN" = false ]; then
    mkdir -p "$(dirname "$ALERT_RULES")"
    
    cat > "$ALERT_RULES" << 'EOF'
groups:
  - name: downloader_alerts
    interval: 30s
    rules:
      - alert: DownloaderContainerDown
        expr: absent(container_last_seen{name="dukascopy_downloader"}) == 1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Container dukascopy_downloader está parado"
          description: "O container de download não está rodando há mais de 2 minutos"
      
      - alert: DownloaderHighMemory
        expr: container_memory_usage_bytes{name="dukascopy_downloader"} / container_spec_memory_limit_bytes{name="dukascopy_downloader"} > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Downloader usando >90% da memória"
          description: "Uso de memória: {{ $value | humanizePercentage }}"
      
      - alert: DiskSpaceLow
        expr: node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Espaço em disco abaixo de 10%"
          description: "Apenas {{ $value | humanizePercentage }} disponível em /"
      
      - alert: DatabaseDown
        expr: pg_up{instance="mt5_db:5432"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL não está respondendo"
          description: "Banco mt5_db está down"
EOF
    
    echo "✅ Regras de alerta criadas: $ALERT_RULES"
    echo "⚠️ Para ativar, adicione ao prometheus.yml:"
    echo "   rule_files:"
    echo "     - 'prometheus_rules/*.yml'"
else
    echo "[DRY-RUN] Seria criado $ALERT_RULES com alertas para:"
    echo "  - Container down"
    echo "  - Memória alta"
    echo "  - Disco cheio"
    echo "  - Database down"
fi

###############################################################################
# 6. Reiniciar Downloader com Novas Configs
###############################################################################
echo -e "\n=================================================="
echo "🔄 6. APLICANDO MELHORIAS"
echo "=================================================="

if [ "$DRY_RUN" = false ]; then
    echo "🛑 Parando downloader..."
    docker-compose -f docker/docker-compose.downloader.yml down
    
    echo "🏗️ Reconstruindo com novas configurações..."
    docker-compose -f docker/docker-compose.downloader.yml up -d --build
    
    echo "✅ Downloader reiniciado com melhorias"
    
    echo -e "\n📊 Status:"
    docker ps -a | grep dukascopy_downloader
    
    echo -e "\n🔍 Aguardando 10 segundos para verificar health..."
    sleep 10
    docker inspect dukascopy_downloader | jq '.[0].State.Health'
else
    echo "[DRY-RUN] Seria executado:"
    echo "  docker-compose down"
    echo "  docker-compose up -d --build"
fi

###############################################################################
# Resumo
###############################################################################
echo -e "\n=================================================="
echo "✅ RESUMO DAS MELHORIAS APLICADAS"
echo "=================================================="

cat << EOF

1. 🗑️ Limpeza de Disco
   - Imagens órfãs removidas
   - Containers parados removidos
   - Logs antigos removidos (>30 dias)

2. 🐳 Docker Compose Melhorado
   - Health check adicionado (checkpoint <10min)
   - Limites de recursos: 1 CPU, 512MB RAM
   - Log rotation: max 50MB, 5 arquivos

3. 💾 Backup Automático
   - Script criado: scripts/maintenance/backup_database.sh
   - Cron: Diariamente às 03:00
   - Mantém últimos 7 backups

4. 📊 Monitoramento
   - Script criado: scripts/maintenance/monitor_downloader.sh
   - Cron: A cada 15 minutos
   - Auto-restart se travar

5. 🚨 Alertas Prometheus
   - Regras criadas: prometheus_rules/downloader_alerts.yml
   - Alertas: Container down, Memória alta, Disco cheio

6. 🔧 Comandos Úteis
   - Backup manual: ./scripts/maintenance/backup_database.sh
   - Monitor manual: ./scripts/maintenance/monitor_downloader.sh
   - Status: docker ps | grep downloader
   - Health: docker inspect dukascopy_downloader | jq '.[0].State.Health'
   - Logs: docker logs -f dukascopy_downloader

EOF

if [ "$DRY_RUN" = true ]; then
    echo "⚠️ MODO DRY-RUN - Execute sem --dry-run para aplicar as mudanças"
fi

echo "🎉 Script concluído!"
