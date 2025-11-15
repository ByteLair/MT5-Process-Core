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
