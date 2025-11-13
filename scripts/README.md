# 🛠️ Scripts - MT5 Process Core

**Última Atualização:** 13 de Novembro de 2025  
**Total de Scripts:** 80+  
**Status:** ✅ Organizado

---

## 📂 Estrutura

```
scripts/
├── 📁 backup/          (4 scripts)   - Backup e restore
├── 📁 database/        (6 scripts)   - Database management
├── 📁 deployment/      (11 scripts)  - Deploy e infra
├── 📁 testing/         (8 scripts)   - Testes automatizados
├── 📁 monitoring/      (9 scripts)   - Monitoramento e health
├── 📁 network/         (5 scripts)   - Network optimization
├── 📁 analysis/        (3 scripts)   - Análise de dados
├── 📁 utilities/       (7 scripts)   - Utilitários gerais
└── 📄 Raiz             (23 scripts)  - Scripts principais
```

---

## 📁 Categorias

### 💾 Backup (4 scripts)

| Script | Descrição | Uso |
|--------|-----------|-----|
| `backup.sh` | Backup completo do sistema | `./backup.sh` |
| `create-snapshot.sh` | Criar snapshot | `./backup/create-snapshot.sh` |
| `restore-snapshot.sh` | Restaurar snapshot | `./backup/restore-snapshot.sh` |
| `INSTALL_BACKUP.sh` | Setup de backup | `./backup/INSTALL_BACKUP.sh` |

**Localização:** `scripts/backup/`

---

### 🗄️ Database (6 scripts)

| Script | Descrição | Frequência |
|--------|-----------|-----------|
| `db_maintenance.sh` | Manutenção do PostgreSQL | Diário |
| `pg_backup.sh` | Backup do PostgreSQL | Diário |
| `tune_postgres_memory.sh` | Otimizar memória | Setup |
| `import_csv.py` | Importar CSV | Manual |
| `import_historical.sh` | Importar histórico | Manual |
| `load_test_pool.py` | Teste de pool | Testing |

**Localização:** `scripts/database/`

**Comandos Úteis:**
```bash
# Manutenção diária
./scripts/database/db_maintenance.sh

# Backup
./scripts/database/pg_backup.sh

# Otimizar configuração
./scripts/database/tune_postgres_memory.sh
```

---

### 🚀 Deployment (11 scripts)

| Script | Descrição | Uso |
|--------|-----------|-----|
| `k8s-deploy.sh` | Deploy Kubernetes | `./k8s-deploy.sh <env>` |
| `k8s-healthcheck.sh` | Health check K8S | `./k8s-healthcheck.sh` |
| `k8s-logs.sh` | Ver logs K8S | `./k8s-logs.sh <pod>` |
| `k8s-rollback.sh` | Rollback K8S | `./k8s-rollback.sh` |
| `k8s-scale.sh` | Escalar pods | `./k8s-scale.sh <replicas>` |
| `setup_infrastructure.sh` | Setup infra | `./setup_infrastructure.sh` |
| `update_stack.sh` | Atualizar stack | `./update_stack.sh` |
| `cpu_tune.sh` | Otimizar CPU | `./cpu_tune.sh` |
| `fix_bind_mounts_permissions.sh` | Fix permissões | `./fix_bind_mounts_permissions.sh` |
| `fix_docker.sh` | Fix Docker | `./fix_docker.sh` |
| `setup_docker_permissions.sh` | Setup Docker | `./setup_docker_permissions.sh` |

**Localização:** `scripts/deployment/`

**Quick Start:**
```bash
# Deploy desenvolvimento
./scripts/deployment/k8s-deploy.sh dev

# Deploy produção
./scripts/deployment/k8s-deploy.sh production

# Health check
./scripts/deployment/k8s-healthcheck.sh
```

---

### 🧪 Testing (8 scripts)

| Script | Descrição | Tipo |
|--------|-----------|------|
| `smoke_ingest.sh` | Teste de ingestão | Smoke |
| `smoke_query.sh` | Teste de queries | Smoke |
| `smoke_test_bulk.sh` | Teste bulk | Smoke |
| `smoke_test_single.sh` | Teste single | Smoke |
| `test-automated.sh` | Testes automatizados | Full |
| `test-backup.sh` | Teste de backup | Validation |
| `test_ea_simulation.sh` | Simulação EA | Integration |
| `test_hybrid_flow.sh` | Teste fluxo híbrido | Integration |

**Localização:** `scripts/testing/`

**Executar Testes:**
```bash
# Smoke tests rápidos
./scripts/testing/smoke_ingest.sh
./scripts/testing/smoke_query.sh

# Teste completo
./scripts/testing/test-automated.sh

# Teste do fluxo híbrido
./scripts/testing/test_hybrid_flow.sh
```

---

### 📊 Monitoring (9 scripts)

| Script | Descrição | Intervalo |
|--------|-----------|-----------|
| `monitor_backups.sh` | Monitorar backups | 1h |
| `monitor_dados.sh` | Monitorar dados | 5m |
| `monitor_ingest_realtime.sh` | Monitorar ingestão | Realtime |
| `monitor-backup.sh` | Monitorar sistema backup | 30m |
| `healthcheck.sh` | Health check geral | 1m |
| `health-check.sh` | Health check detalhado | 5m |
| `health_unhealthy_check.sh` | Check unhealthy | On-demand |
| `health-dashboard.py` | Dashboard de saúde | Web |
| `daily_report.sh` | Relatório diário | 1d |

**Localização:** `scripts/monitoring/`

**Monitoramento:**
```bash
# Health check rápido
./scripts/monitoring/healthcheck.sh

# Dashboard
python ./scripts/monitoring/health-dashboard.py

# Relatório diário
./scripts/monitoring/daily_report.sh
```

---

### 🌐 Network (5 scripts)

| Script | Descrição | Uso |
|--------|-----------|-----|
| `network_health_check.sh` | Health check de rede | Diagnóstico |
| `network_load_test.sh` | Teste de carga | Performance |
| `network_monitor.sh` | Monitorar rede | Continuous |
| `network_quick_setup.sh` | Setup rápido | Setup |
| `optimize_network.sh` | Otimizar rede | Tuning |

**Localização:** `scripts/network/`

**Network Tools:**
```bash
# Health check
./scripts/network/network_health_check.sh

# Otimizar
./scripts/network/optimize_network.sh

# Monitorar
./scripts/network/network_monitor.sh
```

---

### 🔬 Analysis (3 scripts)

| Script | Descrição | Output |
|--------|-----------|--------|
| `analisa_modelo.py` | Analisar modelo ML | Métricas |
| `analisa_threshold.py` | Analisar threshold | Gráficos |
| `test_database.py` | Analisar database | Estatísticas |

**Localização:** `scripts/analysis/`

**Análise:**
```bash
# Analisar modelo
python ./scripts/analysis/analisa_modelo.py

# Analisar threshold
python ./scripts/analysis/analisa_threshold.py

# Analisar database
python ./scripts/analysis/test_database.py
```

---

### 🔧 Utilities (7 scripts)

| Script | Descrição | Uso |
|--------|-----------|-----|
| `generate_userlist.sh` | Gerar userlist | Setup |
| `update_project_paths.sh` | Atualizar paths | Manutenção |
| `freeze_requirements.sh` | Freeze deps | Release |
| `add_header.py` | Adicionar headers | Dev |
| `precommit-helper.sh` | Helper pre-commit | Dev |
| `precommit-quickstart.sh` | Setup pre-commit | Setup |
| `check_vulnerabilities.sh` | Check CVEs | Security |

**Localização:** `scripts/utilities/`

---

### 📄 Scripts na Raiz (23 scripts)

Scripts principais e de orquestração:

**Principais:**
- `quickstart.sh` - Quick start do projeto
- `auto-commit.sh` - Auto commit
- `backup-full-repo.sh` - Backup completo
- `commit_version.sh` - Commit de versão
- `enviar-backup.sh` - Enviar backup
- `git_commit_email_notify.sh` - Notificações git
- `install_*.sh` - Scripts de instalação
- `maintenance.sh` - Manutenção geral
- `restore.sh` - Restore geral
- `setup-*.sh` - Scripts de setup
- `start_github_runner.sh` - GitHub Runner
- `check_github_runner.sh` - Check runner
- `ingest_files.py` - Ingerir arquivos
- `log_diario_ia.sh` - Log diário IA
- `weekly-backup-flow.sh` - Backup semanal

---

## 🚀 Quick Start

### Setup Inicial

```bash
# 1. Quick start do projeto
./scripts/quickstart.sh

# 2. Setup de infraestrutura
./scripts/deployment/setup_infrastructure.sh

# 3. Setup de permissões Docker
./scripts/deployment/setup_docker_permissions.sh

# 4. Setup de backup
./scripts/setup-backup.sh

# 5. Setup de health check
./scripts/setup-health-check.sh
```

### Operação Diária

```bash
# Health check
./scripts/monitoring/healthcheck.sh

# Monitorar dados
./scripts/monitoring/monitor_dados.sh

# Manutenção do banco
./scripts/database/db_maintenance.sh

# Backup
./scripts/database/pg_backup.sh
```

### Testes

```bash
# Smoke tests
./scripts/testing/smoke_ingest.sh
./scripts/testing/smoke_query.sh

# Teste completo
./scripts/testing/test-automated.sh
```

### Deploy

```bash
# Deploy K8S
./scripts/deployment/k8s-deploy.sh production

# Health check
./scripts/deployment/k8s-healthcheck.sh

# Ver logs
./scripts/deployment/k8s-logs.sh mt5-api
```

---

## 📋 Convenções

### Nomenclatura

- `setup_*.sh` - Scripts de configuração inicial
- `install_*.sh` - Scripts de instalação
- `monitor_*.sh` - Scripts de monitoramento
- `test_*.sh` - Scripts de teste
- `k8s-*.sh` - Scripts Kubernetes
- `*_backup.sh` - Scripts de backup
- `check_*.sh` - Scripts de verificação

### Parâmetros Comuns

```bash
# Ambiente
./script.sh dev|staging|production

# Verbosidade
./script.sh -v          # Verbose
./script.sh --debug     # Debug mode

# Dry-run
./script.sh --dry-run   # Simular sem executar

# Help
./script.sh --help      # Ajuda
./script.sh -h          # Ajuda curta
```

---

## 🔍 Buscar Scripts

### Por Funcionalidade

```bash
# Backup
find scripts/ -name "*backup*"

# Monitoramento
find scripts/ -name "*monitor*" -o -name "*health*"

# Kubernetes
find scripts/ -name "k8s-*"

# Testes
find scripts/testing/ -name "*.sh"
```

### Por Tipo

```bash
# Bash scripts
find scripts/ -name "*.sh"

# Python scripts
find scripts/ -name "*.py"

# Por categoria
ls scripts/database/
ls scripts/deployment/
ls scripts/testing/
```

---

## 🛡️ Permissões

### Tornar Executável

```bash
# Um script
chmod +x scripts/monitoring/healthcheck.sh

# Todos os scripts
find scripts/ -name "*.sh" -exec chmod +x {} \;

# Por categoria
chmod +x scripts/deployment/*.sh
```

### Verificar Permissões

```bash
# Listar scripts sem permissão de execução
find scripts/ -name "*.sh" ! -perm -u+x

# Verificar script específico
ls -l scripts/monitoring/healthcheck.sh
```

---

## 📊 Estatísticas

### Por Categoria

| Categoria | Scripts | Linhas | Uso |
|-----------|---------|--------|-----|
| **Deployment** | 11 | ~2,500 | Setup, deploy, K8S |
| **Monitoring** | 9 | ~2,000 | Health, metrics |
| **Testing** | 8 | ~1,500 | Testes automatizados |
| **Utilities** | 7 | ~1,200 | Ferramentas dev |
| **Database** | 6 | ~1,800 | DB management |
| **Network** | 5 | ~1,000 | Network tools |
| **Backup** | 4 | ~800 | Backup/restore |
| **Analysis** | 3 | ~600 | Análise de dados |
| **Raiz** | 23 | ~4,000 | Orquestração |
| **TOTAL** | **80** | **~15,400** | - |

### Por Linguagem

- 🐚 **Bash:** 68 scripts (~85%)
- 🐍 **Python:** 12 scripts (~15%)

### Por Frequência de Uso

- ⚡ **Contínuo:** 8 scripts (monitoring, realtime)
- 🔄 **Diário:** 12 scripts (backup, maintenance)
- 📅 **Semanal:** 5 scripts (reports, cleanup)
- 🛠️ **Manual:** 55 scripts (setup, analysis, troubleshooting)

---

## 🤝 Contribuindo

### Adicionar Novo Script

1. Criar script na categoria apropriada
2. Adicionar header padrão:
```bash
#!/bin/bash
# Script: nome_do_script.sh
# Descrição: O que o script faz
# Autor: Seu Nome
# Data: YYYY-MM-DD
```

3. Tornar executável:
```bash
chmod +x scripts/categoria/nome_do_script.sh
```

4. Atualizar este README

5. Commit:
```bash
git add scripts/
git commit -m "scripts: adiciona novo_script na categoria X"
```

---

## 📞 Suporte

- 📧 **Issues:** [GitHub Issues](https://github.com/ByteLair/MT5-Process-Core/issues)
- 📚 **Documentação:** `docs/`
- 💬 **Discussões:** [GitHub Discussions](https://github.com/ByteLair/MT5-Process-Core/discussions)

---

## 🔗 Links Relacionados

- [README Principal](../README.md)
- [Documentação](../docs/README.md)
- [Guia de Deploy](../docs/kubernetes/K8S_DEPLOYMENT.md)
- [Guia de Testes](../docs/testing/GUIA_TESTES.md)

---

**Mantido por:** Equipe MT5 Process Core  
**Última Atualização:** 13 de Novembro de 2025  
**Versão:** 2.0
