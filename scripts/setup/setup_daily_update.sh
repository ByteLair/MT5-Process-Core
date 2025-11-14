#!/bin/bash
# Setup de atualização automática diária de dados Forex

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   🔄 CONFIGURAÇÃO DE ATUALIZAÇÃO DIÁRIA AUTOMÁTICA       ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 1. Verificar se o script existe
SCRIPT_PATH="/home/lair/MT5-Process-Core/scripts/database/update_forex_data.py"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Script não encontrado: $SCRIPT_PATH"
    exit 1
fi

echo "✅ Script encontrado: $SCRIPT_PATH"
echo ""

# 2. Testar execução manual primeiro
echo "🧪 Teste 1: Executando manualmente para verificar..."
echo ""

docker exec mt5_api python /app/scripts/database/update_forex_data.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Teste manual funcionou!"
else
    echo ""
    echo "❌ Teste manual falhou. Verifique erros acima."
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# 3. Configurar cron job
echo "⚙️  Configurando cron job..."
echo ""

# Criar diretório de logs
sudo mkdir -p /var/log/mt5
sudo chmod 777 /var/log/mt5

# Linha do cron
CRON_LINE="5 0 * * * /usr/bin/docker exec mt5_api python /app/scripts/database/update_forex_data.py >> /var/log/mt5/update_daily.log 2>&1"

# Verificar se já existe
if crontab -l 2>/dev/null | grep -q "update_forex_data.py"; then
    echo "ℹ️  Cron job já existe. Removendo versão antiga..."
    crontab -l | grep -v "update_forex_data.py" | crontab -
fi

# Adicionar novo
echo "📝 Adicionando cron job:"
echo "   $CRON_LINE"
echo ""

(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job configurado com sucesso!"
else
    echo "❌ Erro ao configurar cron job"
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# 4. Verificar configuração
echo "🔍 Cron jobs ativos:"
crontab -l | grep -E "mt5|forex"

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# 5. Resumo
cat << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║                   ✅ CONFIGURAÇÃO CONCLUÍDA!                 ║
╚═══════════════════════════════════════════════════════════════╝

📋 RESUMO:

  🕐 Horário de Execução:
     Todo dia às 00:05 (meia-noite e cinco)

  📥 O que acontece:
     1. Script verifica última data no banco
     2. Baixa dados novos via Yahoo Finance (últimos 7 dias)
     3. Insere apenas novos registros (evita duplicatas)
     4. Loga resultado em /var/log/mt5/update_daily.log

  📊 Volume Esperado:
     ~10.000 candles/dia (depende da volatilidade do mercado)

  📝 Logs:
     tail -f /var/log/mt5/update_daily.log

  🧪 Testar Manualmente:
     docker exec mt5_api python /app/scripts/database/update_forex_data.py

  🔧 Editar Cron:
     crontab -e

  ❌ Remover Automação:
     crontab -l | grep -v update_forex_data | crontab -

╔═══════════════════════════════════════════════════════════════╗
║              🎯 DADOS SEMPRE ATUALIZADOS!                    ║
╚═══════════════════════════════════════════════════════════════╝

EOF

echo ""
echo "💡 Dica: O primeiro update roda amanhã às 00:05"
echo "   Para testar agora, execute manualmente:"
echo ""
echo "   docker exec mt5_api python /app/scripts/database/update_forex_data.py"
echo ""
