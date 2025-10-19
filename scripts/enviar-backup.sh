#!/usr/bin/env bash
# Script para enviar arquivo de backup para o servidor de backup Linux
# Uso: ./scripts/enviar-backup.sh /caminho/para/arquivo

set -euo pipefail

API_URL="http://192.168.15.20:9101"
TOKEN="mt5-backup-secure-token-2025"
ARQUIVO="${1:-}"

if [ -z "$ARQUIVO" ] || [ ! -f "$ARQUIVO" ]; then
    echo "Uso: $0 /caminho/para/arquivo"
    exit 1
fi


RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_URL/upload" \
    -H "Authorization: Bearer $TOKEN" \
    -H "X-Repository-Name: mt5-trading-db" \
    -F "file=@$ARQUIVO")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "[OK] Upload realizado com sucesso!"
    echo "Resposta do servidor: $BODY"
else
    echo "[ERRO] Falha no upload (HTTP $HTTP_CODE)"
    echo "Resposta do servidor: $BODY"
    exit 1
fi
