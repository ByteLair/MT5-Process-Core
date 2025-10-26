#!/usr/bin/env bash
################################################################################
# MT5 Trading DB - Backup System Installation Script
#
# Este script configura todo o sistema de backup automático:
#   - Cria diretórios necessários
#   - Configura permissões
#   - Instala dependências
#   - Configura serviço systemd
#   - Configura timer para backup diário
#   - Realiza teste de backup
#
################################################################################

set -euo pipefail

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log colorido
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    log_error "Este script precisa ser executado como root"
    log_info "Use: sudo $0"
    exit 1
fi

log_info "=========================================="
log_info "MT5 TRADING DB - SETUP DE BACKUP"
log_info "=========================================="
echo ""

# ============================================================================
# 1. CRIAR DIRETÓRIOS
# ============================================================================

log_info "Criando diretórios de backup..."
mkdir -p /var/backups/mt5/logs
chown -R root:root /var/backups/mt5
chmod 750 /var/backups/mt5
log_success "Diretórios criados"

# ============================================================================
# 2. INSTALAR DEPENDÊNCIAS
# ============================================================================

log_info "Verificando dependências..."
MISSING_DEPS=()

for cmd in pg_dump curl sha256sum jq; do
    if ! command -v "$cmd" &> /dev/null; then
        MISSING_DEPS+=("$cmd")
    fi
done

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    log_warn "Dependências ausentes: ${MISSING_DEPS[*]}"
    log_info "Instalando pacotes necessários..."
    apt-get update -qq
    apt-get install -y -qq postgresql-client curl coreutils jq
    log_success "Dependências instaladas"
else
    log_success "Todas as dependências estão instaladas"
fi

# ============================================================================
# 3. CONFIGURAR VARIÁVEIS DE AMBIENTE
# ============================================================================

log_info "Configurando variáveis de ambiente..."

if [ ! -f /etc/default/mt5-backup ]; then
    cp /home/felipe/mt5-trading-db/.env.backup /etc/default/mt5-backup
    chmod 600 /etc/default/mt5-backup
    chown root:root /etc/default/mt5-backup
    log_success "Arquivo de configuração criado: /etc/default/mt5-backup"
    log_warn "⚠️  IMPORTANTE: Edite /etc/default/mt5-backup e configure:"
    log_warn "   - BACKUP_API_URL (substitua SEU_IP_BACKUP pelo IP real)"
    log_warn "   - POSTGRES_PASSWORD (se diferente do padrão)"
    echo ""
else
    log_info "Arquivo de configuração já existe: /etc/default/mt5-backup"
fi

# ============================================================================
# 4. TORNAR SCRIPT EXECUTÁVEL
# ============================================================================

log_info "Configurando permissões do script..."
chmod +x /home/felipe/mt5-trading-db/scripts/backup.sh
log_success "Script de backup configurado"

# ============================================================================
# 5. INSTALAR SERVIÇO SYSTEMD
# ============================================================================

log_info "Instalando serviço systemd..."
cp /home/felipe/mt5-trading-db/systemd/mt5-backup.service /etc/systemd/system/
cp /home/felipe/mt5-trading-db/systemd/mt5-backup.timer /etc/systemd/system/
systemctl daemon-reload
log_success "Serviço systemd instalado"

# ============================================================================
# 6. HABILITAR E INICIAR TIMER
# ============================================================================

log_info "Habilitando timer de backup automático..."
systemctl enable mt5-backup.timer
systemctl start mt5-backup.timer
log_success "Timer habilitado (backup diário às 03:00 AM)"

# ============================================================================
# 7. VERIFICAR STATUS
# ============================================================================

log_info "Verificando status do timer..."
systemctl status mt5-backup.timer --no-pager | head -n 10

echo ""
log_info "Próxima execução agendada:"
systemctl list-timers mt5-backup.timer --no-pager

# ============================================================================
# 8. TESTE DE BACKUP (OPCIONAL)
# ============================================================================

echo ""
read -p "Deseja executar um backup de teste agora? (s/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    log_info "=========================================="
    log_info "EXECUTANDO BACKUP DE TESTE"
    log_info "=========================================="

    if systemctl start mt5-backup.service; then
        log_success "Backup de teste iniciado"
        log_info "Aguardando conclusão..."
        sleep 5

        log_info "Status do serviço:"
        systemctl status mt5-backup.service --no-pager | tail -n 20

        echo ""
        log_info "Verificando backups criados:"
        ls -lh /var/backups/mt5/*.dump 2>/dev/null || log_warn "Nenhum backup encontrado ainda"

        echo ""
        log_info "Últimas linhas do log:"
        ls -t /var/backups/mt5/logs/*.log 2>/dev/null | head -n1 | xargs tail -n 20 || log_warn "Log não encontrado"
    else
        log_error "Falha ao executar backup de teste"
        log_info "Verifique os logs: journalctl -u mt5-backup.service -n 50"
    fi
fi

# ============================================================================
# RESUMO FINAL
# ============================================================================

echo ""
log_info "=========================================="
log_success "SETUP DE BACKUP CONCLUÍDO!"
log_info "=========================================="
echo ""
log_info "📁 Diretório de backups: /var/backups/mt5/"
log_info "📝 Logs: /var/backups/mt5/logs/"
log_info "⚙️  Configuração: /etc/default/mt5-backup"
log_info "🕐 Agendamento: Diariamente às 03:00 AM"
echo ""
log_info "Comandos úteis:"
log_info "  • Executar backup manualmente:"
log_info "    sudo systemctl start mt5-backup.service"
echo ""
log_info "  • Ver status do timer:"
log_info "    systemctl status mt5-backup.timer"
echo ""
log_info "  • Ver logs do último backup:"
log_info "    journalctl -u mt5-backup.service -n 100"
echo ""
log_info "  • Listar backups locais:"
log_info "    ls -lh /var/backups/mt5/"
echo ""
log_info "  • Testar conectividade com servidor remoto:"
log_info "    curl http://SEU_IP_BACKUP:9101/health"
echo ""

if [ ! -f /etc/default/mt5-backup ] || grep -q "SEU_IP_BACKUP" /etc/default/mt5-backup; then
    log_warn "=========================================="
    log_warn "⚠️  AÇÃO NECESSÁRIA:"
    log_warn "=========================================="
    log_warn "Edite o arquivo de configuração:"
    log_warn "  sudo nano /etc/default/mt5-backup"
    echo ""
    log_warn "Configure o IP do servidor de backup:"
    log_warn "  BACKUP_API_URL=http://IP_DO_SERVIDOR:9101"
    echo ""
    log_warn "Após editar, teste a conexão:"
    log_warn "  curl \$BACKUP_API_URL/health"
    log_warn "=========================================="
fi

echo ""
log_success "✓ Setup completo!"
