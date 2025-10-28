#!/bin/bash
set -euo pipefail

# Backup script for mt5_data
BACKUP_DIR="/backup/mt5_data"
DB_NAME="mt5_data"
TIMESTAMP=$(date +'%Y%m%dT%H%M%S')
mkdir -p "$BACKUP_DIR"
chown postgres:postgres "$BACKUP_DIR" || true

echo "Creating backup ${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"
sudo -u postgres pg_dump -Fc -d "$DB_NAME" -f "${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.dump"

# Keep last 7 backups
find "$BACKUP_DIR" -type f -name "${DB_NAME}_*.dump" -mtime +7 -exec rm -f {} \;

echo "Backup finished"
