#!/bin/bash
# scripts/start_github_runner.sh
# Inicia e habilita o GitHub Actions Runner como serviço systemd

SERVICE="actions.runner.Lysk-dot-mt5-trading-db.2v4g1.service"

sudo systemctl start "$SERVICE"
sudo systemctl enable "$SERVICE"
echo "[OK] GitHub Actions Runner iniciado e configurado para iniciar automaticamente."
