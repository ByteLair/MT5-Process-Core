# 📊 MT5 Trading Database - Sistema Completo de Ingestão e Análise

> Sistema híbrido de alta performance para coleta, processamento e análise de dados de trading do MetaTrader 5, com suporte a machine learning e indicadores técnicos server-side.

[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![TimescaleDB](https://img.shields.io/badge/TimescaleDB-2.14-orange.svg)](https://www.timescale.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)

## 🎯 Características Principais

### 1. Ingestão Híbrida de Dados

- **Candles diretos**: M1/M5/M15/M30/H1/H4/D1 via `POST /ingest_batch`
- **Ticks em tempo real**: Alta fluidez de mercado via `POST /ingest/tick`
- **Agregação automática**: Ticks → Candles M1 a cada 5 segundos
- **Deduplicação inteligente**: Por janela de tempo (timeframe bucket)

### 2. Processamento Server-Side

- **Indicadores técnicos**: RSI, MACD, ATR, Bollinger Bands (cálculo consistente)
- **Continuous Aggregates**: TimescaleDB gera M5/M15/H1/D1 automaticamente
- **Workers assíncronos**: Agregação e cálculo paralelo
- **State tracking**: Processamento incremental sem reprocessamento

### 3. Machine Learning Pipeline

- **Feature engineering**: Extração automática de features
- **Modelo treinado**: Random Forest / LightGBM
- **Inferência em tempo real**: Endpoint `/predict`
- **Backtesting**: Framework completo de validação

### 4. Observabilidade Completa

- **Métricas Prometheus**: Latência, throughput, duplicados
- **Logs estruturados**: JSON com contexto completo
- **Tracing distribuído**: Jaeger OpenTelemetry
- **Dashboards Grafana**: Visualização em tempo real

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        Expert Advisor (MT5)                      │
└────────┬────────────────────────────────────────────┬───────────┘
         │ POST /ingest_batch                         │ POST /ingest/tick
         │ (candles M1 diretos)                       │ (ticks alta fluidez)
         v                                            v
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                          │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────┐  │
│  │ /ingest      │  │ /ingest_batch │  │ /ingest/tick       │  │
│  │ (flexible)   │  │ (array puro)  │  │ (raw ticks)        │  │
│  └──────┬───────┘  └───────┬───────┘  └─────────┬──────────┘  │
└─────────┼──────────────────┼────────────────────┼─────────────┘
          │                  │                    │
          v                  v                    v
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL + TimescaleDB                      │
│  ┌──────────────────────┐         ┌──────────────────────────┐ │
│  │   market_data        │         │   market_data_raw        │ │
│  │   (hypertable)       │         │   (JSONB ticks)          │ │
│  │   - M1 candles       │         │   - Raw tick data        │ │
│  │   - Indicadores      │         └─────────┬────────────────┘ │
│  └──────────┬───────────┘                   │                  │
│             │                               │                  │
│             │      ┌────────────────────────┘                  │
│             │      │                                            │
└─────────────┼──────┼────────────────────────────────────────────┘
              │      │
              │      v
              │  ┌─────────────────────────────┐
              │  │  Tick Aggregator Worker     │
              │  │  - A cada 5s                │
              │  │  - Agrega ticks → M1        │
              │  │  - OHLCV + spread           │
              │  └─────────────┬───────────────┘
              │                │
              │                v
              │  ┌─────────────────────────────┐
              │  │  Indicators Worker          │
              │  │  - A cada 60s               │
              │  │  - RSI/MACD/ATR/BB          │
              │  │  - Consistência treino/prod │
              │  └─────────────┬───────────────┘
              │                │
              v                v
    ┌──────────────────────────────────────────┐
    │  Continuous Aggregates (TimescaleDB)     │
    │  ┌─────┐ ┌──────┐ ┌─────┐ ┌──────┐      │
    │  │ M5  │ │ M15  │ │ H1  │ │ D1   │      │
    │  └─────┘ └──────┘ └─────┘ └──────┘      │
    │  (refresh automático incremental)        │
    └──────────────────────────────────────────┘
```

## 🚀 Quick Start

### Pré-requisitos

- Docker & Docker Compose
- 4GB RAM mínimo (8GB recomendado)
- 20GB espaço em disco

### 1. Clone e Configure

```bash
git clone https://github.com/Lysk-dot/mt5-trading-db.git
cd mt5-trading-db

# Copiar e configurar variáveis de ambiente
cp env.template .env
nano .env  # Ajuste credenciais e parâmetros
```

### 2. Criar Volumes

```bash
docker volume create models_mt5
```

### 3. Subir Infraestrutura

```bash
# Subir tudo
docker-compose up -d

# Verificar status
docker-compose ps

# Aguardar todos ficarem healthy
watch docker-compose ps
```

### 4. Inicializar Continuous Aggregates (primeira vez)

```bash
docker-compose exec db psql -U trader -d mt5_trading \
  -f /docker-entrypoint-initdb.d/04-continuous-aggregates.sql
```

### 5. Testar Fluxo Completo

```bash
./test_hybrid_flow.sh
```

### 6. Acessar Interfaces

- **API Docs**: <http://localhost:18003/docs>
- **Grafana**: <http://localhost:3000> (admin/admin)
- **Prometheus**: <http://localhost:19090>
- **Jaeger**: <http://localhost:16686>
- **PgAdmin**: <http://localhost:5050>

## 📡 API Endpoints

### Ingestão de Dados

#### POST `/ingest_batch` - Candles M1 Diretos (Recomendado)

Envia array puro de candles. **Caminho mais rápido**.

```bash
curl -X POST http://localhost:18003/ingest_batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: supersecretkey" \
  -d '[
    {
      "ts": "2025-10-20T10:00:00Z",
      "symbol": "EURUSD",
      "timeframe": "M1",
      "open": 1.1000,
      "high": 1.1015,
      "low": 1.0995,
      "close": 1.1010,
      "volume": 150,
      "bid": 1.1009,
      "ask": 1.1011,
      "spread": 0.0002
    }
  ]'
```

**Resposta:**

```json
{
  "ok": true,
  "inserted": 1,
  "received": 1,
  "duplicates": 0,
  "details": [
    {
      "symbol": "EURUSD",
      "timeframe": "M1",
      "ts_original": "2025-10-20T10:00:00Z",
      "ts_bucket": "2025-10-20T10:00:00+00:00",
      "status": "inserted"
    }
  ]
}
```

#### POST `/ingest/tick` - Ticks Alta Fluidez

Para mercados muito voláteis. Ticks são agregados automaticamente.

```bash
curl -X POST http://localhost:18003/ingest/tick \
  -H "Content-Type: application/json" \
  -H "X-API-Key: supersecretkey" \
  -d '{
    "ticks": [
      {
        "ts": "2025-10-20T10:00:00.123Z",
        "symbol": "GBPUSD",
        "bid": 1.2750,
        "ask": 1.2752,
        "spread": 0.0002,
        "volume": 1
      }
    ]
  }'
```

#### POST `/ingest` - Flexível

Aceita candle único ou `{"items": [...]}`.

### Predição e Sinais

#### GET `/predict?symbol=EURUSD&limit=30`

Retorna probabilidade de alta com base nos últimos N candles.

```json
{
  "symbol": "EURUSD",
  "n": 30,
  "prob_up_latest": 0.68,
  "ts_latest": "2025-10-20T10:00:00Z"
}
```

#### GET `/signals/latest?symbol=EURUSD&period=M1`

Gera sinal de trading baseado no modelo.

### Métricas

#### GET `/prometheus`

Métricas Prometheus para scraping.

#### GET `/metrics`

Métricas atuais em JSON.

## 🗂️ Estrutura de Dados

### Tabela `market_data` (Hypertable TimescaleDB)

```sql
CREATE TABLE market_data (
  ts timestamptz NOT NULL,
  symbol text NOT NULL,
  timeframe text NOT NULL,
  open double precision,
  high double precision,
  low double precision,
  close double precision,
  volume double precision,
  spread double precision,
  bid double precision,
  ask double precision,
  -- Indicadores técnicos
  rsi double precision,
  macd double precision,
  macd_signal double precision,
  macd_hist double precision,
  atr double precision,
  bb_upper double precision,
  bb_middle double precision,
  bb_lower double precision,
  PRIMARY KEY (symbol, timeframe, ts)
);
```

**Chave primária**: `(symbol, timeframe, ts_bucket)`

- Garante 1 candle por janela de tempo
- Normalização de ts antes de inserir

### Tabela `market_data_raw` (Ticks brutos)

```sql
CREATE TABLE market_data_raw (
  received_at timestamptz NOT NULL DEFAULT now(),
  source text NOT NULL,
  payload jsonb NOT NULL
);
```

Armazena ticks em JSONB para processamento posterior.

### Views Materializadas (Continuous Aggregates)

- `market_data_m5`: Agregação de 5 minutos
- `market_data_m15`: Agregação de 15 minutos
- `market_data_m30`: Agregação de 30 minutos
- `market_data_h1`: Agregação de 1 hora
- `market_data_h4`: Agregação de 4 horas
- `market_data_d1`: Agregação diária

**Refresh automático** gerenciado pelo TimescaleDB.

## ⚙️ Configuração

### Variáveis de Ambiente (.env)

```bash
# Database
POSTGRES_USER=trader
POSTGRES_PASSWORD=trader123
POSTGRES_DB=mt5_trading

# API
API_KEY=supersecretkey
DATABASE_URL=postgresql+psycopg://trader:trader123@pgbouncer:5432/mt5_trading

# Workers
TICK_AGG_INTERVAL=5        # Agregação de ticks (segundos)
INDICATORS_INTERVAL=60     # Cálculo de indicadores (segundos)
SYMBOLS=EURUSD,GBPUSD,USDJPY,GOLD

# ML
MODELS_DIR=./models
```

### Parâmetros dos Indicadores

Configurados em `api/app/indicators_worker.py`:

- **RSI**: 14 períodos
- **MACD**: 12/26/9
- **ATR**: 14 períodos
- **Bollinger Bands**: 20 períodos, 2 desvios padrão

## 🔧 Operação

### Monitoramento

```bash
# Status dos serviços
docker-compose ps

# Logs em tempo real
docker-compose logs -f api tick-aggregator indicators-worker

# Logs de um serviço específico
docker-compose logs -f tick-aggregator

# Métricas do sistema
docker stats
```

### Verificação de Dados

```bash
# Conectar ao banco
docker-compose exec db psql -U trader -d mt5_trading

# Verificar candles por símbolo/timeframe
SELECT symbol, timeframe, COUNT(*) as candles,
       MIN(ts) as first, MAX(ts) as last
FROM market_data
GROUP BY symbol, timeframe
ORDER BY symbol, timeframe;

# Verificar ticks brutos
SELECT source, COUNT(*) as records,
       MIN(received_at) as first, MAX(received_at) as last
FROM market_data_raw
GROUP BY source;

# Verificar estado do aggregator
SELECT * FROM aggregator_state;

# Verificar continuous aggregates
SELECT * FROM market_data_m5
WHERE symbol = 'EURUSD'
ORDER BY ts DESC LIMIT 10;
```

### Manutenção

#### Limpeza de Ticks Antigos

```sql
-- Remover ticks já processados (>7 dias)
DELETE FROM market_data_raw
WHERE received_at < NOW() - INTERVAL '7 days';
```

#### Refresh Manual de Views

```sql
CALL refresh_continuous_aggregate('market_data_m5', NULL, NULL);
CALL refresh_continuous_aggregate('market_data_h1', NULL, NULL);
```

#### Reindexação

```sql
REINDEX TABLE market_data;
```

### Backup e Restore

```bash
# Backup completo
docker-compose exec db pg_dump -U trader mt5_trading > backup_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T db psql -U trader -d mt5_trading < backup_20251020.sql

# Backup apenas dados (sem schema)
docker-compose exec db pg_dump -U trader --data-only mt5_trading > data_backup.sql
```

## 🧪 Testes

### Teste Unitário de Endpoints

```bash
# Rodar script de teste
./test_hybrid_flow.sh

# Testar endpoint específico
curl -s http://localhost:18003/health | jq .
```

### Teste de Carga

```bash
# Instalar wrk
sudo apt install wrk

# Testar ingestão
wrk -t4 -c100 -d30s --latency \
  -H "X-API-Key: supersecretkey" \
  -s load_test.lua \
  http://localhost:18003/ingest_batch
```

### Validação de Indicadores

```bash
# Conectar e verificar
docker-compose exec db psql -U trader -d mt5_trading -c "
  SELECT symbol, COUNT(*) as total,
         COUNT(rsi) as with_rsi,
         COUNT(macd) as with_macd
  FROM market_data
  WHERE timeframe = 'M1'
  GROUP BY symbol;
"
```

## 📊 Machine Learning

### Pipeline de Treino

```bash
# Preparar dataset
docker-compose exec ml-trainer python prepare_dataset.py

# Treinar modelo
docker-compose exec ml-trainer python train_model.py

# Avaliar modelo
docker-compose exec ml-trainer python eval_threshold.py
```

### Feature Engineering

Features automáticas extraídas:

- Preços OHLC
- Volume
- Spread
- Indicadores técnicos (RSI, MACD, ATR, BB)
- Returns defasados (lag 1-5)
- Moving averages (20, 60, 200)

### Uso do Modelo

```python
import requests

response = requests.get(
    "http://localhost:18003/predict",
    params={"symbol": "EURUSD", "limit": 30}
)

prob = response.json()["prob_up_latest"]
if prob > 0.6:
    print("📈 Sinal de COMPRA")
elif prob < 0.4:
    print("📉 Sinal de VENDA")
else:
    print("⏸️ Neutro")
```

## 🔍 Troubleshooting

### Containers não iniciam

```bash
# Ver logs de erro
docker-compose logs db

# Recriar sem cache
docker-compose down -v
docker-compose up -d --build --force-recreate
```

### API retorna 404 nos novos endpoints

```bash
# Verificar se código foi copiado
docker exec mt5_api ls -la /app/app/ | grep ingest

# Rebuild forçado
docker-compose build --no-cache api
docker-compose up -d --force-recreate api
```

### Workers não processam dados

```bash
# Verificar logs
docker-compose logs tick-aggregator indicators-worker

# Verificar health
docker-compose ps | grep -E "tick|indicator"

# Restart
docker-compose restart tick-aggregator indicators-worker
```

### Continuous aggregates desatualizadas

```sql
-- Ver políticas
SELECT * FROM timescaledb_information.jobs
WHERE proc_name LIKE '%continuous%';

-- Forçar refresh
CALL refresh_continuous_aggregate('market_data_m5', NULL, NULL);
```

### Performance lenta

```bash
# Ver queries lentas
docker-compose exec db psql -U trader -d mt5_trading -c "
  SELECT query, calls, mean_exec_time, max_exec_time
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"

# Analisar locks
docker-compose exec db psql -U trader -d mt5_trading -c "
  SELECT * FROM pg_locks WHERE NOT granted;
"
```

## 📚 Documentação Adicional

- [Fluxo Híbrido de Ingestão](docs/HYBRID_INGESTION_FLOW.md) - Detalhes técnicos completos
- [API Reference](docs/api/README.md) - Especificação de todos os endpoints
- [Guia de Performance](docs/PERFORMANCE.md) - Otimizações e benchmarks
- [Runbook Operacional](docs/RUNBOOK.md) - Procedimentos de operação
- [FAQ](docs/FAQ.md) - Perguntas frequentes

## 🤝 Contribuindo

```bash
# Fork e clone
git clone https://github.com/SEU-USER/mt5-trading-db.git

# Criar branch
git checkout -b feature/minha-feature

# Commit com conventional commits
git commit -m "feat: adicionar suporte a Ichimoku"

# Push e PR
git push origin feature/minha-feature
```

## 📄 Licença

MIT License - veja [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- TimescaleDB por hypertables e continuous aggregates
- FastAPI por framework moderno e rápido
- MetaTrader 5 por plataforma de trading

## 📞 Suporte

- Issues: <https://github.com/Lysk-dot/mt5-trading-db/issues>
- Discussions: <https://github.com/Lysk-dot/mt5-trading-db/discussions>

---

**Desenvolvido com ❤️ para traders quantitativos**
