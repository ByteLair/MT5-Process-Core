# Complete & Secure CI Workflow

## ENGLISH

This workflow runs tests on multiple Python versions and OS, checks style, security, dependencies, configs, large files, commit messages, builds Docker images, saves artifacts, and deploys to staging. All steps are commented in English and Portuguese.

### Steps

- Test matrix: Python 3.10/3.11/3.12, Ubuntu/macOS/Windows
- Pre-commit, Ruff, Black, Bandit, pip-audit, detect-secrets, yamllint, markdownlint
- Pytest with coverage and Codecov badge
- Docker Compose validation
- Large file check
- Commit message validation
- Artifact upload
- Docker build
- Notification on failure
- Deploy to staging

## PORTUGUÊS

Este workflow executa testes em múltiplas versões do Python e sistemas operacionais, valida estilo, segurança, dependências, configs, arquivos grandes, mensagens de commit, builda Docker, salva artefatos e faz deploy em staging. Todos os passos têm comentários em inglês e português.

### Etapas

- Testes: Python 3.10/3.11/3.12, Ubuntu/macOS/Windows
- Pre-commit, Ruff, Black, Bandit, pip-audit, detect-secrets, yamllint, markdownlint
- Pytest com cobertura e badge do Codecov
- Validação do Docker Compose
- Checagem de arquivos grandes
- Validação de mensagem de commit
- Upload de artefatos
- Build Docker
- Notificação em caso de falha
- Deploy em staging

---

For details, see `.github/workflows/complete-ci.yml`.
Para detalhes, veja `.github/workflows/complete-ci.yml`.
