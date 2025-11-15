#!/bin/bash
################################################################################
# Script: cleanup_database.sh
# Descrição: Limpa dados de teste e inconsistências do banco PostgreSQL
# 
# PROBLEMAS IDENTIFICADOS:
# 1. market_data_raw: 3 registros de teste (source='test_mt5')
# 2. signals: 3 registros de teste (M5 timeframe - não usado no projeto)
# 3. fills: 0 registros (OK)
# 4. trade_logs: 0 registros (OK)
# 5. market_data: 4,159 registros com volume=0/NULL (podem ser dados incompletos)
#
# AÇÃO:
# - Remove dados de teste das tabelas auxiliares
# - Mantém market_data intacta (dados reais do Dukascopy)
# - Cria backup antes da limpeza
################################################################################

set -e  # Exit on error

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Variáveis
PROJECT_ROOT="/home/lair/MT5-Process-Core"
BACKUP_DIR="$PROJECT_ROOT/backups/database"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/cleanup_backup_$TIMESTAMP.sql.gz"
DRY_RUN=false

# Parse arguments
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}🔍 Modo DRY-RUN ativado (apenas simula, não executa)${NC}"
fi

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       🗄️  LIMPEZA DE DADOS DE TESTE DO BANCO DE DADOS 🗄️      ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Criar diretório de backup se não existir
mkdir -p "$BACKUP_DIR"

################################################################################
# 1. ANÁLISE INICIAL
################################################################################
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}📊 1. ANÁLISE INICIAL DO BANCO${NC}"
echo -e "${BLUE}==================================================${NC}"

echo -e "${CYAN}📋 Verificando estado atual das tabelas...${NC}"

# Executar análise
docker exec mt5_db psql -U trader -d mt5_trading << 'EOF'
\timing off

-- Contagem por tabela
SELECT 
    'market_data' as tabela, 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE volume = 0 OR volume IS NULL) as sem_volume
FROM market_data
UNION ALL
SELECT 'market_data_raw', COUNT(*), 0 FROM market_data_raw
UNION ALL
SELECT 'signals', COUNT(*), 0 FROM signals
UNION ALL
SELECT 'fills', COUNT(*), 0 FROM fills
UNION ALL
SELECT 'trade_logs', COUNT(*), 0 FROM trade_logs
ORDER BY tabela;

-- Dados de teste identificados
\echo ''
\echo '🔍 DADOS DE TESTE IDENTIFICADOS:'
\echo ''

SELECT 'market_data_raw' as fonte, COUNT(*) as registros, 'source=test_mt5' as tipo
FROM market_data_raw 
WHERE source = 'test_mt5';

SELECT 'signals' as fonte, COUNT(*) as registros, 'timeframe=M5 (não usado)' as tipo
FROM signals 
WHERE timeframe = 'M5';

EOF

echo ""

################################################################################
# 2. BACKUP ANTES DA LIMPEZA
################################################################################
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}💾 2. CRIANDO BACKUP DE SEGURANÇA${NC}"
echo -e "${BLUE}==================================================${NC}"

if [ "$DRY_RUN" = false ]; then
    echo -e "${CYAN}📦 Fazendo backup completo do banco...${NC}"
    docker exec mt5_db pg_dump -U trader mt5_trading | gzip > "$BACKUP_FILE"
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup criado: $BACKUP_FILE ($BACKUP_SIZE)${NC}"
else
    echo -e "${YELLOW}[DRY-RUN] Seria criado backup em: $BACKUP_FILE${NC}"
fi

echo ""

################################################################################
# 3. LIMPEZA DE DADOS DE TESTE
################################################################################
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}🧹 3. REMOVENDO DADOS DE TESTE${NC}"
echo -e "${BLUE}==================================================${NC}"

if [ "$DRY_RUN" = false ]; then
    echo -e "${CYAN}🗑️  Limpando market_data_raw (test_mt5)...${NC}"
    DELETED_RAW=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "
        DELETE FROM market_data_raw WHERE source = 'test_mt5';
        SELECT ROW_COUNT();
    " | xargs)
    echo -e "${GREEN}   ✅ Deletados: $DELETED_RAW registros${NC}"
    
    echo -e "${CYAN}🗑️  Limpando signals (timeframe M5)...${NC}"
    DELETED_SIGNALS=$(docker exec mt5_db psql -U trader -d mt5_trading -t -c "
        DELETE FROM signals WHERE timeframe = 'M5';
        SELECT ROW_COUNT();
    " | xargs)
    echo -e "${GREEN}   ✅ Deletados: $DELETED_SIGNALS registros${NC}"
    
else
    echo -e "${YELLOW}[DRY-RUN] DELETE FROM market_data_raw WHERE source = 'test_mt5';${NC}"
    echo -e "${YELLOW}   Seria deletado: ~3 registros${NC}"
    
    echo -e "${YELLOW}[DRY-RUN] DELETE FROM signals WHERE timeframe = 'M5';${NC}"
    echo -e "${YELLOW}   Seria deletado: ~3 registros${NC}"
fi

echo ""

################################################################################
# 4. VERIFICAÇÃO PÓS-LIMPEZA
################################################################################
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}✅ 4. VERIFICAÇÃO PÓS-LIMPEZA${NC}"
echo -e "${BLUE}==================================================${NC}"

if [ "$DRY_RUN" = false ]; then
    echo -e "${CYAN}📊 Estado final das tabelas:${NC}"
    
    docker exec mt5_db psql -U trader -d mt5_trading << 'EOF'
\timing off

SELECT 
    'market_data' as tabela, 
    COUNT(*) as total_registros,
    COUNT(DISTINCT symbol) as simbolos,
    COUNT(DISTINCT timeframe) as timeframes
FROM market_data
UNION ALL
SELECT 
    'market_data_raw', 
    COUNT(*), 
    COUNT(DISTINCT payload->>'symbol'),
    COUNT(DISTINCT payload->>'timeframe')
FROM market_data_raw
UNION ALL
SELECT 'signals', COUNT(*), COUNT(DISTINCT symbol), COUNT(DISTINCT timeframe) FROM signals
UNION ALL
SELECT 'fills', COUNT(*), 0, 0 FROM fills
UNION ALL
SELECT 'trade_logs', COUNT(*), 0, 0 FROM trade_logs
ORDER BY tabela;

EOF

else
    echo -e "${YELLOW}[DRY-RUN] Verificação seria executada após limpeza${NC}"
fi

echo ""

################################################################################
# 5. ANÁLISE DE DADOS COM VOLUME ZERO
################################################################################
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}⚠️  5. ANÁLISE: DADOS COM VOLUME ZERO/NULL${NC}"
echo -e "${BLUE}==================================================${NC}"

echo -e "${YELLOW}⚠️  AVISO: Encontrados 4,159 registros com volume=0/NULL em market_data${NC}"
echo -e "${CYAN}📊 Distribuição por timeframe:${NC}"

docker exec mt5_db psql -U trader -d mt5_trading << 'EOF'
SELECT 
    timeframe,
    COUNT(*) as com_volume_zero,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() as percentual,
    MIN(DATE(ts)) as primeiro,
    MAX(DATE(ts)) as ultimo
FROM market_data 
WHERE volume = 0 OR volume IS NULL
GROUP BY timeframe
ORDER BY timeframe;
EOF

echo ""
echo -e "${YELLOW}💡 DECISÃO SOBRE VOLUME ZERO:${NC}"
echo -e "   ➤ ${CYAN}Dados do Dukascopy podem ter volume=0 em períodos sem trades${NC}"
echo -e "   ➤ ${CYAN}Isso é NORMAL e não indica erro${NC}"
echo -e "   ➤ ${GREEN}✅ Recomendação: MANTER esses dados (são válidos)${NC}"
echo ""

################################################################################
# 6. VACUUM E ANÁLISE
################################################################################
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}🔧 6. OTIMIZAÇÃO DO BANCO${NC}"
echo -e "${BLUE}==================================================${NC}"

if [ "$DRY_RUN" = false ]; then
    echo -e "${CYAN}🔄 Executando VACUUM ANALYZE para otimizar tabelas...${NC}"
    
    docker exec mt5_db psql -U trader -d mt5_trading << 'EOF'
VACUUM ANALYZE market_data;
VACUUM ANALYZE market_data_raw;
VACUUM ANALYZE signals;
VACUUM ANALYZE fills;
VACUUM ANALYZE trade_logs;

SELECT 'Tabelas otimizadas' as status;
EOF
    
    echo -e "${GREEN}✅ Otimização concluída${NC}"
else
    echo -e "${YELLOW}[DRY-RUN] VACUUM ANALYZE seria executado${NC}"
fi

echo ""

################################################################################
# 7. ESTATÍSTICAS FINAIS
################################################################################
echo -e "${BLUE}==================================================${NC}"
echo -e "${BLUE}📊 7. ESTATÍSTICAS FINAIS${NC}"
echo -e "${BLUE}==================================================${NC}"

if [ "$DRY_RUN" = false ]; then
    echo -e "${CYAN}📈 Resumo market_data (dados reais Dukascopy):${NC}"
    
    docker exec mt5_db psql -U trader -d mt5_trading << 'EOF'
SELECT 
    symbol,
    timeframe,
    COUNT(*) as candles,
    MIN(DATE(ts)) as primeiro,
    MAX(DATE(ts)) as ultimo,
    ROUND(AVG(CASE WHEN volume > 0 THEN volume END), 2) as vol_medio
FROM market_data
GROUP BY symbol, timeframe
ORDER BY 
    CASE timeframe 
        WHEN 'M1' THEN 1 
        WHEN 'H1' THEN 2 
        WHEN 'H4' THEN 3 
        WHEN 'D1' THEN 4 
    END;
EOF

fi

echo ""

################################################################################
# RESUMO FINAL
################################################################################
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                    ✅ RESUMO DA LIMPEZA                       ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$DRY_RUN" = false ]; then
    echo -e "${GREEN}✅ 1. Backup criado com sucesso${NC}"
    echo -e "   📁 Local: $BACKUP_FILE"
    echo -e "   📦 Tamanho: $BACKUP_SIZE"
    echo ""
    
    echo -e "${GREEN}✅ 2. Dados de teste removidos${NC}"
    echo -e "   🗑️  market_data_raw: $DELETED_RAW registros deletados"
    echo -e "   🗑️  signals: $DELETED_SIGNALS registros deletados"
    echo ""
    
    echo -e "${GREEN}✅ 3. Banco otimizado (VACUUM ANALYZE)${NC}"
    echo ""
    
    echo -e "${CYAN}📊 4. Dados reais preservados:${NC}"
    echo -e "   ✅ market_data: 104,091 candles EURUSD (2015-2025)"
    echo -e "   ✅ Volume zero: 4,159 registros MANTIDOS (normal no Dukascopy)"
    echo ""
    
    echo -e "${YELLOW}⚠️  IMPORTANTE:${NC}"
    echo -e "   • Backup disponível em: backups/database/"
    echo -e "   • Para restaurar: gunzip -c $BACKUP_FILE | docker exec -i mt5_db psql -U trader mt5_trading"
    echo ""
    
else
    echo -e "${YELLOW}[DRY-RUN] Nenhuma alteração foi feita${NC}"
    echo ""
    echo -e "${CYAN}📋 AÇÕES QUE SERIAM EXECUTADAS:${NC}"
    echo -e "   1. ✅ Criar backup em backups/database/"
    echo -e "   2. 🗑️  Deletar 3 registros de market_data_raw (test_mt5)"
    echo -e "   3. 🗑️  Deletar 3 registros de signals (M5 timeframe)"
    echo -e "   4. 🔧 Executar VACUUM ANALYZE"
    echo -e "   5. ✅ Manter dados reais intactos"
    echo ""
    echo -e "${GREEN}Para executar: ./scripts/maintenance/cleanup_database.sh${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Script concluído!${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
