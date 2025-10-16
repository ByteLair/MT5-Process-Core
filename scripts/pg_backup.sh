#!/usr/bin/env bash
set -euo pipefail

# Configuration
BACKUP_DIR="/var/backups/mt5"
RETENTION_DAYS=14
DATE=$(date +%F)

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Database backup
echo "[$(date)] Starting database backup..."
docker exec -i mt5_db pg_dump -U trader mt5_trading | gzip > "$BACKUP_DIR/db-$DATE.sql.gz"

# Models backup
echo "[$(date)] Starting models backup..."
docker run --rm -v models_mt5:/m -v "$BACKUP_DIR:/b" busybox sh -c "cd /m && tar czf /b/models-$DATE.tgz ."

# Cleanup old backups
echo "[$(date)] Cleaning up old backups..."
find "$BACKUP_DIR" -type f -mtime +"$RETENTION_DAYS" -delete

echo "[$(date)] Backup completed successfully"