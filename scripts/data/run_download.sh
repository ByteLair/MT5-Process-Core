#!/bin/bash
# Script para executar download de dados históricos em container
# Uso: ./run_download.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "════════════════════════════════════════════════════════════════════════════"
echo "  📥 DOWNLOAD DADOS HISTÓRICOS FOREX - 10 ANOS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Diretório do projeto: $PROJECT_ROOT"
echo ""

# Verificar se PostgreSQL está rodando
echo "🔍 Verificando PostgreSQL..."
if docker ps | grep -q mt5_db; then
    echo "   ✅ PostgreSQL rodando"
else
    echo "   ❌ PostgreSQL não está rodando!"
    echo "   💡 Execute: docker-compose up -d mt5_db"
    exit 1
fi

echo ""

# Build da imagem
echo "🔨 Construindo imagem Docker..."
docker build -f "$PROJECT_ROOT/docker/Dockerfile.downloader" -t mt5-downloader:latest "$PROJECT_ROOT"

echo ""

# Executar container
echo "🚀 Iniciando download..."
echo "   ⏱️  Isso pode levar 5-15 minutos dependendo da conexão"
echo ""

docker run --rm \
    --name forex_downloader \
    --network mt5-process-core_default \
    -e DB_HOST=mt5_db \
    -e DB_PORT=5432 \
    -e DB_NAME=mt5_trading \
    -e DB_USER=trader \
    -e DB_PASS=trader123 \
    mt5-downloader:latest

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "  ✅ DOWNLOAD CONCLUÍDO!"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "🎯 Próximos passos:"
echo "   1. Calcular indicadores: ./scripts/ml/calculate_indicators_all.sh"
echo "   2. Treinar modelo: python scripts/ml/train_h1_mtf_model.py"
echo "   3. Backtest: python scripts/ml/backtest_h1_mtf.py"
echo ""
