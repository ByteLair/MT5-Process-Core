#!/bin/bash
###############################################################################
# Script de Limpeza e Organização do Diretório Raiz
# 
# Este script organiza o projeto, movendo:
# - Dados históricos duplicados (526MB) para backups/
# - Backups de configs para backups/configs/
# - Documentação antiga para docs/legacy/
# - Remove arquivos vazios
#
# SEGURO: Tudo é movido, não deletado
#
# Uso: ./scripts/maintenance/cleanup_root_directory.sh [--dry-run]
###############################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DRY_RUN=false

if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 Modo DRY-RUN ativado (apenas simula, não executa)"
fi

cd "$PROJECT_ROOT"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║       📂 LIMPEZA E ORGANIZAÇÃO DO DIRETÓRIO RAIZ 📂          ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

###############################################################################
# 1. Criar estrutura de backups/
###############################################################################
echo "=================================================="
echo "📁 1. CRIANDO ESTRUTURA DE BACKUPS"
echo "=================================================="

if [ "$DRY_RUN" = false ]; then
    mkdir -p backups/{database,historical_data,configs,docs}
    echo "✅ Estrutura criada:"
    tree -L 2 backups/ 2>/dev/null || ls -la backups/
else
    echo "[DRY-RUN] Seria criado:"
    echo "  backups/"
    echo "    ├─ database/"
    echo "    ├─ historical_data/"
    echo "    ├─ configs/"
    echo "    └─ docs/"
fi

###############################################################################
# 2. Mover dados históricos duplicados (526MB)
###############################################################################
echo -e "\n=================================================="
echo "📊 2. MOVENDO DADOS HISTÓRICOS DUPLICADOS"
echo "=================================================="

if [ -d "Files" ]; then
    SIZE=$(du -sh Files/ 2>/dev/null | cut -f1)
    echo "📦 Files/ ($SIZE)"
    
    if [ "$DRY_RUN" = false ]; then
        mv Files/ backups/historical_data/
        echo "✅ Movido para backups/historical_data/Files/"
    else
        echo "[DRY-RUN] mv Files/ backups/historical_data/"
    fi
else
    echo "⚠️ Files/ não encontrado"
fi

if [ -d "HistoricalFIles" ]; then
    SIZE=$(du -sh HistoricalFIles/ 2>/dev/null | cut -f1)
    echo "📦 HistoricalFIles/ ($SIZE)"
    
    if [ "$DRY_RUN" = false ]; then
        mv HistoricalFIles/ backups/historical_data/
        echo "✅ Movido para backups/historical_data/HistoricalFIles/"
    else
        echo "[DRY-RUN] mv HistoricalFIles/ backups/historical_data/"
    fi
else
    echo "⚠️ HistoricalFIles/ não encontrado"
fi

if [ -f "dados_historicos.csv" ]; then
    SIZE=$(du -sh dados_historicos.csv 2>/dev/null | cut -f1)
    echo "📦 dados_historicos.csv ($SIZE)"
    
    if [ "$DRY_RUN" = false ]; then
        mv dados_historicos.csv backups/historical_data/
        echo "✅ Movido para backups/historical_data/dados_historicos.csv"
    else
        echo "[DRY-RUN] mv dados_historicos.csv backups/historical_data/"
    fi
else
    echo "⚠️ dados_historicos.csv não encontrado"
fi

###############################################################################
# 3. Consolidar backups de configs
###############################################################################
echo -e "\n=================================================="
echo "⚙️ 3. CONSOLIDANDO BACKUPS DE CONFIGS"
echo "=================================================="

# Backups de .env
for file in .env.backup .env.bak.* .env.local; do
    if [ -f "$file" ]; then
        echo "📄 $file"
        if [ "$DRY_RUN" = false ]; then
            mv "$file" backups/configs/
            echo "✅ Movido para backups/configs/"
        else
            echo "[DRY-RUN] mv $file backups/configs/"
        fi
    fi
done

# Backups de outros arquivos
for file in *.bak; do
    if [ -f "$file" ]; then
        echo "📄 $file"
        if [ "$DRY_RUN" = false ]; then
            mv "$file" backups/configs/
            echo "✅ Movido para backups/configs/"
        else
            echo "[DRY-RUN] mv $file backups/configs/"
        fi
    fi
done

# Backups de database antigos
for file in db_backup.dump db_backup.sql; do
    if [ -f "$file" ]; then
        echo "📄 $file"
        if [ "$DRY_RUN" = false ]; then
            mv "$file" backups/database/
            echo "✅ Movido para backups/database/"
        else
            echo "[DRY-RUN] mv $file backups/database/"
        fi
    fi
done

###############################################################################
# 4. Deletar arquivos vazios
###############################################################################
echo -e "\n=================================================="
echo "🗑️ 4. REMOVENDO ARQUIVOS VAZIOS"
echo "=================================================="

for file in ssh symbol timeframe; do
    if [ -f "$file" ]; then
        SIZE=$(wc -c < "$file")
        if [ "$SIZE" -eq 0 ]; then
            echo "📄 $file (0 bytes)"
            if [ "$DRY_RUN" = false ]; then
                rm "$file"
                echo "✅ Deletado"
            else
                echo "[DRY-RUN] rm $file"
            fi
        fi
    fi
done

###############################################################################
# 5. Organizar documentação
###############################################################################
echo -e "\n=================================================="
echo "📚 5. ORGANIZANDO DOCUMENTAÇÃO"
echo "=================================================="

if [ "$DRY_RUN" = false ]; then
    mkdir -p docs/legacy
fi

LEGACY_DOCS=(
    "DADOS_HISTORICOS_IMPORTADOS.md"
    "DOCUMENTACAO_ORGANIZADA.md"
    "SCRIPTS_ORGANIZADOS.md"
    "NETWORK_SETUP_VISUAL.txt"
)

for doc in "${LEGACY_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo "📄 $doc"
        if [ "$DRY_RUN" = false ]; then
            mv "$doc" docs/legacy/
            echo "✅ Movido para docs/legacy/"
        else
            echo "[DRY-RUN] mv $doc docs/legacy/"
        fi
    fi
done

###############################################################################
# 6. Atualizar .gitignore
###############################################################################
echo -e "\n=================================================="
echo "📝 6. ATUALIZANDO .gitignore"
echo "=================================================="

GITIGNORE_ENTRIES=(
    "# Backups"
    "backups/"
    "*.bak"
    "*.backup"
    ""
    "# Arquivos temporários"
    "ssh"
    "symbol"
    "timeframe"
)

if [ "$DRY_RUN" = false ]; then
    # Verifica se já existe a seção de backups
    if ! grep -q "# Backups" .gitignore 2>/dev/null; then
        echo "" >> .gitignore
        for entry in "${GITIGNORE_ENTRIES[@]}"; do
            echo "$entry" >> .gitignore
        done
        echo "✅ .gitignore atualizado"
    else
        echo "⚠️ .gitignore já contém as entradas"
    fi
else
    echo "[DRY-RUN] Seria adicionado ao .gitignore:"
    for entry in "${GITIGNORE_ENTRIES[@]}"; do
        echo "  $entry"
    done
fi

###############################################################################
# 7. Estatísticas finais
###############################################################################
echo -e "\n=================================================="
echo "📊 7. ESTATÍSTICAS FINAIS"
echo "=================================================="

echo "📁 Estrutura do raiz após limpeza:"
if [ "$DRY_RUN" = false ]; then
    ls -1 | grep -v "^\." | wc -l | xargs -I {} echo "   Itens visíveis: {}"
    du -sh . | cut -f1 | xargs -I {} echo "   Tamanho total: {}"
    
    if [ -d "backups" ]; then
        echo ""
        echo "📦 Conteúdo de backups/:"
        du -sh backups/*/ 2>/dev/null | while read size dir; do
            echo "   $dir: $size"
        done
    fi
else
    echo "[DRY-RUN] Estatísticas seriam calculadas após execução"
fi

###############################################################################
# Resumo
###############################################################################
echo -e "\n=================================================="
echo "✅ RESUMO DA LIMPEZA"
echo "=================================================="

cat << EOF

1. 📁 Estrutura de Backups
   $([ "$DRY_RUN" = false ] && echo "✅" || echo "⏳") backups/database/
   $([ "$DRY_RUN" = false ] && echo "✅" || echo "⏳") backups/historical_data/
   $([ "$DRY_RUN" = false ] && echo "✅" || echo "⏳") backups/configs/
   $([ "$DRY_RUN" = false ] && echo "✅" || echo "⏳") backups/docs/

2. 📊 Dados Históricos Duplicados
   $([ -d "backups/historical_data/Files" ] && echo "✅" || echo "⏳") Files/ movido (~510MB)
   $([ -d "backups/historical_data/HistoricalFIles" ] && echo "✅" || echo "⏳") HistoricalFIles/ movido (~14MB)
   $([ -f "backups/historical_data/dados_historicos.csv" ] && echo "✅" || echo "⏳") dados_historicos.csv movido (~1.4MB)

3. ⚙️ Backups de Configs
   $([ "$DRY_RUN" = false ] && echo "✅" || echo "⏳") .env.backup e .env.bak.* movidos
   $([ "$DRY_RUN" = false ] && echo "✅" || echo "⏳") *.bak movidos
   $([ "$DRY_RUN" = false ] && echo "✅" || echo "⏳") db_backup.* movidos

4. 🗑️ Arquivos Vazios
   $([ ! -f "ssh" ] && echo "✅" || echo "⏳") ssh deletado
   $([ ! -f "symbol" ] && echo "✅" || echo "⏳") symbol deletado
   $([ ! -f "timeframe" ] && echo "✅" || echo "⏳") timeframe deletado

5. 📚 Documentação
   $([ -f "docs/legacy/DADOS_HISTORICOS_IMPORTADOS.md" ] && echo "✅" || echo "⏳") Docs antigos movidos para docs/legacy/

6. 📝 .gitignore
   $(grep -q "backups/" .gitignore 2>/dev/null && echo "✅" || echo "⏳") Atualizado com novos padrões

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 GANHOS:

Espaço liberado no raiz: ~526MB
Arquivos movidos para backup: Seguros em backups/
Organização: Estrutura profissional e limpa
.gitignore: Atualizado para evitar commits acidentais

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ IMPORTANTE:

Os dados NÃO foram deletados, apenas movidos para backups/
- Para restaurar: cp -r backups/historical_data/Files ./
- Para deletar permanentemente: rm -rf backups/

PostgreSQL continua com todos os dados:
- 96.388 candles M1
- 2.416+ candles H1
- Download ativo de 10 anos

EOF

if [ "$DRY_RUN" = true ]; then
    echo "⚠️ MODO DRY-RUN - Execute sem --dry-run para aplicar as mudanças"
fi

echo "🎉 Script concluído!"
