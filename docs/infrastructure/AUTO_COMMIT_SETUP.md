# 🤖 Auto-Commit Configuration

Sistema de commits automáticos diários com versionamento e mensagens inteligentes.

## 📅 Agendamento

**Horário:** 4:00 AM (UTC-3) todos os dias
**Execução:** Via GitHub Actions no runner self-hosted

## 🎯 O que faz

1. Detecta mudanças no repositório
2. Gera commit com mensagem descritiva automática
3. Inclui estatísticas (arquivos adicionados/modificados/deletados)
4. Lista até 10 arquivos modificados
5. Faz push automático para `main`
6. Adiciona `[skip ci]` para evitar loop de CI/CD

## 🚀 Como Usar

### Opção 1: GitHub Actions (Recomendado)

O workflow `.github/workflows/auto-commit.yml` já está configurado!

**Agendamento:**

- Automático: Diariamente às 4:00 AM (UTC-3)
- Manual: Via GitHub Actions interface

**Ativar manualmente:**

1. Vá para: <https://github.com/Lysk-dot/mt5-trading-db/actions>
2. Selecione "Auto Commit Daily"
3. Clique em "Run workflow"

### Opção 2: Script Manual

Execute o script quando quiser:

```bash
cd /home/felipe/MT5-Process-Core-full
./scripts/auto-commit.sh
```

### Opção 3: Crontab Local (Backup)

Se quiser executar localmente no servidor:

```bash
# Editar crontab
crontab -e

# Adicionar linha (4:00 AM todos os dias)
0 4 * * * cd /home/felipe/MT5-Process-Core-full && ./scripts/auto-commit.sh >> /home/felipe/MT5-Process-Core-full/logs/auto-commit.log 2>&1
```

## 📋 Formato da Mensagem de Commit

```
chore: automated commit - 2025-10-18 04:00:00 UTC-3

Auto-generated commit by scheduled workflow

Changes summary:
- Added: 2 file(s)
- Modified: 5 file(s)
- Deleted: 0 file(s)

Modified files:
  - api/main.py
  - docs/README.md
  - scripts/backup.sh
  - ml/train_model.py
  - docker-compose.yml

[skip ci]
```

## 🔧 Configurações

### Modificar Horário

Edite `.github/workflows/auto-commit.yml`:

```yaml
on:
  schedule:
    # Formato: "minuto hora * * *"
    - cron: '0 7 * * *'  # 7:00 UTC = 4:00 UTC-3
```

**Exemplos de horários:**

- `0 7 * * *` - 4:00 AM (UTC-3) diariamente
- `0 10 * * *` - 7:00 AM (UTC-3) diariamente
- `0 7 * * 1` - 4:00 AM (UTC-3) toda segunda-feira
- `0 7 1 * *` - 4:00 AM (UTC-3) dia 1 de cada mês

### Excluir Arquivos

Adicione ao `.gitignore`:

```bash
# Arquivos temporários
*.tmp
*.log

# Modelos ML grandes
ml/models/*.pkl
models/*.h5

# Dados sensíveis
.env
*.key
```

### Filtrar Apenas Certos Arquivos

Modifique o script `scripts/auto-commit.sh`:

```bash
# Adicionar apenas arquivos Python
git add **/*.py

# Adicionar apenas docs
git add docs/**/*.md

# Adicionar tudo exceto logs
git add -A
git reset logs/
```

## 🛡️ Segurança

**Atenção:** Commits automáticos podem incluir:

- ❌ Arquivos sensíveis (.env, chaves)
- ❌ Dados pessoais
- ❌ Credenciais

**Proteções implementadas:**

- ✅ `.gitignore` respeita exclusões
- ✅ `[skip ci]` evita loop infinito
- ✅ Commits descritivos para auditoria

**Recomendações:**

- Revise `.gitignore` regularmente
- Monitore commits automáticos no GitHub
- Use `git secrets` para detectar credenciais

## 📊 Monitoramento

### Ver Histórico de Auto-Commits

```bash
# Últimos 10 commits automáticos
git log --grep="automated commit" --oneline -10

# Ver detalhes do último auto-commit
git log --grep="automated commit" -1 --stat

# Commits automáticos da última semana
git log --grep="automated commit" --since="1 week ago"
```

### Logs do Workflow

Ver execuções:
<https://github.com/Lysk-dot/mt5-trading-db/actions/workflows/auto-commit.yml>

### Logs do Script Local (se usar crontab)

```bash
tail -f ~/mt5-trading-db/logs/auto-commit.log
```

## 🔄 Desabilitar Auto-Commits

### Desabilitar GitHub Actions

1. Vá para: <https://github.com/Lysk-dot/mt5-trading-db/settings/actions>
2. Desabilite o workflow "Auto Commit Daily"

Ou remova/renomeie o arquivo:

```bash
mv .github/workflows/auto-commit.yml .github/workflows/auto-commit.yml.disabled
```

### Desabilitar Crontab

```bash
crontab -e
# Comente ou remova a linha do auto-commit
```

## 🧪 Testar Auto-Commit

### Teste Manual

```bash
# Criar mudança de teste
echo "test" > test_file.txt

# Executar auto-commit
./scripts/auto-commit.sh

# Verificar no GitHub
git log -1
```

### Teste via GitHub Actions

1. Faça uma mudança qualquer
2. Vá para Actions → Auto Commit Daily
3. Clique em "Run workflow"
4. Acompanhe a execução

## 📚 Referências

- [GitHub Actions Cron Syntax](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule)
- [Crontab Guru (testar cron)](https://crontab.guru/)
- [Git Automation Best Practices](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)

---

**Última atualização:** Outubro 2025
**Status:** ✅ Ativo e funcionando
