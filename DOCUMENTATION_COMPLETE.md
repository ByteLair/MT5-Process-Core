# 📚 Documentação Completa - Sistema MT5 Trading

**Versão:** 2.0
**Data:** 2025-10-20
**Status:** ✅ Produção

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Fluxo de Dados Híbrido](#fluxo-de-dados-híbrido)
4. [Componentes](#componentes)
5. [API Endpoints](#api-endpoints)
6. [Workers](#workers)
7. [Banco de Dados](#banco-de-dados)
8. [Observabilidade](#observabilidade)
9. [Configuração](#configuração)
10. [Deploy e Infraestrutura](#deploy-e-infraestrutura)
11. [Testes](#testes)
12. [Troubleshooting](#troubleshooting)
13. [Desenvolvimento](#desenvolvimento)
14. [Referências](#referências)

---

## 🎯 Visão Geral

### O que é o Sistema MT5 Trading?

Sistema completo de ingestão, processamento e análise de dados financeiros do MetaTrader 5 (MT5), com arquitetura híbrida que suporta:

- 📊 **Candles OHLC** (timeframes M1, M5, M15, M30, H1, H4, D1)
- ⚡ **Dados Tick-by-tick** para alta frequência
- 🤖 **Cálculo automático de indicadores técnicos** (RSI, MACD, ATR, Bollinger Bands)
- 🔄 **Agregação automática** de ticks em candles
- 📈 **Continuous aggregates** para múltiplos timeframes
- 🧠 **Pipeline de Machine Learning** para previsões

### Características Principais

- ✅ **Alta Performance**: TimescaleDB para séries temporais
- ✅ **Escalável**: Arquitetura de microserviços com Docker
- ✅ **Observável**: Stack completa (Prometheus, Grafana, Loki, Jaeger)
- ✅ **Resiliente**: Health checks, retries, logs estruturados
- ✅ **Consistente**: Indicadores calculados server-side
- ✅ **Flexível**: Suporta ingestão de candles prontos ou ticks brutos

---

## 🏗 Arquitetura do Sistema

### Diagrama de Arquitetura

```
┌────────────────────────────────────────────────────────────────┐
│                        CAMADA DE ENTRADA                        │
│  ┌──────────┐         ┌──────────┐         ┌──────────┐       │
│  │ EA (MT5) │         │  APIs    │         │ Scripts  │       │
│  │ Candles  │         │ Externas │         │  Batch   │       │
│  └────┬─────┘         └────┬─────┘         └────┬─────┘       │
└───────┼────────────────────┼───────────────────┼──────────────┘
        │                    │                   │
        │ M1 Candles         │ Ticks             │ Historical
        │                    │                   │
        ▼                    ▼                   ▼
┌────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  POST /ingest          POST /ingest_batch                │  │
│  │  POST /ingest/tick     GET /health                       │  │
│  │  Authentication: X-API-Key                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────┬────────────────────────────────────────┬───────────────┘
        │                                        │
        ▼                                        ▼
┌─────────────────────┐              ┌─────────────────────┐
│   market_data       │              │  market_data_raw    │
│   (Candles OHLC)    │              │  (Ticks JSONB)      │
│   - Hypertable      │              │  - Raw storage      │
│   - Indicadores     │              │  - High frequency   │
└──────┬──────────────┘              └──────┬──────────────┘
       │                                     │
       │                            ┌────────▼───────────┐
       │                            │ tick_aggregator    │
       │                            │ Worker (5s)        │
       │                            │ Agregar → M1       │
       │                            └────────┬───────────┘
       │                                     │
       │◄────────────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│ indicators_worker   │
│ Worker (60s)        │
│ RSI/MACD/ATR/BB     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│              CONTINUOUS AGGREGATES (TimescaleDB)        │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │
│  │   M5   │ │  M15   │ │  M30   │ │   H1   │ ...      │
│  │ Refresh│ │ Refresh│ │ Refresh│ │ Refresh│          │
│  │  1 min │ │  5 min │ │ 10 min │ │ 15 min │          │
│  └────────┘ └────────┘ └────────┘ └────────┘          │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                 MACHINE LEARNING PIPELINE               │
│  prepare_dataset.py → train_model.py → predict.py      │
└─────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                   OBSERVABILITY STACK                   │
│  Prometheus → Metrics  |  Loki → Logs                  │
│  Jaeger → Traces       |  Grafana → Dashboards         │
└─────────────────────────────────────────────────────────┘
```

### Fluxo de Decisão: Candles vs Ticks

```
┌─────────────────────┐
│  EA Recebe Dados    │
└──────────┬──────────┘
           │
           ▼
    ┌──────────────┐
    │ Mercado com  │◄─── SIM ─── POST /ingest_batch
    │ liquidez     │              (Candles M1)
    │ normal?      │
    └──────┬───────┘
           │
          NÃO (alta volatilidade)
           │
           ▼
    POST /ingest/tick ──► market_data_raw
    (Ticks brutos)              │
                                │
                        ┌───────▼────────┐
                        │ tick_aggregator │
                        │    (5s loop)    │
                        └───────┬─────────┘
                                │
                        Agregação SQL:
                        - time_bucket('1 minute')
                        - OHLC de (bid+ask)/2
                        - Volume = count(*)
                                │
                                ▼
                           market_data
                           (Candles M1)
```

---

## 🧩 Componentes

### 1. API (FastAPI)

**Localização:** `api/app/main.py`, `api/app/ingest.py`
**Imagem Docker:** `mt5-api`
**Porta:** 18002, 18003

**Responsabilidades:**

- Receber dados do EA via HTTP REST
- Validar payloads com Pydantic
- Normalizar timestamps por timeframe bucket
- Inserir dados no banco com controle de duplicatas
- Retornar respostas detalhadas com status por item
- Coletar métricas Prometheus
- Emitir traces OpenTelemetry

**Endpoints Principais:**

```python
POST /ingest          # Candle único ou {"items": [...]}
POST /ingest_batch    # Array direto [...]
POST /ingest/tick     # {"ticks": [...]}
GET  /health          # Health check
GET  /docs            # Swagger UI
GET  /metrics         # Prometheus metrics
```

**Dependências:**

- FastAPI 0.115.0
- SQLAlchemy 2.0.36
- psycopg (binary)
- Pydantic 2.9.2
- prometheus-client
- opentelemetry-*

### 2. Tick Aggregator Worker

**Localização:** `api/app/tick_aggregator.py`, `api/run_tick_aggregator.py`
**Container:** `mt5_tick_aggregator`
**Intervalo:** 5 segundos (configurável via `TICK_AGG_INTERVAL`)

**Responsabilidades:**

- Ler ticks de `market_data_raw` (JSONB)
- Agregar usando SQL com `time_bucket('1 minute')`
- Calcular OHLC a partir de `(bid + ask) / 2`
- Inserir/atualizar candles M1 em `market_data`
- Manter estado em `aggregator_state`
- Logar cada execução com contadores

**Algoritmo de Agregação:**

```sql
SELECT
  symbol,
  'M1' as timeframe,
  time_bucket('1 minute', ts) as ts,
  (array_agg((bid + ask)/2 ORDER BY ts))[1] as open,
  MAX((bid + ask)/2) as high,
  MIN((bid + ask)/2) as low,
  (array_agg((bid + ask)/2 ORDER BY ts DESC))[1] as close,
  COUNT(*) as volume,
  AVG(ask - bid) as spread
FROM (
  SELECT
    r.symbol,
    (t->>'ts')::timestamptz as ts,
    (t->>'bid')::numeric as bid,
    (t->>'ask')::numeric as ask
  FROM market_data_raw r,
  jsonb_array_elements(r.data) as t
  WHERE r.received_at > :last
    AND r.received_at <= :upto
) ticks
GROUP BY symbol, time_bucket('1 minute', ts)
```

**Configuração:**

```yaml
TICK_AGG_INTERVAL: 5  # segundos entre execuções
DATABASE_URL: postgresql+psycopg://trader:trader123@db:5432/mt5_trading
```

### 3. Indicators Worker

**Localização:** `api/app/indicators_worker.py`, `api/run_indicators_worker.py`
**Container:** `mt5_indicators_worker`
**Intervalo:** 60 segundos (configurável via `INDICATORS_INTERVAL`)

**Responsabilidades:**

- Calcular indicadores técnicos server-side
- Garantir consistência entre treino e produção
- Processar últimos 200 minutos por símbolo
- Atualizar colunas em `market_data`

**Indicadores Implementados:**

1. **RSI (Relative Strength Index)**
   - Período: 14
   - Fórmula: `100 - (100 / (1 + RS))`
   - RS = Média de ganhos / Média de perdas

2. **MACD (Moving Average Convergence Divergence)**
   - Fast EMA: 12
   - Slow EMA: 26
   - Signal: 9
   - Retorna: macd_line, macd_signal, macd_hist

3. **ATR (Average True Range)**
   - Período: 14
   - True Range = max(high-low, |high-prev_close|, |low-prev_close|)
   - ATR = Média móvel do TR

4. **Bollinger Bands**
   - Período: 20
   - Desvios: 2.0
   - Upper = SMA + (2 × StdDev)
   - Middle = SMA
   - Lower = SMA - (2 × StdDev)

**Código Exemplo:**

```python
def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

**Configuração:**

```yaml
INDICATORS_INTERVAL: 60  # segundos
SYMBOLS: EURUSD,GBPUSD,USDJPY  # símbolos a processar
DATABASE_URL: postgresql+psycopg://trader:trader123@db:5432/mt5_trading
```

### 4. Banco de Dados (TimescaleDB)

**Imagem:** `timescale/timescaledb:2.14.2-pg16`
**Container:** `mt5_db`
**Porta Interna:** 5432

**Extensões Habilitadas:**

- `timescaledb` - Séries temporais
- `pg_stat_statements` - Estatísticas de queries
- `btree_gist` - Índices avançados

**Tabelas Principais:**

#### market_data (Hypertable)

```sql
CREATE TABLE market_data (
    id BIGSERIAL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    open NUMERIC(18,8) NOT NULL,
    high NUMERIC(18,8) NOT NULL,
    low NUMERIC(18,8) NOT NULL,
    close NUMERIC(18,8) NOT NULL,
    volume NUMERIC(18,2) DEFAULT 0,
    spread NUMERIC(18,8),
    rsi NUMERIC(18,8),
    macd NUMERIC(18,8),
    macd_signal NUMERIC(18,8),
    macd_hist NUMERIC(18,8),
    atr NUMERIC(18,8),
    bb_upper NUMERIC(18,8),
    bb_middle NUMERIC(18,8),
    bb_lower NUMERIC(18,8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, timeframe, ts)
);

-- Converter em hypertable
SELECT create_hypertable('market_data', 'ts',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Índices
CREATE INDEX idx_market_data_symbol_tf ON market_data(symbol, timeframe, ts DESC);
CREATE INDEX idx_market_data_ts ON market_data(ts DESC);
```

#### market_data_raw (Ticks JSONB)

```sql
CREATE TABLE market_data_raw (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    data JSONB NOT NULL,  -- Array de ticks
    received_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_market_data_raw_symbol ON market_data_raw(symbol);
CREATE INDEX idx_market_data_raw_received ON market_data_raw(received_at DESC);
```

#### aggregator_state

```sql
CREATE TABLE aggregator_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**Continuous Aggregates:**

Definidos em `db/init/04-continuous-aggregates.sql`:

```sql
-- M5 (refresh a cada 1 min)
CREATE MATERIALIZED VIEW market_data_m5
WITH (timescaledb.continuous) AS
SELECT
    symbol,
    'M5' as timeframe,
    time_bucket('5 minutes', ts) as ts,
    first(open, ts) as open,
    max(high) as high,
    min(low) as low,
    last(close, ts) as close,
    sum(volume) as volume,
    avg(spread) as spread
FROM market_data
WHERE timeframe = 'M1'
GROUP BY symbol, time_bucket('5 minutes', ts);

SELECT add_continuous_aggregate_policy('market_data_m5',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute'
);
```

Similar para M15, M30, H1, H4, D1.

### 5. Observabilidade

#### Prometheus (Métricas)

- **Porta:** 19090
- **Config:** `prometheus.yml`
- **Scrape Interval:** 15s
- **Targets:** API, Node Exporter

#### Grafana (Dashboards)

- **Porta:** 13000
- **Credenciais:** admin/admin
- **Datasources:** Prometheus, Loki, Jaeger, PostgreSQL
- **Dashboards:** `grafana/dashboards/`

#### Loki (Logs)

- **Porta:** 13100
- **Config:** `loki/loki-config.yml`
- **Retention:** 168h (7 dias)

#### Promtail (Coleta de Logs)

- **Config:** `loki/promtail-config.yml`
- **Sources:** `/var/log`, `./logs`

#### Jaeger (Distributed Tracing)

- **UI:** 26686
- **OTLP gRPC:** 24317
- **OTLP HTTP:** 24318
- **Storage:** Badger (local)

#### PgBouncer (Connection Pooling)

- **Porta:** 6432
- **Max Connections:** 50
- **Pool Mode:** session
- **Config:** `pgbouncer/pgbouncer.ini`

---

## 📡 API Endpoints

### Base URL

```
http://localhost:18002
```

### Autenticação

Todos os endpoints (exceto `/health` e `/docs`) requerem:

```http
X-API-Key: <valor_do_arquivo_.env>
```

### POST /ingest

Envia candle único ou batch com envelope.

**Request:**

```json
{
  "items": [
    {
      "symbol": "EURUSD",
      "timeframe": "M1",
      "ts": "2025-10-20T03:00:00Z",
      "open": 1.0855,
      "high": 1.0857,
      "low": 1.0854,
      "close": 1.0856,
      "volume": 150,
      "spread": 2
    }
  ]
}
```

**Response:**

```json
{
  "ok": true,
  "received": 1,
  "inserted": 1,
  "duplicates": 0,
  "details": [
    {
      "symbol": "EURUSD",
      "timeframe": "M1",
      "ts_original": "2025-10-20T03:00:00+00:00",
      "ts_bucket": "2025-10-20T03:00:00+00:00",
      "status": "inserted"
    }
  ]
}
```

### POST /ingest_batch

Envia array direto de candles (mais simples para EA).

**Request:**

```json
[
  {
    "symbol": "EURUSD",
    "timeframe": "M1",
    "ts": "2025-10-20T03:00:00Z",
    "open": 1.0855,
    "high": 1.0857,
    "low": 1.0854,
    "close": 1.0856,
    "volume": 150,
    "spread": 2
  },
  {
    "symbol": "GBPUSD",
    "timeframe": "M1",
    "ts": "2025-10-20T03:00:00Z",
    "open": 1.2850,
    "high": 1.2852,
    "low": 1.2849,
    "close": 1.2851,
    "volume": 120,
    "spread": 2
  }
]
```

**Response:** Igual ao `/ingest`

### POST /ingest/tick

Envia ticks de alta frequência.

**Request:**

```json
{
  "ticks": [
    {
      "symbol": "EURUSD",
      "ts": "2025-10-20T03:01:10.123Z",
      "bid": 1.0855,
      "ask": 1.0857
    },
    {
      "symbol": "EURUSD",
      "ts": "2025-10-20T03:01:15.456Z",
      "bid": 1.0856,
      "ask": 1.0858
    }
  ]
}
```

**Response:**

```json
{
  "ok": true,
  "received": 2,
  "details": [
    {
      "symbol": "EURUSD",
      "ts_original": "2025-10-20T03:01:10.123Z",
      "ts_bucket": "2025-10-20T03:01:00+00:00",
      "status": "received"
    },
    {
      "symbol": "EURUSD",
      "ts_original": "2025-10-20T03:01:15.456Z",
      "ts_bucket": "2025-10-20T03:01:00+00:00",
      "status": "received"
    }
  ]
}
```

### GET /health

Health check da API.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2025-10-20T03:05:00Z"
}
```

### Normalização de Timestamps

A API normaliza timestamps para o início do bucket do timeframe:

| Timeframe | Normalização | Exemplo |
|-----------|--------------|---------|
| M1 | Segundos = 0 | 03:05:23 → 03:05:00 |
| M5 | Minuto múltiplo de 5 | 03:07:00 → 03:05:00 |
| M15 | Minuto múltiplo de 15 | 03:12:00 → 03:00:00 |
| M30 | Minuto 0 ou 30 | 03:45:00 → 03:30:00 |
| H1 | Minutos = 0 | 03:30:00 → 03:00:00 |
| H4 | Hora múltipla de 4 | 05:00:00 → 04:00:00 |
| D1 | Meia-noite UTC | 15:00:00 → 00:00:00 |

**Função Python:**

```python
def _bucket_start(ts: datetime, timeframe: str) -> datetime:
    if timeframe == "M1":
        return ts.replace(second=0, microsecond=0)
    elif timeframe == "M5":
        return ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
    elif timeframe == "M15":
        return ts.replace(minute=(ts.minute // 15) * 15, second=0, microsecond=0)
    # ... etc
```

---

## 🔧 Configuração

### Variáveis de Ambiente (.env)

```bash
# Database
POSTGRES_USER=trader
POSTGRES_PASSWORD=trader123
POSTGRES_DB=mt5_trading

# API
API_KEY=seu_token_super_secreto_aqui
API_PORT_INTERNAL=8001
UVICORN_WORKERS=1

# Workers
TICK_AGG_INTERVAL=5
INDICATORS_INTERVAL=60
SYMBOLS=EURUSD,GBPUSD,USDJPY

# Observability
JAEGER_AGENT_HOST=jaeger
JAEGER_AGENT_PORT=6831

# PgAdmin
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin123
PGADMIN_PORT=15050

# Grafana
GF_SECURITY_ADMIN_PASSWORD=admin
```

### docker-compose.yml

Arquivo principal de orquestração. Principais serviços:

```yaml
services:
  db:
    image: timescale/timescaledb:2.14.2-pg16
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./db/init:/docker-entrypoint-initdb.d:ro

  api:
    build: ./api
    image: mt5-api
    ports:
      - "18002:8001"
      - "18003:8001"
    environment:
      DATABASE_URL: postgresql+psycopg://trader:trader123@db:5432/mt5_trading

  tick-aggregator:
    image: mt5-api
    command: ["python", "run_tick_aggregator.py"]
    environment:
      TICK_AGG_INTERVAL: ${TICK_AGG_INTERVAL:-5}

  indicators-worker:
    image: mt5-api
    command: ["python", "run_indicators_worker.py"]
    environment:
      INDICATORS_INTERVAL: ${INDICATORS_INTERVAL:-60}
      SYMBOLS: ${SYMBOLS:-EURUSD,GBPUSD,USDJPY}
```

### Portas Utilizadas

| Serviço | Porta Host | Porta Container | Protocolo |
|---------|-----------|----------------|-----------|
| API | 18002, 18003 | 8001 | HTTP |
| PgBouncer | 6432 | 5432 | PostgreSQL |
| Prometheus | 19090 | 9090 | HTTP |
| Grafana | 13000 | 3000 | HTTP |
| Loki | 13100 | 3100 | HTTP |
| Jaeger UI | 26686 | 16686 | HTTP |
| Jaeger OTLP gRPC | 24317 | 4317 | gRPC |
| Jaeger OTLP HTTP | 24318 | 4318 | HTTP |
| PgAdmin | 15050 | 80 | HTTP |
| Node Exporter | 9100 | 9100 | HTTP |

---

## 🧪 Testes

### Script de Teste Automatizado

**Arquivo:** `test_hybrid_flow.sh`

```bash
#!/bin/bash

API_KEY=$(grep ^API_KEY= .env | cut -d= -f2 | tr -d '"')
BASE_URL="http://localhost:18002"

echo "1. Testando /ingest_batch com candle M1"
curl -X POST "$BASE_URL/ingest_batch" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '[{
    "symbol":"EURUSD",
    "timeframe":"M1",
    "ts":"2025-10-20T03:00:00Z",
    "open":1.0855,
    "high":1.0857,
    "low":1.0854,
    "close":1.0856,
    "volume":150,
    "spread":2
  }]' | jq

echo -e "\n2. Testando /ingest/tick com ticks"
curl -X POST "$BASE_URL/ingest/tick" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "ticks":[
      {"symbol":"EURUSD","ts":"2025-10-20T03:01:10.123Z","bid":1.0855,"ask":1.0857},
      {"symbol":"EURUSD","ts":"2025-10-20T03:01:15.456Z","bid":1.0856,"ask":1.0858}
    ]
  }' | jq

echo -e "\n3. Verificando dados no banco"
docker exec mt5_db psql -U trader -d mt5_trading \
  -c "SELECT symbol, timeframe, ts, close FROM market_data ORDER BY ts DESC LIMIT 5;"
```

### Testes Manuais

#### 1. Health Check

```bash
curl http://localhost:18002/health
```

#### 2. Teste de Ingestão

```bash
API_KEY=$(grep ^API_KEY= .env | cut -d= -f2 | tr -d '"')

curl -X POST http://localhost:18002/ingest_batch \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '[{
    "symbol":"EURUSD",
    "timeframe":"M1",
    "ts":"2025-10-20T03:00:00Z",
    "open":1.0855,
    "high":1.0857,
    "low":1.0854,
    "close":1.0856,
    "volume":150,
    "spread":2
  }]'
```

#### 3. Verificar Workers

```bash
# Tick Aggregator
docker logs mt5_tick_aggregator --tail 20

# Indicators Worker
docker logs mt5_indicators_worker --tail 20
```

#### 4. Query no Banco

```bash
docker exec mt5_db psql -U trader -d mt5_trading

# No psql:
SELECT * FROM market_data WHERE symbol='EURUSD' ORDER BY ts DESC LIMIT 10;
SELECT symbol, COUNT(*) FROM market_data_raw GROUP BY symbol;
SELECT * FROM aggregator_state;
```

### Testes de Performance

#### Benchmark de Ingestão

```bash
# Gerar 1000 candles
for i in {1..1000}; do
  curl -X POST http://localhost:18002/ingest_batch \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d "[{\"symbol\":\"EURUSD\",\"timeframe\":\"M1\",\"ts\":\"2025-10-20T03:$(printf %02d $((i%60))):00Z\",\"open\":1.08,\"high\":1.081,\"low\":1.079,\"close\":1.0805,\"volume\":100,\"spread\":2}]" \
    -s -o /dev/null -w "%{time_total}\n"
done | awk '{sum+=$1; count++} END {print "Média:", sum/count, "s"}'
```

---

## 🚀 Deploy e Infraestrutura

### Deploy Local (Docker Compose)

```bash
# 1. Clonar repositório
git clone https://github.com/Lysk-dot/mt5-trading-db.git
cd mt5-trading-db

# 2. Criar arquivo .env
cp env.template .env
nano .env  # Configurar variáveis

# 3. Criar volume para modelos ML
docker volume create models_mt5

# 4. Subir todos os containers
docker-compose up -d

# 5. Verificar status
docker-compose ps

# 6. Ver logs
docker-compose logs -f api tick-aggregator indicators-worker

# 7. Aplicar continuous aggregates
docker exec mt5_db psql -U trader -d mt5_trading \
  -f /docker-entrypoint-initdb.d/04-continuous-aggregates.sql
```

### Deploy Kubernetes (Helm)

```bash
# 1. Configurar valores
cp helm/mt5-trading/values.yaml helm/mt5-trading/values-prod.yaml
nano helm/mt5-trading/values-prod.yaml

# 2. Instalar chart
helm install mt5-trading ./helm/mt5-trading \
  -f helm/mt5-trading/values-prod.yaml \
  --namespace trading \
  --create-namespace

# 3. Verificar pods
kubectl get pods -n trading

# 4. Port forward para acesso local
kubectl port-forward -n trading svc/mt5-api 18002:8001
```

### Estrutura Kubernetes

```
k8s/
├── base/
│   ├── api/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── workers/
│   │   ├── tick-aggregator-deployment.yaml
│   │   └── indicators-worker-deployment.yaml
│   └── database/
│       ├── statefulset.yaml
│       └── service.yaml
└── overlays/
    ├── dev/
    ├── staging/
    └── production/
```

### Terraform (IaC)

```bash
cd infra/terraform

# Inicializar
terraform init

# Planejar
terraform plan -out=plan.out

# Aplicar
terraform apply plan.out
```

**Recursos Provisionados:**

- VPC e Subnets
- EKS Cluster
- RDS TimescaleDB
- S3 para backups
- CloudWatch logs
- ALB para API

---

## 🔍 Troubleshooting

### Problemas Comuns

#### 1. Workers marcados como "unhealthy"

**Sintoma:**

```
mt5_tick_aggregator     Up 10 minutes (unhealthy)
```

**Causa:** Healthcheck usa `pgrep` que não existe na imagem Python slim

**Verificação:**

```bash
docker logs mt5_tick_aggregator --tail 20
# Deve mostrar: "INFO - Aggregated ticks: ..."
```

**Solução:** Se logs mostram processamento, ignorar status "unhealthy" (é cosmético)

**Correção Permanente:** Instalar `procps` na imagem ou trocar healthcheck

#### 2. Erro "wrong password type"

**Sintoma:**

```
psycopg.OperationalError: connection failed: FATAL: server login failed: wrong password type
```

**Causa:** Workers tentando conectar via pgbouncer com psycopg

**Solução:**

```yaml
# docker-compose.yml
environment:
  DATABASE_URL: postgresql+psycopg://trader:trader123@db:5432/mt5_trading
  # NÃO usar @pgbouncer
```

#### 3. Containers com nomes estranhos

**Sintoma:**

```
15c1ad2b98f5_mt5_tick_aggregator
```

**Causa:** Recriações múltiplas deixaram containers órfãos

**Solução:**

```bash
# Obter PID e matar
PID=$(docker inspect <container> | grep '"Pid"' | grep -oP '\d+' | tail -1)
sudo kill -9 $PID

# Remover e recriar
docker rm -f <container>
docker-compose up -d <service>
```

#### 4. Grafana em loop de restart

**Sintoma:**

```
mt5_grafana  Restarting (1) 29 seconds ago
```

**Logs:**

```
Error: ✗ alert rules: A folder with that name already exists
```

**Solução:**

```bash
# Desabilitar provisionamento problemático
cd grafana/provisioning/alerting
for f in *.yml *.yaml; do mv "$f" "$f.disabled"; done

# Recriar volume
docker stop mt5_grafana
docker rm mt5_grafana
docker volume rm mt5-trading-db_grafana_data
docker-compose up -d grafana
```

#### 5. API não recebe dados

**Verificações:**

```bash
# 1. Health check
curl http://localhost:18002/health

# 2. Verificar logs
docker logs mt5_api --tail 50

# 3. Testar autenticação
API_KEY=$(grep ^API_KEY= .env | cut -d= -f2 | tr -d '"')
curl -H "X-API-Key: $API_KEY" http://localhost:18002/health

# 4. Verificar conectividade com banco
docker exec mt5_api nc -zv db 5432
```

#### 6. Banco de dados lento

**Diagnóstico:**

```sql
-- Queries lentas
SELECT * FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Tamanho das tabelas
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Chunks da hypertable
SELECT * FROM timescaledb_information.chunks
WHERE hypertable_name = 'market_data'
ORDER BY range_start DESC;
```

**Otimizações:**

```sql
-- Reindexar
REINDEX TABLE market_data;

-- Vacuum
VACUUM ANALYZE market_data;

-- Comprimir chunks antigos
SELECT compress_chunk(i)
FROM show_chunks('market_data', older_than => INTERVAL '7 days') i;
```

### Logs e Debugging

#### Acessar logs estruturados

```bash
# API
docker logs mt5_api -f --tail 100

# Workers
docker logs mt5_tick_aggregator -f
docker logs mt5_indicators_worker -f

# Banco
docker logs mt5_db --tail 50

# Todos juntos
docker-compose logs -f
```

#### Conectar ao container

```bash
# Bash no container
docker exec -it mt5_api bash

# Python REPL no container
docker exec -it mt5_api python

# PostgreSQL
docker exec -it mt5_db psql -U trader -d mt5_trading
```

#### Verificar métricas

```bash
# Prometheus metrics
curl http://localhost:18002/metrics

# Node exporter
curl http://localhost:9100/metrics

# Container stats
docker stats mt5_api mt5_tick_aggregator mt5_indicators_worker
```

---

## 👨‍💻 Desenvolvimento

### Setup Local

```bash
# 1. Criar ambiente virtual
python3.11 -m venv env
source env/bin/activate

# 2. Instalar dependências
pip install -r api/requirements.txt
pip install -r ml/requirements.txt

# 3. Instalar dev tools
pip install pytest black mypy ruff

# 4. Configurar pre-commit (opcional)
pre-commit install
```

### Estrutura do Projeto

```
mt5-trading-db/
├── api/                      # API FastAPI
│   ├── app/
│   │   ├── main.py          # Entry point
│   │   ├── ingest.py        # Endpoints de ingestão
│   │   ├── tick_aggregator.py
│   │   ├── indicators_worker.py
│   │   ├── db.py            # Database connection
│   │   └── config.py        # Configurações
│   ├── run_tick_aggregator.py
│   ├── run_indicators_worker.py
│   ├── requirements.txt
│   └── Dockerfile
├── ml/                       # Machine Learning
│   ├── prepare_dataset.py
│   ├── train_model.py
│   ├── predict.py
│   └── requirements.txt
├── db/                       # Database
│   └── init/
│       ├── 01-init.sql
│       ├── 02-hypertable.sql
│       ├── 03-indexes.sql
│       └── 04-continuous-aggregates.sql
├── docs/                     # Documentação
│   ├── HYBRID_INGESTION_FLOW.md
│   ├── API.md
│   └── DEPLOYMENT.md
├── grafana/                  # Dashboards
│   ├── dashboards/
│   └── provisioning/
├── k8s/                      # Kubernetes manifests
├── helm/                     # Helm charts
├── infra/terraform/          # Infrastructure as Code
├── docker-compose.yml
├── .env
└── README.md
```

### Padrões de Código

#### Python

```python
# Imports
import os
import sys
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import FastAPI
from sqlalchemy import create_engine

# Type hints sempre
def process_data(symbol: str, timeframe: str) -> dict[str, int]:
    return {"count": 0}

# Docstrings
def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcula o RSI (Relative Strength Index).

    Args:
        series: Série de preços de fechamento
        period: Período para cálculo (padrão 14)

    Returns:
        Série com valores de RSI
    """
    pass

# Logging
import logging
logger = logging.getLogger(__name__)
logger.info("Processing started", extra={"symbol": "EURUSD"})
```

#### SQL

```sql
-- Sempre usar comentários
-- Índices descritivos
CREATE INDEX idx_market_data_symbol_ts
    ON market_data(symbol, ts DESC);

-- CTEs para legibilidade
WITH recent_data AS (
    SELECT * FROM market_data
    WHERE ts > NOW() - INTERVAL '1 hour'
)
SELECT symbol, COUNT(*)
FROM recent_data
GROUP BY symbol;
```

### Testes Unitários

```bash
# Rodar todos os testes
pytest

# Com coverage
pytest --cov=api --cov-report=html

# Testes específicos
pytest api/tests/test_ingest.py -v
```

**Exemplo de Teste:**

```python
# api/tests/test_ingest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ingest_batch_success():
    response = client.post(
        "/ingest_batch",
        headers={"X-API-Key": "test_key"},
        json=[{
            "symbol": "EURUSD",
            "timeframe": "M1",
            "ts": "2025-10-20T03:00:00Z",
            "open": 1.0855,
            "high": 1.0857,
            "low": 1.0854,
            "close": 1.0856,
            "volume": 150,
            "spread": 2
        }]
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["inserted"] == 1
```

### Linting e Formatação

```bash
# Black (formatação)
black api/ ml/

# Ruff (linting)
ruff check api/ ml/

# MyPy (type checking)
mypy api/ --strict

# Tudo de uma vez
black api/ && ruff check api/ && mypy api/
```

### CI/CD

**GitHub Actions:** `.github/workflows/ci.yml`

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r api/requirements.txt
      - run: pytest api/tests/
      - run: black --check api/
      - run: ruff check api/

  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: docker-compose build
      - run: docker-compose up -d
      - run: ./test_hybrid_flow.sh
```

---

## 📚 Referências

### Documentação Externa

- **FastAPI:** <https://fastapi.tiangolo.com/>
- **SQLAlchemy:** <https://docs.sqlalchemy.org/>
- **TimescaleDB:** <https://docs.timescale.com/>
- **Prometheus:** <https://prometheus.io/docs/>
- **Grafana:** <https://grafana.com/docs/>
- **OpenTelemetry:** <https://opentelemetry.io/docs/>
- **Docker Compose:** <https://docs.docker.com/compose/>
- **Kubernetes:** <https://kubernetes.io/docs/>

### Arquivos de Documentação

- `docs/HYBRID_INGESTION_FLOW.md` - Arquitetura do fluxo híbrido
- `docs/API.md` - Especificação detalhada da API
- `DEPLOYMENT_STATUS.md` - Status do deploy atual
- `CONTAINERS_STATUS.md` - Status dos containers
- `ALL_CONTAINERS_RUNNING.md` - Guia de containers e portas
- `WARNINGS_FIXED.md` - Resolução de problemas comuns
- `openapi.yaml` - Especificação OpenAPI 3.0

### Scripts Úteis

- `test_hybrid_flow.sh` - Testes automatizados
- `backup.sh` - Backup do banco de dados
- `setup_docker_permissions.sh` - Configurar permissões Docker
- `monitor_dados.sh` - Monitorar ingestão de dados

### Contatos

- **Repositório:** <https://github.com/Lysk-dot/mt5-trading-db>
- **Issues:** <https://github.com/Lysk-dot/mt5-trading-db/issues>
- **Desenvolvedor:** Felipe (Lysk-dot)

---

**Documentação gerada em:** 2025-10-20
**Versão do Sistema:** 2.0
**Status:** ✅ Produção
**Última Atualização:** 2025-10-20 02:55 UTC
