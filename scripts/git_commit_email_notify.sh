#!/bin/bash
# scripts/git_commit_email_notify.sh
# Envia email com status do repositório a cada commit

EMAIL="kuramopr@gmail.com"
REPO_DIR="/home/felipe/MT5-Process-Core-full"
cd "$REPO_DIR"

LAST_COMMIT=$(git log -1 --pretty=format:'%h - %an, %ad : %s' --date=iso)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
STATUS=$(git status --short)

BODY="Novo commit realizado no repositório MT5 Trading DB

Branch: $BRANCH
Commit: $LAST_COMMIT

Status do repositório:
$STATUS
"

echo -e "$BODY" | mailx -s "[MT5] Novo commit: $LAST_COMMIT" "$EMAIL"
