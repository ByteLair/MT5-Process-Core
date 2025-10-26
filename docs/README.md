# 📚 MT5 Trading Platform - Documentação

Documentação completa da plataforma MT5 Trading Database com Machine Learning, Kubernetes e Monitoring.

---

## 📋 Índice Geral

### 🚀 [Quick Start](#quick-start)

### ☸️ [Kubernetes](#kubernetes)

### 🏗️ [Infraestrutura](#infraestrutura)

### 📖 [Guias](#guias)

### 📚 [Referência](#referência)

### 🔌 [API](#api)

---

## 🚀 Quick Start

Para começar rapidamente:

```bash
# 1. Clonar repositório
git clone https://github.com/Lysk-dot/mt5-trading-db.git
cd mt5-trading-db

# 2. Iniciar com Docker Compose
./quickstart.sh

# 3. Verificar saúde
./healthcheck.sh

# 4. Acessar serviços
# API: http://localhost:18001/docs
# Grafana: http://localhost:3000 (admin/admin)
```

**Mais detalhes**: Veja [README.md](../README.md)

---

## ☸️ Kubernetes

Documentação completa para deployment em Kubernetes.

### 📄 Documentos Principais

| Documento | Descrição | Páginas |
|-----------|-----------|---------|
| **[Deployment Guide](kubernetes/K8S_DEPLOYMENT.md)** | Guia completo de deployment | 400+ |
| **[Quick Reference](kubernetes/K8S_QUICK_REFERENCE.md)** | Comandos rápidos | 200+ |
| **[Implementation Summary](kubernetes/K8S_IMPLEMENTATION_SUMMARY.md)** | Sumário da implementação | 300+ |
| **[Presentation](kubernetes/K8S_PRESENTATION.md)** | Apresentação executiva | 350+ |

### 🎯 Por Onde Começar

**Iniciante?** → [K8S_DEPLOYMENT.md](kubernetes/K8S_DEPLOYMENT.md)
**Precisa de comandos rápidos?** → [K8S_QUICK_REFERENCE.md](kubernetes/K8S_QUICK_REFERENCE.md)
**Quer entender o que foi feito?** → [K8S_IMPLEMENTATION_SUMMARY.md](kubernetes/K8S_IMPLEMENTATION_SUMMARY.md)

### 📦 Recursos

- **11 Manifests** base (namespace, deployments, services, etc.)
- **3 Ambientes** configurados (dev, staging, production)
- **Helm Chart** v2.0.0 completo
- **5 Scripts** de automação
- **HPA** para auto-scaling
- **Ingress** NGINX + TLS

### 🚀 Deploy Rápido

```bash
# Development
./scripts/k8s-deploy.sh dev

# Production
./scripts/k8s-deploy.sh production

# Health check
./scripts/k8s-healthcheck.sh production
```

---

## 🏗️ Infraestrutura

Documentação sobre infraestrutura como código (IaC).

### 📄 Documentos

| Documento | Descrição |
|-----------|-----------|
| **[Terraform Dashboard Summary](infrastructure/TERRAFORM_DASHBOARD_SUMMARY.md)** | Guia Terraform + Grafana |

### 🔧 Componentes

#### Docker Compose

- Multi-container orchestration
- 9 serviços (db, api, ml, monitoring)
- Volumes persistentes
- Networks isolados

#### Terraform

- Infrastructure as Code
- Docker provider
- 5 containers gerenciados
- Variables e outputs

#### Grafana

- 10 painéis configurados
- Auto-provisioning
- Datasources: Prometheus + PostgreSQL
- 6 alertas configurados

### 📊 Monitoramento

```bash
# Acessar Grafana
http://localhost:3000 (admin/admin)

# Acessar Prometheus
http://localhost:9090

# Ver métricas da API
http://localhost:18001/prometheus
```

---

## 📖 Guias

Guias práticos e tutoriais passo-a-passo.

### 📄 Documentos

| Guia | Descrição | Para Quem |
|------|-----------|-----------|
| **[EA Integration Guide](guides/EA_INTEGRATION_GUIDE.md)** | Integração Expert Advisor MT5 | Traders, Devs MT5 |

### 🎯 Conteúdo

#### EA Integration Guide

- Configuração do Expert Advisor
- Código MQL5 completo
- Endpoints da API
- Exemplos de requisições
- Troubleshooting
- Ambiente Windows

### 💡 Uso

```mql5
// Exemplo de código MQL5
bool SendCandleToAPI(string symbol, ENUM_TIMEFRAMES timeframe) {
   // Código completo no guia
}
```

---

## 📚 Referência

Documentação de referência técnica.

### 📄 Documentos

| Documento | Descrição | Uso |
|-----------|-----------|-----|
| **[SQL Queries](reference/SQL_QUERIES.md)** | 21 queries úteis | Análise de dados |
| **[Project Structure](reference/PROJECT_STRUCTURE.md)** | Estrutura completa | Overview do projeto |

### 🗂️ SQL Queries

Categorias de queries disponíveis:

1. **Estatísticas Gerais** (5 queries)
   - Total de registros
   - Símbolos ativos
   - Timeframes
   - Range de datas

2. **Análise por Símbolo** (4 queries)
   - Dados por símbolo
   - Volume total
   - Estatísticas por timeframe

3. **Dados Recentes** (3 queries)
   - Últimos registros
   - Dados do dia
   - Última semana

4. **Qualidade de Dados** (3 queries)
   - Gaps temporais
   - Duplicatas
   - Volume zero

5. **Performance** (3 queries)
   - Volatilidade
   - Comparação de preços
   - Padrões

6. **Manutenção** (3 queries)
   - Tamanho de tabelas
   - Índices
   - Vacuum status

### 🏗️ Project Structure

Visão completa da estrutura:

- Arquivos e diretórios
- Componentes
- Estatísticas
- Deployment options
- Roadmap

---

## 🔌 API

Documentação da API REST.

### 📊 Endpoints Principais

#### POST /ingest

Ingerir candles do MT5 (single ou batch)

```bash
curl -X POST "http://localhost:18001/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod" \
  -d '{
    "ts":"2025-10-18T14:00:00Z",
    "symbol":"EURUSD",
    "timeframe":"M1",
    "open":1.0950,
    "high":1.0955,
    "low":1.0948,
    "close":1.0952,
    "volume":1250
  }'
```

#### GET /metrics

Estatísticas por símbolo

```bash
curl http://localhost:18001/metrics
```

#### GET /signals/next

Obter próximo sinal de trading

```bash
curl "http://localhost:18001/signals/next?symbols=EURUSD,GBPUSD" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"
```

#### GET /predict

Predição ML para símbolo

```bash
curl "http://localhost:18001/predict?symbol=EURUSD&timeframe=M1" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"
```

### 📝 Documentação Interativa

Acesse: <http://localhost:18001/docs>

- Swagger UI completo
- Testes interativos
- Schemas de dados
- Exemplos de uso

---

## 🔗 Links Rápidos

### Documentação Externa

- [Kubernetes](../k8s/)
- [Helm Chart](../helm/mt5-trading/)
- [Terraform](../terraform/)
- [Scripts](../scripts/)

### Arquivos Principais

- [README.md](../README.md) - Documentação principal
- [CHANGELOG.md](../CHANGELOG.md) - Histórico de versões
- [README.legacy.md](../README.legacy.md) - Documentação anterior

---

## 📖 Navegação por Cenário

### "Quero fazer deploy em Kubernetes"

1. [K8S Deployment Guide](kubernetes/K8S_DEPLOYMENT.md)
2. [K8S Quick Reference](kubernetes/K8S_QUICK_REFERENCE.md)
3. Executar: `./scripts/k8s-deploy.sh dev`

### "Preciso integrar com MT5"

1. [EA Integration Guide](guides/EA_INTEGRATION_GUIDE.md)
2. Copiar código MQL5
3. Configurar endpoints

### "Quero analisar os dados"

1. [SQL Queries](reference/SQL_QUERIES.md)
2. Conectar: `psql -h localhost -U trader -d mt5_trading`
3. Executar queries

### "Preciso entender a infraestrutura"

1. [Project Structure](reference/PROJECT_STRUCTURE.md)
2. [Terraform Summary](infrastructure/TERRAFORM_DASHBOARD_SUMMARY.md)
3. Ver [README.md](../README.md)

### "Quero monitorar o sistema"

1. Grafana: <http://localhost:3000>
2. Prometheus: <http://localhost:9090>
3. [Terraform Summary](infrastructure/TERRAFORM_DASHBOARD_SUMMARY.md)

---

## 🎯 Índice por Nível

### 👶 Iniciante

- [README.md](../README.md) - Comece aqui!
- [EA Integration Guide](guides/EA_INTEGRATION_GUIDE.md)
- [Quick Start](#quick-start)

### 👨‍💻 Intermediário

- [K8S Deployment Guide](kubernetes/K8S_DEPLOYMENT.md)
- [SQL Queries](reference/SQL_QUERIES.md)
- [Terraform Summary](infrastructure/TERRAFORM_DASHBOARD_SUMMARY.md)

### 🚀 Avançado

- [K8S Implementation Summary](kubernetes/K8S_IMPLEMENTATION_SUMMARY.md)
- [Project Structure](reference/PROJECT_STRUCTURE.md)
- [K8S Presentation](kubernetes/K8S_PRESENTATION.md)

### 🔧 DevOps

- [K8S Quick Reference](kubernetes/K8S_QUICK_REFERENCE.md)
- Scripts: `/scripts/k8s-*.sh`
- Helm Chart: `/helm/mt5-trading/`

---

## 📊 Estatísticas da Documentação

| Categoria | Documentos | Linhas | Status |
|-----------|-----------|--------|--------|
| **Kubernetes** | 4 | 1,250+ | ✅ Completo |
| **Infraestrutura** | 1 | 150+ | ✅ Completo |
| **Guias** | 1 | 250+ | ✅ Completo |
| **Referência** | 2 | 450+ | ✅ Completo |
| **API** | - | - | 📝 Swagger UI |
| **Total** | **8** | **2,100+** | ✅ |

---

## 🤝 Contribuindo

Para contribuir com a documentação:

1. Fork o repositório
2. Crie uma branch (`git checkout -b docs/melhoria`)
3. Faça suas alterações
4. Teste os links
5. Commit (`git commit -m 'docs: adiciona seção X'`)
6. Push (`git push origin docs/melhoria`)
7. Abra um Pull Request

### Padrões

- Use Markdown
- Inclua exemplos práticos
- Adicione links entre documentos
- Mantenha índices atualizados
- Screenshots quando necessário

---

## 📞 Suporte

- 📧 **Issues**: [GitHub Issues](https://github.com/Lysk-dot/mt5-trading-db/issues)
- 📚 **Docs**: Este diretório
- 💬 **Discussões**: [GitHub Discussions](https://github.com/Lysk-dot/mt5-trading-db/discussions)

---

## 📜 Licença

MIT License - Veja [LICENSE](../LICENSE)

---

**Versão da Documentação**: 2.0.0
**Última Atualização**: 18 de Outubro de 2025
**Mantido por**: Felipe

---

## 🗺️ Mapa da Documentação

```
docs/
├── README.md                    # 👈 Você está aqui
│
├── kubernetes/                  # ☸️ Kubernetes
│   ├── K8S_DEPLOYMENT.md       # Guia completo
│   ├── K8S_QUICK_REFERENCE.md  # Comandos rápidos
│   ├── K8S_IMPLEMENTATION_SUMMARY.md
│   └── K8S_PRESENTATION.md     # Apresentação
│
├── infrastructure/              # 🏗️ Infraestrutura
│   └── TERRAFORM_DASHBOARD_SUMMARY.md
│
├── guides/                      # 📖 Guias práticos
│   └── EA_INTEGRATION_GUIDE.md # Integração MT5
│
├── reference/                   # 📚 Referência
│   ├── SQL_QUERIES.md          # Queries úteis
│   └── PROJECT_STRUCTURE.md    # Estrutura completa
│
└── api/                         # 🔌 API (Swagger UI)
    └── (documentação interativa em /docs)
```

---

**🚀 Happy Coding! ☸️**
