#!/usr/bin/env bash
################################################################################
# MT5 Trading DB Backup Script with Remote Upload
# 
# Features:
#   - PostgreSQL database backup using pg_dump
#   - Compression with gzip (level 9)
#   - SHA256 checksum generation
#   - Upload to remote backup server via API
#   - Retry logic with exponential backoff
#   - Structured logging
#   - Local retention policy
#   - Health check integration
#
# Requirements:
#   - pg_dump (PostgreSQL client tools)
#   - curl
#   - sha256sum
#
# Environment Variables:
#   POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
#   BACKUP_DIR, BACKUP_API_URL, BACKUP_API_TOKEN
#   KEEP_LOCAL_BACKUPS (default: 3)
#
################################################################################

set -euo pipefail

# Verificar se está rodando como root
if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Este script deve ser executado como root (sudo)." >&2
    exit 1
fi

# ============================================================================
# CONFIGURAÇÃO E VARIÁVEIS DE AMBIENTE
# ============================================================================

# Configurações do banco de dados
DB=${POSTGRES_DB:-mt5_trading}
USER=${POSTGRES_USER:-trader}
HOST=${POSTGRES_HOST:-localhost}
PORT=${POSTGRES_PORT:-5432}

# Configurações de backup local
BACKUP_DIR=${BACKUP_DIR:-/var/backups/mt5}
KEEP_LOCAL_BACKUPS=${KEEP_LOCAL_BACKUPS:-3}
LOG_DIR="${BACKUP_DIR}/logs"

# Configurações de backup remoto
BACKUP_API_URL=${BACKUP_API_URL:-""}
BACKUP_API_TOKEN=${BACKUP_API_TOKEN:-""}
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-5}

# Execução do dump (host|container|auto)
DUMP_MODE=${DUMP_MODE:-auto}
DB_CONTAINER_NAME=${DB_CONTAINER_NAME:-mt5_db}

# Criar diretórios necessários
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

# Configurações de timestamp e arquivo
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB}-${TIMESTAMP}.dump"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
LOG_FILE="${LOG_DIR}/backup-${TIMESTAMP}.log"

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

# Função de logging estruturado
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date -Iseconds)
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

# Função para calcular tamanho formatado
format_size() {
    local size=$1
    if [ "$size" -lt 1024 ]; then
        echo "${size}B"
    elif [ "$size" -lt 1048576 ]; then
        echo "$((size / 1024))KB"
    elif [ "$size" -lt 1073741824 ]; then
        echo "$((size / 1048576))MB"
    else
        echo "$((size / 1073741824))GB"
    fi
}

# Função de limpeza em caso de erro
cleanup_on_error() {
    log_error "Erro detectado, limpando arquivos temporários..."
    [ -f "$BACKUP_FILE" ] && rm -f "$BACKUP_FILE"
    [ -f "$CHECKSUM_FILE" ] && rm -f "$CHECKSUM_FILE"
}

trap cleanup_on_error ERR

# Função para verificar dependências
check_dependencies() {
    local missing_deps=()
    
    for cmd in pg_dump curl sha256sum; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done
    # Se pretendemos usar container ou auto com container rodando, validar docker
    if [ "$DUMP_MODE" = "container" ] || [ "$DUMP_MODE" = "auto" ]; then
        if command -v docker &> /dev/null; then
            :
        else
            # Se modo container for obrigatório, falha. Se auto, continua (vai tentar host)
            if [ "$DUMP_MODE" = "container" ]; then
                missing_deps+=("docker")
            fi
        fi
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_error "Dependências ausentes: ${missing_deps[*]}"
        log_error "Instale: sudo apt-get install postgresql-client curl coreutils"
        if printf '%s\n' "${missing_deps[@]}" | grep -q '^docker$'; then
            log_error "Docker é necessário para DUMP_MODE=container. Instale docker.io ou mude DUMP_MODE=host."
        fi
        exit 1
    fi
}

# ============================================================================
# BACKUP DO BANCO DE DADOS
# ============================================================================

container_running() {
    command -v docker &> /dev/null || return 1
    docker ps --format '{{.Names}}' | grep -qx "$DB_CONTAINER_NAME"
}

perform_database_backup() {
    log_info "=========================================="
    log_info "INICIANDO BACKUP DO BANCO DE DADOS"
    log_info "=========================================="
    log_info "Banco: ${DB}"
    log_info "Host: ${HOST}:${PORT}"
    log_info "Arquivo: ${BACKUP_FILE}"
    
    local start_time=$(date +%s)

    # Escolher estratégia de dump
    local use_container=false
    if [ "$DUMP_MODE" = "container" ]; then
        use_container=true
    elif [ "$DUMP_MODE" = "auto" ] && container_running; then
        use_container=true
    fi

    if [ "$use_container" = true ]; then
        log_info "Modo de dump: container (docker exec em ${DB_CONTAINER_NAME})"
        # Executar pg_dump dentro do container e redirecionar para o arquivo no host
        if docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-trader123}" "$DB_CONTAINER_NAME" \
            pg_dump -h 127.0.0.1 -p 5432 -U "$USER" -d "$DB" -Fc -Z9 \
            > "$BACKUP_FILE" 2>>"$LOG_FILE"; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            local file_size=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
            local formatted_size=$(format_size "$file_size")
            log_success "Backup (container) concluído com sucesso!"
            log_info "Tempo: ${duration}s"
            log_info "Tamanho: ${formatted_size} (${file_size} bytes)"
            return 0
        else
            log_error "Falha no pg_dump via container"
            # Se estava em auto, tentar fallback para host
            if [ "$DUMP_MODE" = "auto" ]; then
                log_warn "Tentando fallback para modo host..."
            else
                return 1
            fi
        fi
    fi

    # Modo host (padrão)
    log_info "Modo de dump: host (conexão direta em ${HOST}:${PORT})"
    export PGPASSWORD="${POSTGRES_PASSWORD:-trader123}"
    if pg_dump -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -Fc -Z9 \
        --verbose -f "$BACKUP_FILE" 2>&1 | tee -a "$LOG_FILE"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        local file_size=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
        local formatted_size=$(format_size "$file_size")
        log_success "Backup (host) concluído com sucesso!"
        log_info "Tempo: ${duration}s"
        log_info "Tamanho: ${formatted_size} (${file_size} bytes)"
        unset PGPASSWORD
        return 0
    else
        log_error "Falha ao executar pg_dump (host)"
        unset PGPASSWORD
        return 1
    fi
}

# ============================================================================
# CHECKSUM E VERIFICAÇÃO
# ============================================================================

generate_checksum() {
    log_info "Gerando checksum SHA256..."
    
    if sha256sum "$BACKUP_FILE" > "$CHECKSUM_FILE"; then
        local checksum=$(cut -d' ' -f1 "$CHECKSUM_FILE")
        log_success "Checksum gerado: ${checksum}"
        echo "$checksum"
        return 0
    else
        log_error "Falha ao gerar checksum"
        return 1
    fi
}

verify_backup_integrity() {
    log_info "Verificando integridade do backup..."
    
    if sha256sum -c "$CHECKSUM_FILE" &> /dev/null; then
        log_success "Integridade verificada: OK"
        return 0
    else
        log_error "Verificação de integridade FALHOU!"
        return 1
    fi
}

# ============================================================================
# UPLOAD PARA SERVIDOR REMOTO
# ============================================================================

upload_to_remote_server() {
    if [ -z "$BACKUP_API_URL" ]; then
        log_warn "BACKUP_API_URL não configurada, pulando upload remoto"
        return 0
    fi
    
    if [ -z "$BACKUP_API_TOKEN" ]; then
        log_error "BACKUP_API_TOKEN não configurada"
        return 1
    fi
    
    log_info "=========================================="
    log_info "UPLOAD PARA SERVIDOR REMOTO"
    log_info "=========================================="
    log_info "URL: ${BACKUP_API_URL}"
    
    local filename=$(basename "$BACKUP_FILE")
    local checksum=$(cut -d' ' -f1 "$CHECKSUM_FILE")
    local file_size=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
    
    local retry=0
    local success=false
    
    while [ $retry -lt $MAX_RETRIES ]; do
        log_info "Tentativa $((retry + 1))/${MAX_RETRIES}..."
        
        # Realizar upload com curl
        local response=$(curl -s -w "\n%{http_code}" \
            -X POST "${BACKUP_API_URL}/api/backup/upload" \
            -H "Authorization: Bearer ${BACKUP_API_TOKEN}" \
            -H "X-Repository-Name: mt5-trading-db" \
            -H "X-Backup-Type: full" \
            -H "X-DB-Name: ${DB}" \
            -F "file=@${BACKUP_FILE}" \
            2>&1)
        
        local http_code=$(echo "$response" | tail -n1)
        local body=$(echo "$response" | head -n-1)
        
        if [ "$http_code" = "200" ]; then
            log_success "Upload concluído com sucesso!"
            log_info "Resposta: ${body}"
            
            # Extrair backup_id da resposta JSON (se possível)
            if command -v jq &> /dev/null; then
                local backup_id=$(echo "$body" | jq -r '.backup_id // empty')
                [ -n "$backup_id" ] && log_info "Backup ID: ${backup_id}"
            fi
            
            success=true
            break
        else
            log_error "Upload falhou com HTTP ${http_code}"
            log_error "Resposta: ${body}"
            
            retry=$((retry + 1))
            if [ $retry -lt $MAX_RETRIES ]; then
                local wait_time=$((RETRY_DELAY * retry))
                log_warn "Aguardando ${wait_time}s antes de tentar novamente..."
                sleep "$wait_time"
            fi
        fi
    done
    
    if [ "$success" = true ]; then
        return 0
    else
        log_error "Upload falhou após ${MAX_RETRIES} tentativas"
        return 1
    fi
}

# ============================================================================
# ROTAÇÃO DE BACKUPS LOCAIS
# ============================================================================

rotate_local_backups() {
    log_info "=========================================="
    log_info "ROTAÇÃO DE BACKUPS LOCAIS"
    log_info "=========================================="
    log_info "Mantendo últimos ${KEEP_LOCAL_BACKUPS} backups"
    
    # Lista backups ordenados por data (mais antigos primeiro)
    local backups=($(ls -1t "${BACKUP_DIR}"/*.dump 2>/dev/null || true))
    local total=${#backups[@]}
    
    log_info "Total de backups locais: ${total}"
    
    if [ "$total" -gt "$KEEP_LOCAL_BACKUPS" ]; then
        local to_remove=$((total - KEEP_LOCAL_BACKUPS))
        log_info "Removendo ${to_remove} backup(s) antigo(s)..."
        
        # Remove backups excedentes (do final da lista, que são os mais antigos)
        for ((i=KEEP_LOCAL_BACKUPS; i<total; i++)); do
            local old_backup="${backups[$i]}"
            local old_checksum="${old_backup}.sha256"
            
            log_info "Removendo: $(basename "$old_backup")"
            rm -f "$old_backup" "$old_checksum"
        done
        
        log_success "Rotação concluída"
    else
        log_info "Nenhum backup precisa ser removido"
    fi
}

# ============================================================================
# RELATÓRIO FINAL
# ============================================================================

generate_report() {
    local status=$1
    local duration=$2
    
    log_info "=========================================="
    log_info "RELATÓRIO DE BACKUP"
    log_info "=========================================="
    log_info "Status: ${status}"
    log_info "Data/Hora: $(date -Iseconds)"
    log_info "Duração total: ${duration}s"
    log_info "Arquivo: ${BACKUP_FILE}"
    log_info "Log: ${LOG_FILE}"
    
    if [ "$status" = "SUCCESS" ]; then
        log_info "Backup local: $([ -f "$BACKUP_FILE" ] && echo "✓ Disponível" || echo "✗ Não encontrado")"
        log_info "Checksum: $([ -f "$CHECKSUM_FILE" ] && echo "✓ Gerado" || echo "✗ Não gerado")"
        log_info "Upload remoto: $([ -n "$BACKUP_API_URL" ] && echo "✓ Configurado" || echo "⊝ Não configurado")"
    fi
    
    log_info "=========================================="
}

# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================

check_remote_health() {
    if [ -z "$BACKUP_API_URL" ]; then
        log_warn "BACKUP_API_URL não configurada, pulando health check remoto."
        return 0
    fi
    local health_url="$BACKUP_API_URL/health"
    log_info "Verificando saúde do endpoint remoto: $health_url"
    local health_resp
    health_resp=$(curl -sS --max-time 5 "$health_url" || echo FAIL)
    if echo "$health_resp" | grep -q '"status":"ok"'; then
        log_success "Endpoint remoto saudável: $health_resp"
        return 0
    else
        log_error "Endpoint remoto não respondeu corretamente: $health_resp"
        return 1
    fi
}

main() {
    local script_start=$(date +%s)
    local exit_code=0
    
    log_info "=========================================="
    log_info "MT5 TRADING DB - BACKUP SYSTEM"
    log_info "Versão: 1.0.0"
    log_info "=========================================="
    
    # Verificar dependências
    check_dependencies

    # Health check do endpoint remoto
    if ! check_remote_health; then
        log_error "Abortando backup: endpoint remoto indisponível."
        exit 2
    fi
    
    # Executar backup
    if ! perform_database_backup; then
        log_error "Backup do banco de dados falhou"
        exit_code=1
    fi
    
    # Gerar e verificar checksum
    if [ $exit_code -eq 0 ]; then
        if ! generate_checksum; then
            log_error "Geração de checksum falhou"
            exit_code=1
        elif ! verify_backup_integrity; then
            log_error "Verificação de integridade falhou"
            exit_code=1
        fi
    fi
    
    # Upload remoto (não bloqueia o sucesso do backup local)
    if [ $exit_code -eq 0 ] && [ -n "$BACKUP_API_URL" ]; then
        if ! upload_to_remote_server; then
            log_warn "Upload remoto falhou, mas backup local está disponível"
            # Não altera exit_code para permitir que backup local seja considerado sucesso
        fi
    fi
    
    # Rotação de backups locais
    if [ $exit_code -eq 0 ]; then
        rotate_local_backups
    fi
    
    # Relatório final
    local script_end=$(date +%s)
    local total_duration=$((script_end - script_start))
    
    if [ $exit_code -eq 0 ]; then
        generate_report "SUCCESS" "$total_duration"
        log_success "✓ BACKUP CONCLUÍDO COM SUCESSO!"
    else
        generate_report "FAILED" "$total_duration"
        log_error "✗ BACKUP FALHOU!"
    fi
    
    exit $exit_code
}

# Executar função principal
main "$@"
