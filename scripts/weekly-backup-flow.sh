#!/usr/bin/env bash
################################################################################
# MT5 Trading DB - Weekly Backup Flow
#
# Executa em sequência:
#   1. Backup do banco de dados
#   2. Backup completo do repositório
#   3. Monitoramento do backup
#
################################################################################
set -euo pipefail

# Verificar se está rodando como root
if [ "$(id -u)" -ne 0 ]; then
	echo "[ERROR] Este script deve ser executado como root (sudo)." >&2
	exit 1
fi

cd /home/felipe/MT5-Process-Core-full

echo "[FLOW] Iniciando backup do banco de dados..."
bash scripts/backup.sh

echo "[FLOW] Iniciando backup completo do repositório..."
bash scripts/backup-full-repo.sh

echo "[FLOW] Executando monitoramento do backup..."
bash scripts/monitor-backup.sh

echo "[FLOW] Exportando métricas para Prometheus..."
bash scripts/backup-metrics-exporter.sh

echo "[FLOW] Backup semanal completo!"
exit 0
