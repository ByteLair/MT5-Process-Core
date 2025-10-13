#!/usr/bin/env bash
set -euo pipefail

# Uses environment or defaults
DB=${POSTGRES_DB:-mt5_trading}
USER=${POSTGRES_USER:-trader}
HOST=${POSTGRES_HOST:-localhost}
PORT=${POSTGRES_PORT:-5432}
OUT_DIR=${BACKUP_DIR:-/var/backups/mt5}
mkdir -p "$OUT_DIR"

STAMP=$(date +%Y%m%d-%H%M%S)
FILE="$OUT_DIR/${DB}-${STAMP}.dump"

export PGPASSWORD="${POSTGRES_PASSWORD:-trader123}"
pg_dump -h "$HOST" -p "$PORT" -U "$USER" -d "$DB" -Fc -Z9 -f "$FILE"
echo "Backup written: $FILE"
