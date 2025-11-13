# 📚 Índice Completo de Documentação - MT5 Process Core

**Última Atualização:** 13 de Novembro de 2025  
**Total de Documentos:** 60+  
**Status:** ✅ Organizado

---

## 📂 Estrutura de Pastas

```
docs/
├── README.md                          # 👈 Índice principal
├── RESUMO_EXECUTIVO_TESTES.md        # Resumo da sprint de testes
├── CONTRIBUTING.md                    # Como contribuir
├── CONTRACTS.md                       # Contratos e interfaces
├── CHANGELOG_ML_TESTS.md             # Changelog de testes ML
├── DIAGRAMS.md                        # Diagramas do sistema
├── DOCUMENTATION.md                   # Meta-documentação
├── EXAMPLES.md                        # Exemplos práticos
├── FAQ.md                            # Perguntas frequentes
├── GLOSSARY.md                        # Glossário de termos
├── HYBRID_INGESTION_FLOW.md          # Fluxo de ingestão híbrido
├── ONBOARDING.md                      # Guia de onboarding
├── PERFORMANCE.md                     # Análise de performance
├── PRE_COMMIT_GUIDE.md               # Guia de pre-commit
├── PRECOMMIT_SUMMARY.md              # Resumo pre-commit
├── PRE_COMMIT_FILES_INDEX.md         # Índice de arquivos
├── RECONSTRUCTION_LOG.md              # Log de reconstrução
├── RECOVERY_AND_ML_RUNBOOK.md        # Runbook de recovery
├── RUNBOOK.md                         # Runbook operacional
├── SECURITY_SECRETS_ALLOWLIST.md     # Allowlist de secrets
├── TESTS_ML_COVERAGE_REPORT.md       # Cobertura de testes ML
├── TESTS_ML_INTEGRATION.md           # Integração de testes ML
├── TEST_COVERAGE_IMPROVEMENT_REPORT.md # Melhoria de cobertura
├── backup.md                          # Guia de backup
│
├── architecture/                      # 🏛️ Arquitetura
│   └── ANALISE_COMPLETA_PROJETO.md   # Análise arquitetural completa
│
├── infrastructure/                    # 🔧 Infraestrutura
│   ├── ALL_CONTAINERS_RUNNING.md     # Guia de containers
│   ├── AUTOSCALING_AND_SNAPSHOTS.md  # Auto-scaling e snapshots
│   ├── AUTO_COMMIT_SETUP.md          # Setup de auto-commit
│   ├── CONNECTION_POOLING.md         # Pool de conexões
│   ├── CONTAINERS_STATUS.md          # Status dos containers
│   ├── DEPLOYMENT_STATUS.md          # Status de deployment
│   ├── DEPLOYMENT_STATUS_FINAL.md    # Status final
│   ├── GITHUB_ACTIONS_REPORT.md      # Relatório GitHub Actions
│   ├── HEALTH_CHECK_SYSTEM.md        # Sistema de health check
│   ├── INFRASTRUCTURE_IMPROVEMENTS.md # Melhorias de infra
│   ├── NETWORK_OPTIMIZATION_GUIDE.md # Otimização de rede
│   ├── NETWORK_OPTIMIZATION_SUMMARY.md # Resumo otimização
│   ├── NETWORK_TOOLS_README.md       # Ferramentas de rede
│   ├── OBSERVABILITY_QUICKSTART.md   # Quick start observability
│   ├── OBSERVABILITY_STACK.md        # Stack de observability
│   ├── README-complete-ci.md         # CI/CD completo
│   ├── README-secure-ci.md           # CI/CD seguro
│   ├── RELATORIO_PGBOUNCER_TESTES.md # Fix PgBouncer
│   ├── SETUP_SELF_HOSTED_RUNNER.md   # Setup runner
│   └── TERRAFORM_DASHBOARD_SUMMARY.md # Terraform + Grafana
│
├── testing/                           # 🧪 Testes
│   ├── DATABASE_TEST_REPORT.md       # Relatório de testes DB
│   ├── GUIA_TESTES.md                # Guia prático de testes
│   ├── RELATORIO_COBERTURA_TESTES.md # Cobertura 26%
│   ├── SNAPSHOT_TEST_REPORT.md       # Relatório de snapshots
│   └── SPRINT_TESTES_CONCLUIDA.md    # Resumo da sprint
│
├── guides/                            # 📖 Guias Práticos
│   ├── EA_CHECKLIST.md               # Checklist para EA
│   ├── EA_DEBUG_GUIDE.md             # Debug do EA MT5
│   └── EA_INTEGRATION_GUIDE.md       # Integração com MT5
│
├── reference/                         # 📚 Referência
│   ├── DOCUMENTACAO_COMPLETA.md      # Documentação em PT-BR
│   ├── DOCUMENTACAO_LICENCA_AUTOMACAO.md # Licenças
│   ├── DOCUMENTATION_COMPLETE.md     # Documentação completa EN
│   ├── PROJECT_STRUCTURE.md          # Estrutura do projeto
│   ├── README_COMPLETE.md            # README completo
│   ├── README_RECOVERY.md            # Recovery guide
│   ├── README.legacy.md              # README legado
│   ├── SQL_QUERIES.md                # Queries úteis
│   └── WARNINGS_FIXED.md             # Avisos corrigidos
│
├── kubernetes/                        # ☸️ Kubernetes
│   ├── K8S_DEPLOYMENT.md             # Deployment guide
│   ├── K8S_IMPLEMENTATION_SUMMARY.md # Sumário implementação
│   ├── K8S_PRESENTATION.md           # Apresentação
│   └── K8S_QUICK_REFERENCE.md        # Referência rápida
│
├── adr/                               # 📋 Architecture Decision Records
│   ├── 001-timescaledb.md
│   ├── 002-docker-compose.md
│   ├── 005-random-forest.md
│   └── README.md
│
└── archive/                           # 📦 Arquivos históricos
    ├── data_import_guide.md
    ├── db_maintenance.md
    ├── informer_experimento.md
    ├── LOG_ALTERACOES_IA.md
    ├── LOG_ALTERACOES_IA_ANTIGO.md
    ├── LOG_OPERACIONAL_AI.md
    ├── logging.md
    ├── observabilidade.md
    ├── structure.md
    └── README.md
```

---

## 🎯 Documentos por Categoria

### 🏛️ Arquitetura (1 documento)

| Documento | Descrição | Páginas |
|-----------|-----------|---------|
| **[Análise Completa do Projeto](architecture/ANALISE_COMPLETA_PROJETO.md)** | Análise arquitetural detalhada, stack tecnológico, fluxo de dados | 300+ |

**Use quando:** Entender a arquitetura geral do sistema.

---

### 🔧 Infraestrutura (20 documentos)

| Documento | Descrição | Status |
|-----------|-----------|--------|
| **[PgBouncer Report](infrastructure/RELATORIO_PGBOUNCER_TESTES.md)** | Fix DNS resolution, validação | ✅ |
| **[All Containers Running](infrastructure/ALL_CONTAINERS_RUNNING.md)** | Guia de todos os containers | ✅ |
| **[Containers Status](infrastructure/CONTAINERS_STATUS.md)** | Status dos containers | ✅ |
| **[Deployment Status](infrastructure/DEPLOYMENT_STATUS.md)** | Status de deployment | ✅ |
| **[Deployment Final](infrastructure/DEPLOYMENT_STATUS_FINAL.md)** | Status final do deploy | ✅ |
| **[GitHub Actions Report](infrastructure/GITHUB_ACTIONS_REPORT.md)** | Relatório de CI/CD | ✅ |
| **[Network Optimization](infrastructure/NETWORK_OPTIMIZATION_GUIDE.md)** | Guia de otimização | ✅ |
| **[Network Summary](infrastructure/NETWORK_OPTIMIZATION_SUMMARY.md)** | Resumo de otimização | ✅ |
| **[Network Tools](infrastructure/NETWORK_TOOLS_README.md)** | Ferramentas de rede | ✅ |
| **[Terraform Dashboard](infrastructure/TERRAFORM_DASHBOARD_SUMMARY.md)** | Terraform + Grafana | ✅ |
| **[Auto-scaling](infrastructure/AUTOSCALING_AND_SNAPSHOTS.md)** | HPA e snapshots | ✅ |
| **[Connection Pooling](infrastructure/CONNECTION_POOLING.md)** | PgBouncer config | ✅ |
| **[Health Check System](infrastructure/HEALTH_CHECK_SYSTEM.md)** | Sistema de health check | ✅ |
| **[Infrastructure Improvements](infrastructure/INFRASTRUCTURE_IMPROVEMENTS.md)** | Melhorias | ✅ |
| **[Observability Quick Start](infrastructure/OBSERVABILITY_QUICKSTART.md)** | Quick start | ✅ |
| **[Observability Stack](infrastructure/OBSERVABILITY_STACK.md)** | Stack completa | ✅ |
| **[README Complete CI](infrastructure/README-complete-ci.md)** | CI/CD completo | ✅ |
| **[README Secure CI](infrastructure/README-secure-ci.md)** | CI/CD seguro | ✅ |
| **[Self-Hosted Runner](infrastructure/SETUP_SELF_HOSTED_RUNNER.md)** | Setup runner | ✅ |
| **[Auto Commit Setup](infrastructure/AUTO_COMMIT_SETUP.md)** | Setup auto-commit | ✅ |

**Use quando:** Configurar infraestrutura, deploy, monitoramento, CI/CD.

---

### 🧪 Testes (5 documentos)

| Documento | Descrição | Cobertura |
|-----------|-----------|-----------|
| **[Guia de Testes](testing/GUIA_TESTES.md)** | Como executar e criar testes | - |
| **[Relatório de Cobertura](testing/RELATORIO_COBERTURA_TESTES.md)** | Análise completa | 26% |
| **[Sprint Concluída](testing/SPRINT_TESTES_CONCLUIDA.md)** | Resumo da sprint | ✅ |
| **[Database Test Report](testing/DATABASE_TEST_REPORT.md)** | Testes de banco | ✅ |
| **[Snapshot Test Report](testing/SNAPSHOT_TEST_REPORT.md)** | Testes de snapshot | ✅ |

**Use quando:** Executar testes, aumentar cobertura, troubleshooting.

---

### 📖 Guias Práticos (3 documentos)

| Documento | Descrição | Para Quem |
|-----------|-----------|-----------|
| **[EA Integration Guide](guides/EA_INTEGRATION_GUIDE.md)** | Integração MT5 EA | Traders, Devs MT5 |
| **[EA Debug Guide](guides/EA_DEBUG_GUIDE.md)** | Debug do EA | Devs MT5 |
| **[EA Checklist](guides/EA_CHECKLIST.md)** | Checklist de verificação | Traders |

**Use quando:** Integrar Expert Advisor do MT5 com a API.

---

### 📚 Referência (9 documentos)

| Documento | Descrição | Idioma |
|-----------|-----------|--------|
| **[Documentation Complete](reference/DOCUMENTATION_COMPLETE.md)** | Documentação completa | EN |
| **[Documentação Completa](reference/DOCUMENTACAO_COMPLETA.md)** | Documentação completa | PT-BR |
| **[Project Structure](reference/PROJECT_STRUCTURE.md)** | Estrutura do projeto | EN |
| **[SQL Queries](reference/SQL_QUERIES.md)** | 21 queries úteis | EN |
| **[README Complete](reference/README_COMPLETE.md)** | README completo | EN |
| **[README Recovery](reference/README_RECOVERY.md)** | Recovery guide | EN |
| **[README Legacy](reference/README.legacy.md)** | README legado | EN |
| **[Warnings Fixed](reference/WARNINGS_FIXED.md)** | Avisos corrigidos | EN |
| **[Licenças](reference/DOCUMENTACAO_LICENCA_AUTOMACAO.md)** | Licenças e automação | PT-BR |

**Use quando:** Referência técnica, estrutura do código, queries SQL.

---

### ☸️ Kubernetes (4 documentos)

| Documento | Descrição | Páginas |
|-----------|-----------|---------|
| **[K8S Deployment](kubernetes/K8S_DEPLOYMENT.md)** | Guia completo de deployment | 400+ |
| **[K8S Quick Reference](kubernetes/K8S_QUICK_REFERENCE.md)** | Comandos rápidos | 200+ |
| **[K8S Implementation Summary](kubernetes/K8S_IMPLEMENTATION_SUMMARY.md)** | Sumário | 300+ |
| **[K8S Presentation](kubernetes/K8S_PRESENTATION.md)** | Apresentação | 350+ |

**Use quando:** Deploy em Kubernetes, troubleshooting K8S.

---

### 📋 Architecture Decision Records (4 documentos)

| ADR | Decisão | Status |
|-----|---------|--------|
| **[001](adr/001-timescaledb.md)** | Escolha do TimescaleDB | ✅ Aprovado |
| **[002](adr/002-docker-compose.md)** | Docker Compose | ✅ Aprovado |
| **[005](adr/005-random-forest.md)** | Random Forest ML | ✅ Aprovado |

**Use quando:** Entender decisões arquiteturais do projeto.

---

### 📦 Arquivo (9 documentos)

Documentos históricos e legados:

- `LOG_ALTERACOES_IA.md` - Log de alterações (IA)
- `LOG_ALTERACOES_IA_ANTIGO.md` - Log antigo
- `LOG_OPERACIONAL_AI.md` - Log operacional
- `data_import_guide.md` - Guia de importação
- `db_maintenance.md` - Manutenção do DB
- `informer_experimento.md` - Experimento Informer
- `logging.md` - Sistema de logs
- `observabilidade.md` - Observabilidade
- `structure.md` - Estrutura antiga

**Use quando:** Consultar histórico ou documentação legada.

---

### 📄 Documentos Gerais (15 documentos)

Localizados em `docs/`:

| Documento | Descrição |
|-----------|-----------|
| **RESUMO_EXECUTIVO_TESTES.md** | Resumo da sprint de testes |
| **CONTRIBUTING.md** | Como contribuir |
| **CONTRACTS.md** | Contratos e interfaces |
| **CHANGELOG_ML_TESTS.md** | Changelog de testes ML |
| **DIAGRAMS.md** | Diagramas do sistema |
| **DOCUMENTATION.md** | Meta-documentação |
| **EXAMPLES.md** | Exemplos práticos |
| **FAQ.md** | Perguntas frequentes |
| **GLOSSARY.md** | Glossário de termos |
| **HYBRID_INGESTION_FLOW.md** | Fluxo híbrido |
| **ONBOARDING.md** | Guia de onboarding |
| **PERFORMANCE.md** | Análise de performance |
| **RECONSTRUCTION_LOG.md** | Log de reconstrução |
| **RECOVERY_AND_ML_RUNBOOK.md** | Runbook recovery |
| **RUNBOOK.md** | Runbook operacional |

---

## 🔍 Encontrar Documentação por Tema

### "Preciso configurar o ambiente"

1. [README.md](../README.md) - Começe aqui
2. [ONBOARDING.md](ONBOARDING.md) - Guia de onboarding
3. [CONTRIBUTING.md](CONTRIBUTING.md) - Como contribuir

### "Quero fazer deploy"

1. **Docker Compose:** [README.md](../README.md)
2. **Kubernetes:** [K8S Deployment](kubernetes/K8S_DEPLOYMENT.md)
3. **Terraform:** [Terraform Dashboard](infrastructure/TERRAFORM_DASHBOARD_SUMMARY.md)

### "Preciso integrar com MT5"

1. [EA Integration Guide](guides/EA_INTEGRATION_GUIDE.md)
2. [EA Debug Guide](guides/EA_DEBUG_GUIDE.md)
3. [EA Checklist](guides/EA_CHECKLIST.md)

### "Quero executar testes"

1. [Guia de Testes](testing/GUIA_TESTES.md)
2. [Relatório de Cobertura](testing/RELATORIO_COBERTURA_TESTES.md)
3. [Sprint Concluída](testing/SPRINT_TESTES_CONCLUIDA.md)

### "Preciso resolver problemas"

1. [RUNBOOK.md](RUNBOOK.md) - Troubleshooting
2. [FAQ.md](FAQ.md) - Perguntas frequentes
3. [Warnings Fixed](reference/WARNINGS_FIXED.md)

### "Quero entender a arquitetura"

1. [Análise Completa](architecture/ANALISE_COMPLETA_PROJETO.md)
2. [Documentation Complete](reference/DOCUMENTATION_COMPLETE.md)
3. [Hybrid Ingestion Flow](HYBRID_INGESTION_FLOW.md)

### "Preciso configurar CI/CD"

1. [README Complete CI](infrastructure/README-complete-ci.md)
2. [README Secure CI](infrastructure/README-secure-ci.md)
3. [GitHub Actions Report](infrastructure/GITHUB_ACTIONS_REPORT.md)

### "Quero monitorar o sistema"

1. [Observability Stack](infrastructure/OBSERVABILITY_STACK.md)
2. [Observability Quick Start](infrastructure/OBSERVABILITY_QUICKSTART.md)
3. [Health Check System](infrastructure/HEALTH_CHECK_SYSTEM.md)

---

## 📊 Estatísticas

### Por Categoria

| Categoria | Documentos | Status |
|-----------|-----------|--------|
| **Infraestrutura** | 20 | ✅ 100% |
| **Referência** | 9 | ✅ 100% |
| **Arquivo** | 9 | 📦 Legado |
| **Testes** | 5 | ✅ 100% |
| **Kubernetes** | 4 | ✅ 100% |
| **ADR** | 4 | ✅ 100% |
| **Guias** | 3 | ✅ 100% |
| **Arquitetura** | 1 | ✅ 100% |
| **Gerais** | 15 | ✅ 100% |
| **Total** | **70** | **✅ Organizado** |

### Por Status

- ✅ **Ativo e Atualizado:** 55 documentos
- 📦 **Legado/Arquivo:** 9 documentos
- 🔄 **Em Desenvolvimento:** 6 documentos

### Linhas de Documentação

- **Total:** ~15,000+ linhas
- **Média:** ~200 linhas/documento
- **Maior:** K8S Deployment (400+ linhas)

---

## 🎯 Roadmap de Documentação

### Próximas Adições

1. ⏳ **API Reference Complete** - Swagger expandido
2. ⏳ **ML Pipeline Guide** - Guia completo de ML
3. ⏳ **Performance Tuning** - Otimizações avançadas
4. ⏳ **Backup & Recovery** - Guia completo
5. ⏳ **Security Hardening** - Hardening guide

### Melhorias Planejadas

1. 🔄 Adicionar diagramas em todos os guias principais
2. 🔄 Criar vídeos tutoriais
3. 🔄 Adicionar mais exemplos práticos
4. 🔄 Traduzir documentos principais para PT-BR
5. 🔄 Criar changelog unificado

---

## 🤝 Como Contribuir com Documentação

### Adicionando Nova Documentação

1. Criar arquivo na pasta apropriada:
   - `docs/architecture/` - Arquitetura
   - `docs/infrastructure/` - Infra/Deploy
   - `docs/testing/` - Testes
   - `docs/guides/` - Guias práticos
   - `docs/reference/` - Referência técnica

2. Usar template padrão:
```markdown
# Título do Documento

**Versão:** 1.0
**Data:** YYYY-MM-DD
**Status:** 🔄 Rascunho | ✅ Completo

## Visão Geral
...
```

3. Atualizar este índice

4. Fazer commit:
```bash
git add docs/
git commit -m "docs: adiciona [nome do documento]"
```

### Atualizando Documentação Existente

1. Editar arquivo
2. Atualizar data e versão
3. Adicionar entrada no CHANGELOG.md
4. Commit com prefixo `docs:`

---

## 📞 Suporte

- 📧 **Issues:** [GitHub Issues](https://github.com/ByteLair/MT5-Process-Core/issues)
- 💬 **Discussões:** [GitHub Discussions](https://github.com/ByteLair/MT5-Process-Core/discussions)
- 📚 **Documentação:** Este diretório

---

**Mantido por:** Equipe MT5 Process Core  
**Última Revisão:** 13 de Novembro de 2025  
**Versão do Índice:** 2.0
