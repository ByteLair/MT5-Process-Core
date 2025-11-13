<!-- =============================================================
Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
All rights reserved. | Todos os direitos reservados.
Private License: This code is the exclusive property of Felipe Petracco Carmo.
Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
============================================================= -->

# ✅ Pre-commit Setup Complete

O sistema de pre-commit hooks foi configurado com sucesso no repositório MT5 Trading DB.

---

## 🎉 O que foi instalado

### ✅ Configurações Criadas

1. **`.pre-commit-config.yaml`** - Configuração principal (14 repositórios, 30+ hooks)
2. **`.bandit.yaml`** - Configuração de segurança Python
3. **`.secrets.baseline`** - Baseline para detecção de secrets
4. **`.markdownlint.yaml`** - Configuração para Markdown
5. **`.editorconfig`** - Consistência de código entre editores

### ✅ Hooks Instalados no Git

- ✅ `pre-commit` - Roda antes de cada commit
- ✅ `commit-msg` - Valida mensagens de commit
- ✅ `pre-push` - Roda antes de cada push

### ✅ Documentação

- 📚 **`docs/PRE_COMMIT_GUIDE.md`** - Guia completo de uso
- 🔧 **`scripts/precommit-helper.sh`** - Script auxiliar

---

## 🚀 Quick Start

### Uso Básico

```bash
# Fazer alterações no código
vim api/app/main.py

# Stage e commit (hooks rodam automaticamente)
git add api/app/main.py
git commit -m "feat: adiciona novo endpoint"

# Se hooks falharem e fizerem correções:
git add api/app/main.py
git commit -m "feat: adiciona novo endpoint"
```

### Comandos Úteis

```bash
# Ver status do pre-commit
./scripts/precommit-helper.sh status

# Rodar em todos os arquivos
./scripts/precommit-helper.sh run-all

# Rodar apenas formatadores
./scripts/precommit-helper.sh format

# Rodar apenas verificações de segurança
./scripts/precommit-helper.sh security

# Atualizar hooks para versões mais recentes
./scripts/precommit-helper.sh update

# Ver ajuda completa
./scripts/precommit-helper.sh help
```

---

## 🔍 Hooks Configurados

### Python Quality (5)

- ✅ **Ruff** - Linting ultra-rápido
- ✅ **Black** - Formatação de código
- ✅ **isort** - Organização de imports
- ✅ **mypy** - Type checking
- ✅ **interrogate** - Cobertura de docstrings

### Security (3)

- 🔒 **Bandit** - Vulnerabilidades Python
- 🔒 **Detect Secrets** - Credenciais commitadas
- 🔒 **Safety** - Vulnerabilidades em dependências

### Docker & Shell (2)

- 🐳 **Hadolint** - Linting de Dockerfiles
- 🐚 **ShellCheck** - Linting de shell scripts

### Documentation (2)

- 📚 **Markdownlint** - Linting de Markdown
- 📝 **Interrogate** - Docstring coverage

### SQL (2)

- 💾 **SQLFluff Lint** - Linting SQL
- 💾 **SQLFluff Fix** - Auto-fix SQL

### General (14+)

- ✅ Trailing whitespace
- ✅ End of file fixer
- ✅ YAML/JSON/TOML syntax
- ✅ Large files check
- ✅ Merge conflicts
- ✅ Case conflicts
- ✅ Debug statements
- ✅ Private keys detection
- ✅ Mixed line endings
- E mais...

### Custom (1)

- ©️ **Copyright Header** - Adiciona headers de copyright

---

## 📊 Estatísticas

```
Total de Hooks Configurados: 30+
Repositórios: 14
Arquivos de Configuração: 5
Documentação: 2 arquivos
Scripts Auxiliares: 1
```

---

## 📚 Documentação Completa

Para mais detalhes, consulte:

- **[docs/PRE_COMMIT_GUIDE.md](docs/PRE_COMMIT_GUIDE.md)** - Guia completo
  - Instalação detalhada
  - Descrição de cada hook
  - Troubleshooting
  - Boas práticas
  - Configuração avançada

---

## 🎯 Próximos Passos

### 1. Testar o Sistema

```bash
# Teste completo
./scripts/precommit-helper.sh test

# Rodar em todos os arquivos pela primeira vez
./scripts/precommit-helper.sh run-all
```

### 2. Configurar IDE

Para VSCode, instale as extensões:

- **Ruff** - charliermarsh.ruff
- **Black Formatter** - ms-python.black-formatter
- **Mypy Type Checker** - ms-python.mypy-type-checker
- **ShellCheck** - timonwong.shellcheck

### 3. Configurar CI/CD

Adicione ao `.github/workflows/ci.yml`:

```yaml
- name: Run pre-commit
  uses: pre-commit/action@v3.0.0
```

---

## 🐛 Troubleshooting

### Problema: Hook muito lento

```bash
# Desabilitar hooks pesados temporariamente
SKIP=mypy,bandit git commit -m "mensagem"
```

### Problema: Preciso commitar urgente

```bash
# ⚠️ Use apenas em emergências!
git commit --no-verify -m "mensagem"
```

### Problema: Hook falhando consistentemente

```bash
# Limpar cache e reinstalar
pre-commit clean
pre-commit install --install-hooks
pre-commit run --all-files
```

---

## ⚙️ Personalização

### Desabilitar um hook específico

Edite `.pre-commit-config.yaml` e comente o hook:

```yaml
# - id: mypy
#   name: Type check with mypy
```

### Adicionar exceções

Edite a seção `exclude:` no final do `.pre-commit-config.yaml`:

```yaml
exclude: |
  (?x)^(
      seu/diretorio/aqui/
  )$
```

### Ajustar severidade

Edite os arquivos de configuração:

- `.bandit.yaml` - Para Bandit
- `.markdownlint.yaml` - Para Markdownlint
- `mypy.ini` - Para mypy

---

## 🤝 Para o Time

### Ao fazer Pull Request

1. ✅ Certifique-se de que todos os hooks passam
2. ✅ Rode `./scripts/precommit-helper.sh run-all` antes do PR
3. ✅ Não commite com `--no-verify`
4. ✅ Se precisar adicionar exceção, documente o motivo

### Boas Práticas

- ✅ Mantenha hooks atualizados mensalmente
- ✅ Rode formatadores regularmente
- ✅ Não ignore avisos de segurança
- ✅ Corrija problemas apontados pelos hooks

---

## 📞 Suporte

Para dúvidas ou problemas:

1. Consulte `docs/PRE_COMMIT_GUIDE.md`
2. Rode `./scripts/precommit-helper.sh help`
3. Abra uma issue no GitHub

---

## 🎉 Benefícios Imediatos

✅ **Qualidade de Código** - Padrões consistentes em todo o projeto
✅ **Segurança** - Detecção precoce de vulnerabilidades
✅ **Produtividade** - Menos tempo em code reviews
✅ **Confiabilidade** - Menos bugs em produção
✅ **Manutenibilidade** - Código mais limpo e organizado

---

**Status:** ✅ **TOTALMENTE CONFIGURADO E FUNCIONAL**

**Última atualização:** 2025-10-20
**Versão:** 1.0.0
**Mantido por:** Felipe
