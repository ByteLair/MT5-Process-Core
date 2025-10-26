#!/usr/bin/env bash
# Installs @reboot cron entry to bring up compose on boot (for user felipe)
set -euo pipefail
CRON_ENTRY='@reboot cd /home/felipe/MT5-Process-Core-full && /usr/local/bin/docker-compose -f /home/felipe/MT5-Process-Core-full/docker-compose.yml up -d # mt5-compose'
# Install into current user's crontab
( crontab -l 2>/dev/null | grep -v -F "# mt5-compose" || true; echo "$CRON_ENTRY" ) | crontab -
echo "Installed @reboot entry for docker-compose"
