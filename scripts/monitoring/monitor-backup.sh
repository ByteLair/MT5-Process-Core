#!/usr/bin/env bash
################################################################################
# MT5 Trading DB - Backup Monitoring Script
#
# Features:
#   - Checks last backup logs for errors
#   - Verifies existence and integrity of backup files
#   - Checks remote upload status
#   - Checks disk space
#   - Generates summary report
#
################################################################################



# Verificar se está rodando como root
if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] Este script deve ser executado como root (sudo)." >&2
    exit 1
fi

BACKUP_DIR="/var/backups/mt5"
LOG_DIR="$BACKUP_DIR/logs"
TMP_DIR="/tmp"
REPORT_FILE="$TMP_DIR/mt5-backup-monitor-report-$(date +%Y%m%d-%H%M%S).txt"

# Find last backup log
LAST_LOG=$(ls -1t "$LOG_DIR"/backup-*.log 2>/dev/null | head -1)
LAST_DUMP=$(ls -1t "$BACKUP_DIR"/*.dump 2>/dev/null | head -1)
LAST_REPO=$(ls -1t /tmp/mt5-trading-db-full-backup-*.tar.gz 2>/dev/null | head -1)

# Check disk space
DISK_USAGE=$(df -h "$BACKUP_DIR" | tail -1)

# Start report
{
    echo "==== MT5 Trading DB - Backup Monitoring Report ===="
    echo "Date: $(date -Iseconds)"
    echo "Backup Directory: $BACKUP_DIR"
    echo "Disk Usage: $DISK_USAGE"
    echo
    echo "-- Last Backup Log --"
    if [ -f "$LAST_LOG" ]; then
        tail -20 "$LAST_LOG"
    else
        echo "No backup log found."
    fi
    echo
    echo "-- Last DB Dump --"
    if [ -f "$LAST_DUMP" ]; then
        echo "File: $LAST_DUMP"
        echo "Size: $(stat -c%s "$LAST_DUMP") bytes"
        sha256sum "$LAST_DUMP"
    else
        echo "No DB dump found."
    fi
    echo
    echo "-- Last Repo Backup --"
    if [ -f "$LAST_REPO" ]; then
        echo "File: $LAST_REPO"
        echo "Size: $(stat -c%s "$LAST_REPO") bytes"
        sha256sum "$LAST_REPO"
    else
        echo "No repo backup found."
    fi
    echo
    echo "-- Remote Upload Status --"
    if [ -f "$LAST_LOG" ]; then
        grep -E "Upload concluído|Upload falhou|Resposta:" "$LAST_LOG" | tail -5
    fi
    echo
    echo "==== END OF REPORT ===="
} > "$REPORT_FILE"

cat "$REPORT_FILE"

exit 0
