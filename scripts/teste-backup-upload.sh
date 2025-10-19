#!/usr/bin/env bash
# Script para testar upload de arquivo para o servidor de backup MT5
# Usa as variáveis de /etc/default/mt5-backup

set -euo pipefail

# Carregar configuração
if [ -f /etc/default/mt5-backup ]; then
    source /etc/default/mt5-backup
else
    echo "Arquivo de configuração não encontrado: /etc/default/mt5-backup" >&2
    exit 1
fi

# Criar arquivo de teste
TEST_FILE="/tmp/backup-teste-$(date +%s).txt"
echo "Arquivo de teste gerado em $(date -Iseconds)" > "$TEST_FILE"

# Realizar upload
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$BACKUP_API_URL/api/backup/upload" \
    -H "Authorization: Bearer $BACKUP_API_TOKEN" \
    -H "X-Repository-Name: mt5-trading-db" \
    -H "X-Backup-Type: test" \
    -H "X-DB-Name: test-file" \
    -F "file=@$TEST_FILE")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "[OK] Upload de teste realizado com sucesso!"
    echo "Resposta do servidor: $BODY"
else
    echo "[ERRO] Falha no upload de teste (HTTP $HTTP_CODE)"
    echo "Resposta do servidor: $BODY"
    exit 1
fi

# Limpar arquivo de teste
rm -f "$TEST_FILE"
