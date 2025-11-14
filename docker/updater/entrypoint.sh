#!/bin/bash
# Entrypoint para container forex-updater

set -e

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║       🔄 FOREX DATA UPDATER - CONTAINER INICIANDO          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "$(date) - Container forex-updater iniciado"
echo ""

# Verificar variáveis de ambiente
echo "🔍 Verificando configuração..."

if [ -z "$DB_HOST" ]; then
    echo "⚠️  DB_HOST não definido, usando padrão: db"
    export DB_HOST="db"
fi

if [ -z "$DB_PORT" ]; then
    export DB_PORT="5432"
fi

if [ -z "$DB_NAME" ]; then
    export DB_NAME="mt5_trading"
fi

if [ -z "$DB_USER" ]; then
    export DB_USER="trader"
fi

echo "   Database: $DB_HOST:$DB_PORT/$DB_NAME"
echo "   User: $DB_USER"
echo ""

# Aguardar banco estar pronto
echo "⏳ Aguardando banco de dados..."
until pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER > /dev/null 2>&1; do
    echo "   Banco ainda não está pronto, aguardando 5s..."
    sleep 5
done
echo "✅ Banco de dados pronto!"
echo ""

# Executar primeira atualização imediatamente
echo "🚀 Executando primeira atualização..."
/usr/local/bin/python /app/scripts/update_forex_data.py || echo "⚠️ Primeira atualização falhou (normal se dados já estão atualizados)"
echo ""

# Verificar cron jobs configurados
echo "📋 Cron jobs configurados:"
crontab -l
echo ""

# Iniciar cron
echo "⏰ Iniciando serviço cron..."
echo "   Próximas execuções:"
echo "   - Atualização de dados: A cada 6 horas"
echo "   - Cálculo de indicadores: 15 min após atualização"
echo "   - Verificação de saúde: Diário às 03:00"
echo ""

# Criar arquivo de PID
echo $$ > /var/run/forex-updater.pid

echo "✅ Container pronto! Logs em /var/log/forex-updater/"
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║            🎯 ATUALIZAÇÕES AUTOMÁTICAS ATIVAS               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Executar comando (cron em foreground)
exec "$@"
