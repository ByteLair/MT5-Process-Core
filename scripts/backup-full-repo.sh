#!/usr/bin/env bash
################################################################################
# MT5 Trading DB - Full Repository Backup Script
#
# Features:
#   - Compresses entire repository (excluding libraries, logs, volumes)
#   - Uploads to remote backup server via API
#   - Cleanup of temporary files
#
# Requirements:
#   - tar, curl
#   - BACKUP_API_URL and BACKUP_API_TOKEN configured
#
################################################################################

set -euo pipefail

# Verificar se está rodando como root
if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Este script deve ser executado como root (sudo)." >&2
    exit 1
fi

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

# Carregar variáveis de ambiente
if [ -f /etc/default/mt5-backup ]; then
    source /etc/default/mt5-backup
fi

BACKUP_API_URL=${BACKUP_API_URL:-""}
BACKUP_API_TOKEN=${BACKUP_API_TOKEN:-""}
REPO_DIR=${REPO_DIR:-/home/felipe/MT5-Process-Core-full}
TMP_DIR=${TMP_DIR:-/tmp}
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${TMP_DIR}/mt5-trading-db-full-backup-${TIMESTAMP}.tar.gz"
MAX_UPLOAD_TIME=${MAX_UPLOAD_TIME:-1800}

# ============================================================================
# FUNÇÕES DE LOG
# ============================================================================

log_info() {
    echo "[$(date -Iseconds)] [INFO] $*"
}

log_success() {
    echo "[$(date -Iseconds)] [SUCCESS] $*"
}

log_error() {
    echo "[$(date -Iseconds)] [ERROR] $*" >&2
}

# ============================================================================
# FUNÇÃO DE LIMPEZA
# ============================================================================

cleanup() {
    if [ -f "$BACKUP_FILE" ]; then
        log_info "Removendo arquivo temporário: $BACKUP_FILE"
        rm -f "$BACKUP_FILE"
    fi
}

trap cleanup EXIT

# ============================================================================
# MAIN
# ============================================================================

main() {
    log_info "=========================================="
    log_info "MT5 TRADING DB - FULL REPOSITORY BACKUP"
    log_info "=========================================="

    # Validar configuração
    if [ -z "$BACKUP_API_URL" ]; then
        log_error "BACKUP_API_URL não configurada"
        exit 1
    fi

    if [ -z "$BACKUP_API_TOKEN" ]; then
        log_error "BACKUP_API_TOKEN não configurada"
        exit 1
    fi

    # Criar backup do repositório
    log_info "Compactando repositório..."
    log_info "Diretório: $REPO_DIR"
    log_info "Arquivo: $BACKUP_FILE"

    cd "$REPO_DIR"

    if tar --exclude='logs' \
           --exclude='__pycache__' \
           --exclude='*.dump' \
           --exclude='*.sha256' \
           --exclude='volumes/timescaledb' \
           --exclude='env' \
           --exclude='venv' \
           --exclude='.venv' \
           --exclude='node_modules' \
           --exclude='*.pyc' \
           --exclude='*.pyo' \
           --exclude='.git' \
           -czf "$BACKUP_FILE" .; then

        local file_size=$(stat -c%s "$BACKUP_FILE")
        local formatted_size=$(numfmt --to=iec-i --suffix=B "$file_size" 2>/dev/null || echo "${file_size} bytes")
        log_success "Backup compactado com sucesso!"
        log_info "Tamanho: ${formatted_size}"
    else
        log_error "Falha ao compactar repositório"
        exit 1
    fi

    # Upload para servidor remoto
    log_info "=========================================="
    log_info "UPLOAD PARA SERVIDOR REMOTO"
    log_info "=========================================="
    log_info "URL: ${BACKUP_API_URL}"
    log_info "Timeout: ${MAX_UPLOAD_TIME}s"

    local response=$(curl -s -w "\n%{http_code}" \
        -X POST "${BACKUP_API_URL}/api/backup/upload" \
        -H "Authorization: Bearer ${BACKUP_API_TOKEN}" \
        -H "X-Repository-Name: mt5-trading-db" \
        -H "X-Backup-Type: full-repository" \
        -H "X-DB-Name: mt5_trading" \
        -F "file=@${BACKUP_FILE}" \
        --max-time "$MAX_UPLOAD_TIME" \
        2>&1)

    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        log_success "Upload concluído com sucesso!"
        log_info "Resposta: ${body}"

        # Extrair informações da resposta JSON (se possível)
        if command -v jq &> /dev/null; then
            local remote_path=$(echo "$body" | jq -r '.path // empty')
            local remote_sha256=$(echo "$body" | jq -r '.sha256 // empty')
            [ -n "$remote_path" ] && log_info "Caminho remoto: ${remote_path}"
            [ -n "$remote_sha256" ] && log_info "SHA256: ${remote_sha256}"
        fi

        log_info "=========================================="
        log_success "✓ BACKUP DO REPOSITÓRIO CONCLUÍDO!"
        log_info "=========================================="
        exit 0
    else
        log_error "Upload falhou com HTTP ${http_code}"
        log_error "Resposta: ${body}"
        exit 1
    fi
}

main "$@"
