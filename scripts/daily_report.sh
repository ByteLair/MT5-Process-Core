#!/bin/bash
# scripts/daily_report.sh
# Gera relatório diário de status dos serviços, últimos commits e testes, enviando email único

EMAIL="kuramopr@gmail.com"
REPO_DIR="/home/felipe/mt5-trading-db"
cd "$REPO_DIR"

# Status dos serviços
SERVICES=(mt5-update.service mt5-tests.service actions.runner.Lysk-dot-mt5-trading-db.2v4g1.service github-runner-check.service)
SERVICE_STATUS=""
for SVC in "${SERVICES[@]}"; do
    STATUS=$(systemctl is-active "$SVC")
    SERVICE_STATUS+="$SVC: $STATUS\n"
    if [ "$STATUS" != "active" ]; then
        REASON=$(systemctl status "$SVC" | tail -20)
        SERVICE_STATUS+="Motivo: $REASON\n"
    fi
    SERVICE_STATUS+="\n"
}

# Últimos commits
COMMITS=$(git log -3 --pretty=format:'%h - %an, %ad : %s' --date=iso)

# Último teste
TEST_RESULT=$(journalctl -u mt5-tests.service --since "-1 day" | tail -30)

BODY="Relatório diário MT5 Trading DB\n\nStatus dos serviços:\n$SERVICE_STATUS\nÚltimos commits:\n$COMMITS\n\nResultado dos testes:\n$TEST_RESULT\n"

echo -e "$BODY" | mailx -s "[MT5] Relatório diário de status" "$EMAIL"
