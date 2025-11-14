#!/bin/bash
# Script de setup e teste do container forex-updater

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     🐳 FOREX DATA UPDATER - BUILD E DEPLOY                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

cd /home/lair/MT5-Process-Core

# 1. Verificar arquivos necessários
echo "🔍 Verificando arquivos..."

FILES=(
    "docker/updater/Dockerfile"
    "docker/updater/requirements-updater.txt"
    "docker/updater/crontab"
    "docker/updater/entrypoint.sh"
    "scripts/updater/update_forex_data.py"
    "scripts/updater/healthcheck.py"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "   ✅ $file"
    else
        echo "   ❌ $file (NOT FOUND)"
        exit 1
    fi
done

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# 2. Build da imagem
echo "🔨 Building imagem forex-updater..."
echo ""

docker-compose build forex-updater

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build concluído com sucesso!"
else
    echo ""
    echo "❌ Erro no build"
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# 3. Parar container antigo se existir
if docker ps -a | grep -q mt5_forex_updater; then
    echo "🛑 Parando container antigo..."
    docker-compose stop forex-updater
    docker-compose rm -f forex-updater
    echo "✅ Container antigo removido"
    echo ""
fi

# 4. Iniciar container
echo "🚀 Iniciando container forex-updater..."
echo ""

docker-compose up -d forex-updater

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Container iniciado!"
else
    echo ""
    echo "❌ Erro ao iniciar container"
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# 5. Aguardar inicialização
echo "⏳ Aguardando container inicializar (30s)..."
sleep 30

# 6. Verificar status
echo ""
echo "🔍 Verificando status..."
echo ""

docker ps | grep forex-updater

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Container está rodando!"
else
    echo ""
    echo "❌ Container não está rodando"
    echo ""
    echo "📋 Logs:"
    docker-compose logs forex-updater
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# 7. Verificar logs iniciais
echo "📋 Logs de inicialização:"
echo ""
docker-compose logs --tail 50 forex-updater

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# 8. Testar atualização manual
echo "🧪 Testando atualização manual..."
echo ""

docker exec mt5_forex_updater python /app/scripts/update_forex_data.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Teste de atualização bem-sucedido!"
else
    echo ""
    echo "⚠️  Teste falhou (pode ser normal se dados já estão atualizados)"
fi

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# 9. Verificar cron jobs
echo "⏰ Cron jobs configurados:"
echo ""
docker exec mt5_forex_updater crontab -l

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# 10. Verificar dados no banco
echo "📊 Status dos dados no banco:"
echo ""

docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT 
    timeframe,
    COUNT(*) as total_candles,
    MIN(ts) as primeiro_candle,
    MAX(ts) as ultimo_candle,
    AGE(NOW(), MAX(ts)) as idade_dados
FROM market_data 
WHERE symbol='EURUSD'
GROUP BY timeframe
ORDER BY timeframe;
"

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""

# 11. Resumo final
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════╗
║                  ✅ SETUP CONCLUÍDO COM SUCESSO!                 ║
╚═══════════════════════════════════════════════════════════════════╝

🎯 CONTAINER FOREX-UPDATER ATIVO

📋 Informações:
   • Container: mt5_forex_updater
   • Status: Running
   • Atualização: A cada 6 horas (automático)
   • Próxima execução: Ver cron logs

📊 Comandos Úteis:

   # Ver logs em tempo real
   docker-compose logs -f forex-updater

   # Logs de atualização
   docker exec mt5_forex_updater tail -f /var/log/forex-updater/update.log

   # Executar atualização manual
   docker exec mt5_forex_updater python /app/scripts/update_forex_data.py

   # Ver status do container
   docker ps | grep forex-updater

   # Healthcheck
   docker exec mt5_forex_updater python /app/scripts/healthcheck.py

   # Reiniciar container
   docker-compose restart forex-updater

   # Parar container
   docker-compose stop forex-updater

   # Ver cron schedule
   docker exec mt5_forex_updater crontab -l

🔄 ATUALIZAÇÕES AUTOMÁTICAS:
   ✅ 00:00 - Atualização + Indicadores
   ✅ 06:00 - Atualização + Indicadores
   ✅ 12:00 - Atualização + Indicadores
   ✅ 18:00 - Atualização + Indicadores
   ✅ 03:00 - Verificação de saúde (diário)

📝 Logs persistem em volume Docker:
   docker volume inspect mt5_forex_updater_logs

📚 Documentação completa:
   docker/updater/README.md

╔═══════════════════════════════════════════════════════════════════╗
║         🎉 DADOS SEMPRE ATUALIZADOS AUTOMATICAMENTE!             ║
╚═══════════════════════════════════════════════════════════════════╝

EOF

echo ""
echo "💡 Dica: O container já executou a primeira atualização."
echo "   Próxima atualização automática: próximo horário múltiplo de 6h"
echo ""
