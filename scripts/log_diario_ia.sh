#!/bin/bash
# Script de log diário das ações e erros da IA
# Uso: pode ser agendado via cron ou systemd timer
# Salva em logs/log_diario_ia_$(date +%Y-%m-%d).log

set -euo pipefail
LOG_DIR="../logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/log_diario_ia_$(date +%Y-%m-%d).log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "[LOG DIARIO IA] Data: $(date)"

# 1. Erros dos scripts de ML
if [ -f "$LOG_DIR/pipeline_train.log" ]; then
    echo "\n--- Erros do pipeline ML ---"
    grep -i "error\|exception\|fail" "$LOG_DIR/pipeline_train.log" || echo "Nenhum erro encontrado."
fi

# 2. Últimas ações da IA (execuções, decisões)
if [ -f "$LOG_DIR/pipeline_train.log" ]; then
    echo "\n--- Últimas ações da IA ---"
    tail -20 "$LOG_DIR/pipeline_train.log"
fi

# 3. Logs do scheduler (se existir)
if [ -f "$LOG_DIR/scheduler.log" ]; then
    echo "\n--- Logs do scheduler ---"
    tail -20 "$LOG_DIR/scheduler.log"
fi

# 4. Sinais gerados hoje
if command -v docker-compose &>/dev/null; then
    echo "\n--- Sinais gerados hoje ---"
    docker-compose exec -T db psql -U trader -d mt5_trading -c "SELECT ts, symbol, prob_up, label FROM signals WHERE ts::date = CURRENT_DATE ORDER BY ts DESC LIMIT 10;" 2>/dev/null || echo "Não foi possível consultar o banco."
fi

echo "\n[LOG DIARIO IA] Fim do log."
