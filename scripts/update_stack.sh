#!/bin/bash
# scripts/update_stack.sh
# Atualiza containers, dependências e reinicia serviços do stack MT5

set -e

cd "$(dirname "$0")/.."

echo "[INFO] Atualizando código do repositório..."
git pull

echo "[INFO] Atualizando imagens Docker..."
docker compose pull

echo "[INFO] Recriando containers..."
docker compose up -d --remove-orphans

echo "[INFO] Atualizando dependências Python (API e ML)..."
docker compose exec api pip install -r /app/requirements.txt || true
docker compose exec ml pip install -r /ml/requirements-ml.txt || true

echo "[INFO] Limpeza de imagens antigas..."
docker image prune -f

echo "[OK] Stack atualizado com sucesso."
