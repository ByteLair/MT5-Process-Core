# 🚀 MT5 Trading DB - Complete Trading Infrastructure

> Sistema completo de coleta, análise e predição de dados de mercado MT5 com Machine Learning, monitoramento e infraestrutura como código.

[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-purple)](https://www.terraform.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboard-orange)](https://grafana.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Modern-green)](https://fastapi.tiangolo.com/)

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Arquitetura](#-arquitetura)
- [Quick Start](#-quick-start)
- [Componentes](#-componentes)
- [Documentação](#-documentação)
- [Monitoramento](#-monitoramento)
- [Machine Learning](#-machine-learning)
- [API Reference](#-api-reference)
- [Manutenção](#-manutenção)

---

## 🎯 Visão Geral

Sistema completo para trading algorítmico com:

✅ **Coleta de Dados** - Ingestão em tempo real de candles do MT5  
✅ **Armazenamento** - TimescaleDB otimizado para séries temporais  
✅ **Machine Learning** - Modelos preditivos (RandomForest, Informer)  
✅ **API REST** - FastAPI com autenticação e rate limiting  
✅ **Monitoramento** - Prometheus + Grafana com 10 dashboards  
✅ **Infraestrutura** - Terraform para provisionamento automatizado  
✅ **Alertas** - Notificações automáticas de problemas  

---

## 🏗️ Arquitetura

```
┌─────────────┐
│   MT5 EA    │  ← Coleta dados do MetaTrader 5
└──────┬──────┘
       │ HTTP POST (JSON)
       ↓
┌─────────────────────────────────────────┐
│           FastAPI Backend               │
│  • Autenticação (API Key)               │
│  • Rate Limiting                        │
│  • Métricas Prometheus                  │
│  • Validação de Dados                   │
└──────┬──────────────────────┬───────────┘
       │                      │
       ↓                      ↓
┌──────────────┐      ┌─────────────┐
│ TimescaleDB  │      │ Prometheus  │
│ (PostgreSQL) │      │  Metrics    │
└──────┬───────┘      └──────┬──────┘
       │                     │
       ↓                     ↓
┌──────────────┐      ┌─────────────┐
│  ML Models   │      │   Grafana   │
│  Training    │      │  Dashboard  │
└──────────────┘      └─────────────┘
```

---

## ⚡ Quick Start

### 1. Clonar e Configurar

```bash
git clone https://github.com/Lysk-dot/mt5-trading-db.git
cd mt5-trading-db
cp .env.example .env
# Edite .env com suas configurações
```

### 2. Iniciar Serviços

```bash
# Opção 1: Script rápido
./quickstart.sh

# Opção 2: Docker Compose
docker compose up -d

# Opção 3: Terraform (nova infraestrutura)
cd terraform
terraform init
terraform apply
```

### 3. Verificar Status

```bash
./healthcheck.sh
```

### 4. Acessar Serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **API** | http://localhost:18001 | API Key header |
| **API Docs** | http://localhost:18001/docs | - |
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **pgAdmin** | http://localhost:5051 | - |

---

## 🧩 Componentes

### 1. Database (TimescaleDB)
- **Porta**: 5432 (interna)
- **Usuário**: trader
- **Database**: mt5_trading
- **Features**: Hypertables, continuous aggregates
- **Backups**: Automáticos via `./backup.sh`

### 2. API (FastAPI)
- **Porta**: 18001
- **Endpoints**: `/ingest`, `/metrics`, `/signals/*`, `/predict`
- **Auth**: X-API-Key header
- **Docs**: Swagger UI em `/docs`
- **Métricas**: Prometheus em `/prometheus`

### 3. Machine Learning
- **Modelos**: RandomForest, Informer (Transformer)
- **Features**: 18+ indicadores técnicos
- **Training**: Automatizado via scheduler
- **Storage**: Volume `models_mt5`

### 4. Monitoramento
- **Prometheus**: Coleta de métricas a cada 5s
- **Grafana**: 10 dashboards pré-configurados
- **Alertas**: 6 regras de alerta configuradas
- **Métricas**: Latência, taxa de erros, inserções, duplicatas

---

## 📚 Documentação

### Guias Completos

| Documento | Descrição |
|-----------|-----------|
| [EA Integration Guide](docs/EA_INTEGRATION_GUIDE.md) | Integração do Expert Advisor MT5 |
| [Terraform Guide](terraform/README.md) | Infraestrutura como código |
| [SQL Queries](docs/SQL_QUERIES.md) | 21 queries úteis para análise |
| [Dashboard Summary](docs/TERRAFORM_DASHBOARD_SUMMARY.md) | Guia do Grafana |

### Scripts Úteis

```bash
# Inicialização rápida
./quickstart.sh

# Health check completo
./healthcheck.sh

# Backup automático
./backup.sh

# Monitorar logs
docker compose logs -f api
```

---

## 📊 Monitoramento

### Dashboard Grafana

Acesse: http://localhost:3000 (admin/admin)

**10 Painéis Disponíveis:**
1. Total Candles Inserted
2. API Status (UP/DOWN)
3. Total Records in DB
4. Active Symbols
5. Candle Ingestion Rate (per second)
6. Records per Minute
7. Last Data Received (Top 20)
8. Data Distribution by Symbol
9. Price Chart (Major Pairs)
10. Latest Market Data (Last 50)

### Métricas Prometheus

```bash
# Ver todas as métricas
curl http://localhost:18001/prometheus/

# Taxa de inserção
curl -s http://localhost:9090/api/v1/query?query=rate(ingest_candles_inserted_total[5m])

# Latência P95
curl -s http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,rate(ingest_latency_seconds_bucket[5m]))
```

### Alertas Configurados

1. **API Down** - API indisponível > 1 min (Critical)
2. **High Latency** - P95 > 1s por 5 min (Warning)
3. **High Error Rate** - Erros > 5% por 5 min (Warning)
4. **No Data Received** - Sem inserções por 5 min (Warning)
5. **Database Issues** - Problemas de conexão (Critical)
6. **High Duplicate Rate** - > 50% duplicatas (Warning)

---

## 🤖 Machine Learning

### Modelos Disponíveis

#### 1. RandomForest Regressor
- **Features**: 18 indicadores técnicos
- **Target**: Retorno futuro (1, 5, 10 períodos)
- **Métricas**: R², MAE
- **Storage**: `models/random_forest.pkl`

#### 2. Informer (Transformer)
- **Task**: Classificação binária (trade positivo)
- **Seq Length**: 32-64 candles
- **Métricas**: Precision, Recall, AUC-ROC
- **Configs**: Simple, Advanced, GridSearch
- **Storage**: `models/informer_*.pt`

### Treinamento

```bash
# Preparar dataset
docker compose run --rm ml-trainer python prepare_dataset.py

# Treinar RandomForest
docker compose run --rm ml-trainer python train_model.py

# Treinar Informer
docker compose run --rm ml-trainer python train_informer.py
```

### Verificar Performance

```bash
# Ver relatórios
cat ml/models/last_train_report.json
cat ml/models/informer_report.json

# Avaliar thresholds
docker compose run --rm ml-trainer python eval_threshold.py
```

---

## 🔌 API Reference

### Authentication

Todas as requisições requerem header:
```
X-API-Key: mt5_trading_secure_key_2025_prod
```

### Endpoints

#### POST /ingest
Enviar candles individuais ou em batch.

**Single Candle:**
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

**Batch:**
```bash
curl -X POST "http://localhost:18001/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod" \
  -d '{
    "items": [
      {"ts":"2025-10-18T14:00:00Z","symbol":"EURUSD","timeframe":"M1",...},
      {"ts":"2025-10-18T14:01:00Z","symbol":"EURUSD","timeframe":"M1",...}
    ]
  }'
```

#### GET /metrics
Estatísticas de dados por símbolo.

```bash
curl http://localhost:18001/metrics
```

#### GET /signals/next
Obter próximo sinal de trading.

```bash
curl "http://localhost:18001/signals/next?account_id=123&symbols=EURUSD,GBPUSD&timeframe=M1" \
  -H "X-API-Key: mt5_trading_secure_key_2025_prod"
```

#### GET /health
Health check da API.

```bash
curl http://localhost:18001/health
```

### Timeframes Válidos
`M1`, `M5`, `M15`, `M30`, `H1`, `H4`, `D1`

---

## 🛠️ Manutenção

### Backup

```bash
# Backup manual
./backup.sh

# Backup agendado (crontab)
0 2 * * * /path/to/mt5-trading-db/backup.sh

# Com retenção personalizada
RETENTION_DAYS=30 ./backup.sh
```

**O que é incluído no backup:**
- Dump completo do PostgreSQL
- Modelos ML treinados
- Configurações (docker-compose, .env, Grafana)
- Metadata com estatísticas

### Restore

```bash
# Extrair backup
tar -xzf backups/mt5_backup_YYYYMMDD_HHMMSS.tar.gz

# Restaurar banco
docker exec -i mt5_db psql -U trader -d mt5_trading < mt5_backup_*/database.sql

# Restaurar modelos
docker cp mt5_backup_*/models/. mt5_ml_trainer:/models/

# Restaurar configs
cp -r mt5_backup_*/config/* ./
```

### Logs

```bash
# API logs
docker compose logs -f api

# Banco de dados
docker compose logs -f db

# Todos os serviços
docker compose logs -f

# Últimas 100 linhas
docker compose logs --tail=100 api
```

### Limpeza

```bash
# Parar todos os serviços
docker compose down

# Remover volumes (CUIDADO: apaga dados!)
docker compose down -v

# Remover imagens
docker compose down --rmi all

# Limpar sistema Docker
docker system prune -a
```

### Performance Tuning

```sql
-- Vacuum e análise
VACUUM ANALYZE market_data;

-- Reindex
REINDEX TABLE market_data;

-- Ver tamanho das tabelas
SELECT pg_size_pretty(pg_total_relation_size('market_data'));
```

---

## 🔧 Troubleshooting

### Problema: API retorna 401 Unauthorized
**Solução**: Verifique se o header `X-API-Key` está correto no `.env` e no EA.

### Problema: Container não inicia
**Solução**: 
```bash
docker compose logs [service_name]
docker compose down && docker compose up -d
```

### Problema: Dashboard Grafana não carrega
**Solução**:
```bash
docker compose restart grafana
# Verificar: http://localhost:3000/d/mt5-trading-main
```

### Problema: Banco de dados lento
**Solução**:
```sql
-- Vacuum full (offline)
VACUUM FULL market_data;

-- Aumentar memória no docker-compose.yml
mem_limit: 4g
```

### Problema: Modelos ML não treinam
**Solução**:
```bash
# Verificar dataset
docker compose exec db psql -U trader -d mt5_trading -c "SELECT COUNT(*) FROM market_data;"

# Reexecutar preparação
docker compose run --rm ml-trainer python prepare_dataset.py
```

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

---

## 📝 Changelog

### v2.0.0 (2025-10-18)
- ✅ Adicionado Terraform para IaC
- ✅ Dashboard Grafana completo (10 painéis)
- ✅ 5 novas métricas Prometheus
- ✅ 6 alertas configurados
- ✅ Scripts de healthcheck e backup
- ✅ Documentação completa
- ✅ 21 queries SQL úteis

### v1.0.0 (2021-10-18)
- ✅ Sistema básico de ingestão
- ✅ TimescaleDB implementation
- ✅ RandomForest ML model
- ✅ FastAPI backend

---

## 📄 License

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

---

## 👥 Autores

- **Felipe** - *Desenvolvimento Inicial* - [Lysk-dot](https://github.com/Lysk-dot)

---

## 🙏 Agradecimentos

- TimescaleDB team
- FastAPI community
- Grafana Labs
- MetaTrader 5

---

**⭐ Se este projeto foi útil, considere dar uma estrela!**
