#!/bin/bash
set -euo pipefail

# Configuration
BACKUP_DIR="/backups/mt5"
RETAIN_DAYS=14
DATE=$(date +%Y%m%d)
LOG_FILE="/var/log/mt5/backup.log"
DOCKER_COMPOSE_DIR="/home/felipe/mt5-trading-db"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"/{db,models,configs}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log "Starting MT5 Trading DB backup process..."

# 1. Database backup
log "Starting database backup..."
docker exec mt5_db pg_dump \
    -U trader \
    -d mt5_trading \
    -F c \
    -Z 9 \
    -f /backups/mt5_trading_$DATE.backup || {
        log "ERROR: Database backup failed"
        exit 1
    }

# 2. Models backup
log "Starting models backup..."
docker run --rm \
    -v models_mt5:/models \
    -v "$BACKUP_DIR/models":/backup \
    busybox tar czf \
    /backup/models_$DATE.tar.gz \
    -C /models . || {
        log "ERROR: Models backup failed"
        exit 1
    }

# 3. Configuration backup
log "Backing up configurations..."
cd "$DOCKER_COMPOSE_DIR"
tar czf "$BACKUP_DIR/configs/config_$DATE.tar.gz" \
    docker-compose.yml \
    .env \
    api/config.py || {
        log "ERROR: Configuration backup failed"
        exit 1
    }

# 4. Verify backups
log "Verifying backups..."

# Check database backup
docker exec mt5_db pg_restore -l /backups/mt5_trading_$DATE.backup > /dev/null || {
    log "ERROR: Database backup verification failed"
    exit 1
}

# Check models backup
if ! tar tzf "$BACKUP_DIR/models/models_$DATE.tar.gz" > /dev/null; then
    log "ERROR: Models backup verification failed"
    exit 1
fi

# Check config backup
if ! tar tzf "$BACKUP_DIR/configs/config_$DATE.tar.gz" > /dev/null; then
    log "ERROR: Configuration backup verification failed"
    exit 1
fi

# 5. Cleanup old backups
log "Cleaning up old backups..."
find "$BACKUP_DIR" -type f -mtime +"$RETAIN_DAYS" -delete

# 6. Log backup sizes
log "Backup sizes:"
du -sh "$BACKUP_DIR"/{db,models,configs} | while read size dir; do
    log "$(basename "$dir"): $size"
done

# 7. Create backup report
REPORT="$BACKUP_DIR/backup_report_$DATE.txt"
{
    echo "MT5 Trading DB Backup Report - $DATE"
    echo "====================================="
    echo
    echo "Database Backup:"
    ls -lh "$BACKUP_DIR/db/mt5_trading_$DATE.backup"
    echo
    echo "Models Backup:"
    ls -lh "$BACKUP_DIR/models/models_$DATE.tar.gz"
    echo
    echo "Config Backup:"
    ls -lh "$BACKUP_DIR/configs/config_$DATE.tar.gz"
    echo
    echo "Total Backup Size:"
    du -sh "$BACKUP_DIR"
} > "$REPORT"

log "Backup completed successfully. Report saved to $REPORT"