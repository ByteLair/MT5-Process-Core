#!/usr/bin/env bash
################################################################################
# MT5 Trading DB - Backup Test Script
# 
# Testa a conectividade e funcionalidade do sistema de backup
################################################################################

set -euo pipefail

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[✓]${NC} $*"; }
log_error() { echo -e "${RED}[✗]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $*"; }

# Carregar configuração
if [ -f /etc/default/mt5-backup ]; then
    source /etc/default/mt5-backup
else
    log_error "Arquivo de configuração não encontrado: /etc/default/mt5-backup"
    exit 1
fi

log_info "=========================================="
log_info "MT5 BACKUP SYSTEM - TESTE DE CONECTIVIDADE"
log_info "=========================================="
echo ""

# ============================================================================
# TESTE 1: Verificar Dependências
# ============================================================================

log_info "1. Verificando dependências..."
DEPS_OK=true

for cmd in pg_dump curl sha256sum jq; do
    if command -v "$cmd" &> /dev/null; then
        log_success "$cmd: instalado"
    else
        log_error "$cmd: NÃO instalado"
        DEPS_OK=false
    fi
done

if [ "$DEPS_OK" = false ]; then
    log_error "Instale dependências faltantes: sudo apt-get install postgresql-client curl coreutils jq"
    exit 1
fi
echo ""

# ============================================================================
# TESTE 2: Verificar Diretórios
# ============================================================================

log_info "2. Verificando diretórios..."
if [ -d "$BACKUP_DIR" ]; then
    log_success "Diretório de backup existe: $BACKUP_DIR"
    if [ -w "$BACKUP_DIR" ]; then
        log_success "Diretório é gravável"
    else
        log_error "Diretório NÃO é gravável"
    fi
else
    log_error "Diretório de backup não existe: $BACKUP_DIR"
fi
echo ""

# ============================================================================
# TESTE 3: Testar Conexão com PostgreSQL
# ============================================================================

log_info "3. Testando conexão com PostgreSQL..."
export PGPASSWORD="$POSTGRES_PASSWORD"

if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" &> /dev/null; then
    log_success "PostgreSQL está acessível em ${POSTGRES_HOST}:${POSTGRES_PORT}"
    
    # Testar query
    if psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        -c "SELECT 1;" &> /dev/null; then
        log_success "Autenticação com banco de dados: OK"
    else
        log_error "Falha na autenticação com banco de dados"
    fi
else
    log_error "PostgreSQL não está acessível em ${POSTGRES_HOST}:${POSTGRES_PORT}"
fi

unset PGPASSWORD
echo ""

# ============================================================================
# TESTE 4: Testar API de Backup Remota
# ============================================================================

if [ -n "$BACKUP_API_URL" ]; then
    log_info "4. Testando API de backup remota..."
    log_info "URL: $BACKUP_API_URL"
    
    # Testar endpoint /health
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BACKUP_API_URL/health" 2>/dev/null || echo "000")
    
    if [ "$HTTP_CODE" = "200" ]; then
        log_success "API de backup está acessível (HTTP $HTTP_CODE)"
        
        # Testar autenticação
        AUTH_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer ${BACKUP_API_TOKEN}" \
            "$BACKUP_API_URL/api/backup/list" 2>/dev/null || echo "000")
        
        if [ "$AUTH_CODE" = "200" ]; then
            log_success "Autenticação com API: OK"
            
            # Listar backups existentes
            RESPONSE=$(curl -s -H "Authorization: Bearer ${BACKUP_API_TOKEN}" \
                "$BACKUP_API_URL/api/backup/list?limit=5")
            
            if command -v jq &> /dev/null; then
                BACKUP_COUNT=$(echo "$RESPONSE" | jq -r '.total // 0')
                log_info "Backups remotos encontrados: $BACKUP_COUNT"
            fi
        elif [ "$AUTH_CODE" = "401" ] || [ "$AUTH_CODE" = "403" ]; then
            log_error "Falha na autenticação (HTTP $AUTH_CODE)"
            log_error "Verifique BACKUP_API_TOKEN em /etc/default/mt5-backup"
        else
            log_error "Erro ao autenticar (HTTP $AUTH_CODE)"
        fi
    else
        log_error "API de backup NÃO está acessível (HTTP $HTTP_CODE)"
        log_error "Verifique se o servidor está rodando e acessível"
    fi
else
    log_warn "4. BACKUP_API_URL não configurada - upload remoto desabilitado"
fi
echo ""

# ============================================================================
# TESTE 5: Verificar Serviço Systemd
# ============================================================================

log_info "5. Verificando serviço systemd..."

if systemctl is-enabled mt5-backup.timer &> /dev/null; then
    log_success "Timer está habilitado"
else
    log_warn "Timer NÃO está habilitado"
fi

if systemctl is-active mt5-backup.timer &> /dev/null; then
    log_success "Timer está ativo"
    
    # Mostrar próxima execução
    NEXT_RUN=$(systemctl list-timers mt5-backup.timer --no-pager | grep mt5-backup | awk '{print $1, $2, $3}')
    log_info "Próxima execução: $NEXT_RUN"
else
    log_warn "Timer NÃO está ativo"
fi
echo ""

# ============================================================================
# TESTE 6: Listar Backups Existentes
# ============================================================================

log_info "6. Listando backups locais existentes..."
BACKUP_FILES=($(ls -t "$BACKUP_DIR"/*.dump 2>/dev/null || true))

if [ ${#BACKUP_FILES[@]} -gt 0 ]; then
    log_success "Encontrados ${#BACKUP_FILES[@]} backup(s) local(is):"
    for file in "${BACKUP_FILES[@]}"; do
        SIZE=$(du -h "$file" | cut -f1)
        DATE=$(stat -c %y "$file" | cut -d'.' -f1)
        echo "  • $(basename "$file") - $SIZE - $DATE"
    done
else
    log_warn "Nenhum backup local encontrado em $BACKUP_DIR"
fi
echo ""

# ============================================================================
# RESUMO
# ============================================================================

log_info "=========================================="
log_info "RESUMO DOS TESTES"
log_info "=========================================="
echo ""
log_info "Para executar backup manualmente:"
log_info "  sudo systemctl start mt5-backup.service"
echo ""
log_info "Para ver logs do backup:"
log_info "  sudo journalctl -u mt5-backup.service -n 100"
echo ""
log_info "Para ver status do timer:"
log_info "  systemctl status mt5-backup.timer"
echo ""
