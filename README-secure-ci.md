# Secure & Efficient CI Workflow

## ENGLISH

This workflow runs pre-commit, lint, security, dependency, YAML/Markdown checks, unit tests, and Docker build on every push and pull request. It blocks merges/deploys if any step fails, ensuring code quality and security.

### Steps

- **Pre-commit:** style, type, and secret checks
- **Ruff/Black:** Python lint and formatting
- **Bandit:** Python security analysis
- **pip-audit:** dependency vulnerability scan
- **detect-secrets:** secret exposure scan
- **yamllint:** YAML config validation
- **markdownlint:** Markdown documentation style
- **pytest:** unit tests and coverage
- **Docker build:** deployment validation
- **Notification:** alerts on failure

---

## PORTUGUÊS

Este workflow executa pre-commit, lint, segurança, dependências, validação de YAML/Markdown, testes e build Docker em todo push e pull request. Bloqueia merges/deploys se qualquer etapa falhar, garantindo qualidade e segurança do código.

### Etapas

- **Pre-commit:** estilo, tipos e checagem de segredos
- **Ruff/Black:** lint e formatação Python
- **Bandit:** análise de segurança Python
- **pip-audit:** verificação de vulnerabilidades em dependências
- **detect-secrets:** busca por segredos expostos
- **yamllint:** validação de configs YAML
- **markdownlint:** estilo da documentação Markdown
- **pytest:** testes unitários e cobertura
- **Build Docker:** validação de deploy
- **Notificação:** alerta em caso de falha
