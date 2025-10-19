#!/usr/bin/env bash
################################################################################
# MT5 Trading DB - Prometheus Metrics Exporter
#
# Exports backup metrics for Prometheus/Grafana
################################################################################
set -euo pipefail

BACKUP_DIR="/var/backups/mt5"
LOG_DIR="$BACKUP_DIR/logs"
METRICS_FILE="/var/backups/mt5/backup_metrics.prom"

LAST_LOG=$(ls -1t "$LOG_DIR"/backup-*.log 2>/dev/null | head -1)
LAST_DUMP=$(ls -1t "$BACKUP_DIR"/*.dump 2>/dev/null | head -1)
LAST_REPO=$(ls -1t /tmp/mt5-trading-db-full-backup-*.tar.gz 2>/dev/null | head -1)

# Status
STATUS=0
if grep -q "SUCCESS" "$LAST_LOG"; then STATUS=1; fi

# Tamanho dos arquivos
DB_SIZE=0
REPO_SIZE=0
[ -f "$LAST_DUMP" ] && DB_SIZE=$(stat -c%s "$LAST_DUMP")
[ -f "$LAST_REPO" ] && REPO_SIZE=$(stat -c%s "$LAST_REPO")

# Tempo do último backup
DURATION=$(grep "Duração total:" "$LAST_LOG" | awk '{print $NF}' | sed 's/s//')
DURATION=${DURATION:-0}

# Timestamp do último backup
LAST_TS=$(grep "Data/Hora:" "$LAST_LOG" | awk '{print $NF}')

# Exportar métricas
{
    echo "# HELP mt5_backup_status 1=success, 0=failure"
    echo "mt5_backup_status $STATUS"
    echo "# HELP mt5_backup_db_size_bytes Size of last DB dump in bytes"
    echo "mt5_backup_db_size_bytes $DB_SIZE"
    echo "# HELP mt5_backup_repo_size_bytes Size of last repo backup in bytes"
    echo "mt5_backup_repo_size_bytes $REPO_SIZE"
    echo "# HELP mt5_backup_duration_seconds Duration of last backup in seconds"
    echo "mt5_backup_duration_seconds $DURATION"
    echo "# HELP mt5_backup_last_timestamp ISO8601 timestamp of last backup"
    echo "mt5_backup_last_timestamp{ts=\"$LAST_TS\"} 1"
} > "$METRICS_FILE"

exit 0
