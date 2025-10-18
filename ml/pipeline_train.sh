#!/bin/bash
# Pipeline automatizado: prepara dataset, treina modelo, valida e salva relatório
# Documentação: Cada etapa é logada e pode ser consultada em logs/pipeline_train.log

set -euo pipefail
LOG=../logs/pipeline_train.log
mkdir -p ../logs

exec > >(tee -a "$LOG") 2>&1

echo "[PIPELINE] Iniciando pipeline de ML: $(date)"

# 1. Preparar dataset
echo "[PIPELINE] Etapa 1: Preparando dataset..."
python3 prepare_dataset.py

# 2. Treinar modelo
echo "[PIPELINE] Etapa 2: Treinando modelo..."
python3 train_model.py

# 3. Validar modelo (gera relatório)
if [ -f eval_threshold.py ]; then
    echo "[PIPELINE] Etapa 3: Avaliando thresholds e gerando relatório..."
    python3 eval_threshold.py
else
    echo "[PIPELINE] eval_threshold.py não encontrado, pulando validação."
fi

echo "[PIPELINE] Pipeline finalizado: $(date)"
