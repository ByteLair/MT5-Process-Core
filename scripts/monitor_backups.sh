#!/bin/bash
set -euo pipefail

# Configuration
BACKUP_DIR="/backups/mt5"
LOG_FILE="/var/log/mt5/backup_monitor.log"
ALERT_EMAIL="admin@example.com"  # Change this to your email
DISCORD_WEBHOOK="your_webhook_url"  # Optional: Add your Discord webhook URL
SLACK_WEBHOOK="your_webhook_url"   # Optional: Add your Slack webhook URL

# Notification thresholds
MAX_BACKUP_AGE=25  # Hours
MIN_BACKUP_SIZE=1000000  # 1MB in bytes
MAX_FAILED_BACKUPS=2

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

send_email_alert() {
    local subject="$1"
    local message="$2"
    echo -e "$message" | mail -s "$subject" "$ALERT_EMAIL"
}

send_discord_alert() {
    local message="$1"
    if [ -n "$DISCORD_WEBHOOK" ]; then
        curl -H "Content-Type: application/json" \
             -d "{\"content\":\"$message\"}" \
             "$DISCORD_WEBHOOK"
    fi
}

send_slack_alert() {
    local message="$1"
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST \
             -H "Content-Type: application/json" \
             -d "{\"text\":\"$message\"}" \
             "$SLACK_WEBHOOK"
    fi
}

check_backup_age() {
    local backup_type="$1"
    local backup_path="$2"
    local pattern="$3"
    
    # Find most recent backup file
    local latest_backup=$(find "$backup_path" -name "$pattern" -type f -printf '%T@ %p\n' | sort -n | tail -1)
    
    if [ -z "$latest_backup" ]; then
        log "ERROR: No $backup_type backup found in $backup_path"
        return 1
    fi
    
    # Extract timestamp and filename
    local timestamp=$(echo "$latest_backup" | cut -d' ' -f1)
    local filename=$(echo "$latest_backup" | cut -d' ' -f2)
    
    # Calculate age in hours
    local age_hours=$(( ($(date +%s) - ${timestamp%.*}) / 3600 ))
    
    if [ "$age_hours" -gt "$MAX_BACKUP_AGE" ]; then
        log "WARNING: $backup_type backup is $age_hours hours old"
        return 1
    fi
    
    # Check file size
    local size=$(stat -c%s "$filename")
    if [ "$size" -lt "$MIN_BACKUP_SIZE" ]; then
        log "WARNING: $backup_type backup is suspiciously small ($size bytes)"
        return 1
    fi
    
    return 0
}

check_failed_backups() {
    local recent_failures=$(grep -c "ERROR" "$LOG_FILE" 2>/dev/null || echo "0")
    if [ "$recent_failures" -ge "$MAX_FAILED_BACKUPS" ]; then
        return 1
    fi
    return 0
}

# Main monitoring logic
log "Starting backup monitoring..."

ALERT_MESSAGE=""

# Check database backups
if ! check_backup_age "Database" "$BACKUP_DIR/db" "mt5_trading_*.backup"; then
    ALERT_MESSAGE+="⚠️ Database backup issue detected\n"
fi

# Check models backups
if ! check_backup_age "Models" "$BACKUP_DIR/models" "models_*.tar.gz"; then
    ALERT_MESSAGE+="⚠️ Models backup issue detected\n"
fi

# Check config backups
if ! check_backup_age "Config" "$BACKUP_DIR/configs" "config_*.tar.gz"; then
    ALERT_MESSAGE+="⚠️ Configuration backup issue detected\n"
fi

# Check backup logs for errors
if ! check_failed_backups; then
    ALERT_MESSAGE+="⚠️ Multiple backup failures detected in logs\n"
fi

# Check disk space
DISK_USAGE=$(df -h "$BACKUP_DIR" | awk 'NR==2 {print $5}' | tr -d '%')
if [ "$DISK_USAGE" -gt 85 ]; then
    ALERT_MESSAGE+="⚠️ Backup disk space critical: ${DISK_USAGE}% used\n"
fi

# Generate backup statistics
STATS_MESSAGE="MT5 Trading DB Backup Status:\n"
STATS_MESSAGE+="================================\n"
STATS_MESSAGE+="Last Database Backup: $(ls -lth "$BACKUP_DIR/db" | head -2 | tail -1)\n"
STATS_MESSAGE+="Last Models Backup: $(ls -lth "$BACKUP_DIR/models" | head -2 | tail -1)\n"
STATS_MESSAGE+="Last Config Backup: $(ls -lth "$BACKUP_DIR/configs" | head -2 | tail -1)\n"
STATS_MESSAGE+="Disk Usage: ${DISK_USAGE}%\n"
STATS_MESSAGE+="Recent Errors: $(grep -c "ERROR" "$LOG_FILE" 2>/dev/null || echo "0")\n"

# Send alerts if needed
if [ -n "$ALERT_MESSAGE" ]; then
    FULL_MESSAGE="${ALERT_MESSAGE}\n\n${STATS_MESSAGE}"
    
    log "Sending alerts..."
    send_email_alert "MT5 Trading DB Backup Alert" "$FULL_MESSAGE"
    send_discord_alert "$FULL_MESSAGE"
    send_slack_alert "$FULL_MESSAGE"
else
    log "All backups are healthy"
fi

# Log statistics
log "$STATS_MESSAGE"