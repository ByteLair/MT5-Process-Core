#!/bin/bash
# scripts/check_github_runner.sh
# Verifica status do GitHub Actions Runner e alerta se estiver offline

SERVICE="actions.runner.Lysk-dot-mt5-trading-db.2v4g1.service"
LOG="/var/log/github_runner_status.log"
STATUS=$(systemctl is-active "$SERVICE")
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

EMAIL="kuramopr@gmail.com"
if [ "$STATUS" != "active" ]; then
    REASON=$(systemctl status "$SERVICE" | tail -20)
    echo "$TIMESTAMP - OFFLINE - $REASON" >> "$LOG"
    echo -e "GitHub Actions Runner está OFFLINE em $TIMESTAMP\nMotivo:\n$REASON" | mailx -s "[ALERTA] GitHub Runner OFFLINE" "$EMAIL"
else
    echo "$TIMESTAMP - ONLINE" >> "$LOG"
fi
