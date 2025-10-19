#!/bin/bash
# scripts/install_update_systemd.sh
# Instala e ativa o serviço e timer de atualização automática do stack MT5

set -e

SYSTEMD_DIR=/etc/systemd/system
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

sudo cp "$REPO_DIR/systemd/mt5-update.service" "$SYSTEMD_DIR/mt5-update.service"
sudo cp "$REPO_DIR/systemd/mt5-update.timer" "$SYSTEMD_DIR/mt5-update.timer"

sudo systemctl daemon-reload
sudo systemctl enable --now mt5-update.timer

echo "[OK] Atualização automática agendada para todo dia às 10h."
