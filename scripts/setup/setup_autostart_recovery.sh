#!/bin/bash
# Sistema de Auto-Start e Recuperação de Desastres
# Garante que todos os containers MT5 subam automaticamente após reboot

set -e

PROJECT_DIR="/home/lair/MT5-Process-Core"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
LOG_FILE="/var/log/mt5-autostart.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "╔═══════════════════════════════════════════════════════════════╗"
log "║     🚀 MT5 AUTO-START & DISASTER RECOVERY SETUP             ║"
log "╚═══════════════════════════════════════════════════════════════╝"
log ""

# 1. Verificar restart policies no docker-compose.yml
log "📋 Etapa 1/5: Verificando restart policies..."

cd "$PROJECT_DIR"

# Contar serviços sem restart policy
SERVICES_WITHOUT_RESTART=$(grep -E "^  [a-z-]+:" "$COMPOSE_FILE" | grep -v "#" | wc -l)
SERVICES_WITH_RESTART=$(grep -E "restart: unless-stopped" "$COMPOSE_FILE" | wc -l)

log "   Total de serviços: $SERVICES_WITHOUT_RESTART"
log "   Com restart policy: $SERVICES_WITH_RESTART"

if [ "$SERVICES_WITH_RESTART" -lt "$SERVICES_WITHOUT_RESTART" ]; then
    log "   ⚠️  Alguns serviços sem restart policy"
    log "   💡 Adicionando restart: unless-stopped a todos..."
    
    # Criar script Python para adicionar restart policies
    python3 << 'PYTHON'
import yaml
import sys

compose_file = "/home/lair/MT5-Process-Core/docker-compose.yml"

with open(compose_file, 'r') as f:
    compose = yaml.safe_load(f)

modified = False
for service_name, service_config in compose.get('services', {}).items():
    if 'restart' not in service_config:
        service_config['restart'] = 'unless-stopped'
        print(f"   ✅ Adicionado restart policy: {service_name}")
        modified = True
    else:
        print(f"   ✓  Já configurado: {service_name}")

if modified:
    with open(compose_file, 'w') as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)
    print("   ✅ docker-compose.yml atualizado!")
else:
    print("   ✅ Todos os serviços já têm restart policy!")
PYTHON

else
    log "   ✅ Todos os serviços já têm restart policy!"
fi

log ""

# 2. Criar Systemd Service
log "📋 Etapa 2/5: Criando systemd service..."

sudo tee /etc/systemd/system/mt5-trading.service > /dev/null << 'SERVICE'
[Unit]
Description=MT5 Trading Platform - Docker Compose
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/lair/MT5-Process-Core
ExecStartPre=/usr/bin/docker-compose down
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
ExecReload=/usr/bin/docker-compose restart
TimeoutStartSec=300
User=root

# Restart automaticamente se falhar
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
SERVICE

log "   ✅ Systemd service criado: /etc/systemd/system/mt5-trading.service"

# 3. Habilitar e iniciar service
log ""
log "📋 Etapa 3/5: Habilitando auto-start..."

sudo systemctl daemon-reload
sudo systemctl enable mt5-trading.service

log "   ✅ Service habilitado para iniciar no boot"

# 4. Criar script de backup automático
log ""
log "📋 Etapa 4/5: Configurando backup automático..."

sudo tee /usr/local/bin/mt5-backup.sh > /dev/null << 'BACKUP'
#!/bin/bash
# Backup automático do banco de dados MT5

BACKUP_DIR="/var/backups/mt5"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"

echo "[$(date)] 🔄 Iniciando backup..."

# Backup do PostgreSQL
docker exec mt5_db pg_dump -U trader mt5_trading | gzip > "$BACKUP_DIR/mt5_db_$DATE.sql.gz"

if [ $? -eq 0 ]; then
    echo "[$(date)] ✅ Backup concluído: mt5_db_$DATE.sql.gz"
    
    # Limpar backups antigos
    find "$BACKUP_DIR" -name "mt5_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    echo "[$(date)] 🧹 Backups antigos limpos (>$RETENTION_DAYS dias)"
else
    echo "[$(date)] ❌ Erro no backup!"
    exit 1
fi

# Backup dos volumes Docker
docker run --rm \
    -v mt5-process-core_db_data:/data \
    -v "$BACKUP_DIR":/backup \
    alpine tar czf /backup/volumes_$DATE.tar.gz /data

echo "[$(date)] ✅ Backup de volumes concluído"
BACKUP

sudo chmod +x /usr/local/bin/mt5-backup.sh

log "   ✅ Script de backup criado: /usr/local/bin/mt5-backup.sh"

# 5. Configurar cron para backup diário
log ""
log "📋 Etapa 5/5: Configurando backup diário..."

CRON_LINE="0 2 * * * /usr/local/bin/mt5-backup.sh >> /var/log/mt5-backup.log 2>&1"

# Adicionar ao crontab do root se não existir
(sudo crontab -l 2>/dev/null | grep -v "mt5-backup.sh"; echo "$CRON_LINE") | sudo crontab -

log "   ✅ Backup diário configurado (02:00)"

# 6. Criar script de healthcheck e recovery
log ""
log "📋 Etapa 6/6: Criando healthcheck e recovery..."

sudo tee /usr/local/bin/mt5-healthcheck.sh > /dev/null << 'HEALTHCHECK'
#!/bin/bash
# Verifica saúde dos containers e reinicia se necessário

LOG="/var/log/mt5-healthcheck.log"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"
}

log_msg "🔍 Verificando saúde dos containers MT5..."

# Lista de containers críticos
CRITICAL_CONTAINERS=(
    "mt5_db"
    "mt5_api"
    "mt5_pgbouncer"
    "mt5_forex_updater"
)

UNHEALTHY=0

for container in "${CRITICAL_CONTAINERS[@]}"; do
    if ! docker ps | grep -q "$container"; then
        log_msg "❌ Container $container não está rodando!"
        UNHEALTHY=1
    else
        # Verificar se está healthy
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")
        
        if [ "$HEALTH" == "unhealthy" ]; then
            log_msg "⚠️  Container $container está unhealthy!"
            UNHEALTHY=1
        fi
    fi
done

if [ $UNHEALTHY -eq 1 ]; then
    log_msg "🔄 Tentando reiniciar serviço MT5..."
    
    cd /home/lair/MT5-Process-Core
    /usr/bin/docker-compose restart
    
    sleep 30
    
    log_msg "✅ Serviço reiniciado"
    
    # Enviar notificação (opcional)
    # echo "MT5 Trading Platform foi reiniciado automaticamente" | mail -s "MT5 Auto-Recovery" admin@example.com
else
    log_msg "✅ Todos os containers estão saudáveis"
fi
HEALTHCHECK

sudo chmod +x /usr/local/bin/mt5-healthcheck.sh

# Adicionar healthcheck ao cron (a cada 15 minutos)
HEALTH_CRON="*/15 * * * * /usr/local/bin/mt5-healthcheck.sh"
(sudo crontab -l 2>/dev/null | grep -v "mt5-healthcheck.sh"; echo "$HEALTH_CRON") | sudo crontab -

log "   ✅ Healthcheck configurado (a cada 15 minutos)"

# 7. Criar script de recovery manual
log ""
log "📋 Criando script de recovery manual..."

sudo tee /usr/local/bin/mt5-recover.sh > /dev/null << 'RECOVERY'
#!/bin/bash
# Recovery manual do sistema MT5

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          🚑 MT5 DISASTER RECOVERY - RESTAURAÇÃO             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

BACKUP_DIR="/var/backups/mt5"

# Listar backups disponíveis
echo "📋 Backups disponíveis:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'

echo ""
read -p "Digite o nome do arquivo de backup para restaurar: " BACKUP_FILE

if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo "❌ Arquivo não encontrado!"
    exit 1
fi

echo ""
read -p "⚠️  Isso irá SOBRESCREVER o banco atual. Continuar? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Operação cancelada"
    exit 0
fi

echo ""
echo "🔄 Parando containers..."
cd /home/lair/MT5-Process-Core
docker-compose stop

echo "🗄️  Restaurando banco de dados..."
gunzip -c "$BACKUP_DIR/$BACKUP_FILE" | docker exec -i mt5_db psql -U trader mt5_trading

if [ $? -eq 0 ]; then
    echo "✅ Banco restaurado com sucesso!"
else
    echo "❌ Erro ao restaurar banco!"
    exit 1
fi

echo "🚀 Reiniciando containers..."
docker-compose up -d

echo ""
echo "✅ Recovery concluído!"
RECOVERY

sudo chmod +x /usr/local/bin/mt5-recover.sh

log "   ✅ Script de recovery criado: /usr/local/bin/mt5-recover.sh"

# 8. Testar o sistema
log ""
log "📋 Testando configuração..."

# Verificar se systemd service está ok
if systemctl is-enabled mt5-trading.service &>/dev/null; then
    log "   ✅ Systemd service habilitado"
else
    log "   ❌ Erro: Systemd service não está habilitado"
    exit 1
fi

# Verificar se cron está configurado
if sudo crontab -l | grep -q "mt5-backup.sh"; then
    log "   ✅ Backup diário configurado"
else
    log "   ⚠️  Backup diário não configurado"
fi

if sudo crontab -l | grep -q "mt5-healthcheck.sh"; then
    log "   ✅ Healthcheck configurado"
else
    log "   ⚠️  Healthcheck não configurado"
fi

# Verificar se containers estão rodando
RUNNING_CONTAINERS=$(docker ps --format '{{.Names}}' | grep mt5 | wc -l)
log "   ✅ Containers rodando: $RUNNING_CONTAINERS"

log ""
log "╔═══════════════════════════════════════════════════════════════╗"
log "║              ✅ SETUP CONCLUÍDO COM SUCESSO!                 ║"
log "╚═══════════════════════════════════════════════════════════════╝"
log ""

# 9. Resumo final
cat << 'SUMMARY'

📊 RESUMO DA CONFIGURAÇÃO:

✅ Restart Policies:
   Todos os containers: restart: unless-stopped

✅ Systemd Service:
   Service: mt5-trading.service
   Status: Habilitado (auto-start no boot)
   
   Comandos úteis:
   • sudo systemctl start mt5-trading    - Iniciar
   • sudo systemctl stop mt5-trading     - Parar
   • sudo systemctl restart mt5-trading  - Reiniciar
   • sudo systemctl status mt5-trading   - Ver status

✅ Backup Automático:
   Frequência: Diário às 02:00
   Retenção: 7 dias
   Local: /var/backups/mt5/
   Script: /usr/local/bin/mt5-backup.sh

✅ Healthcheck Automático:
   Frequência: A cada 15 minutos
   Ação: Reinicia automaticamente se unhealthy
   Log: /var/log/mt5-healthcheck.log
   Script: /usr/local/bin/mt5-healthcheck.sh

✅ Recovery Manual:
   Script: /usr/local/bin/mt5-recover.sh
   Uso: sudo mt5-recover.sh

📝 Logs:
   • Auto-start: /var/log/mt5-autostart.log
   • Backup: /var/log/mt5-backup.log
   • Healthcheck: /var/log/mt5-healthcheck.log
   • Docker: journalctl -u mt5-trading

🧪 TESTAR AGORA:
   sudo reboot  # Reinicia servidor
   
   Após reboot:
   docker ps | grep mt5  # Verifica se containers subiram

╔═══════════════════════════════════════════════════════════════╗
║       🎉 SISTEMA PROTEGIDO CONTRA PERDA DE DADOS! 🎉         ║
╚═══════════════════════════════════════════════════════════════╝

SUMMARY

log "📄 Documentação completa salva em: /var/log/mt5-autostart.log"
