# Fluxo Híbrido de Ingestão MT5 Trading

## Arquitetura

```
EA MT5 ──┬─> POST /ingest_batch (candles M1 diretos) ──> market_data (M1)
         │                                                     │
         └─> POST /ingest/tick (ticks alta fluidez) ──> market_data_raw (JSONB)
                                                                │
                                                                v
                                                    Tick Aggregator (5s)
                                                                │
                                                                v
                                                        market_data (M1)
                                                                │
                                                                v
                                                    Indicators Worker (60s)
                                                                │
                                                                v
                                            Calcula RSI/MACD/ATR/BB server-side
                                                                │
                                                                v
                                            Continuous Aggregates (TimescaleDB)
                                                                │
                                     ┌──────────────────────────┴────────────────────────┐
                                     v                  v                v                v
                                   M5 view          M15 view         H1 view           D1 view
                                (auto-refresh)   (auto-refresh)   (auto-refresh)   (auto-refresh)
```

## Componentes

### 1. EA (Expert Advisor MT5)

**Modo normal (minuto):**
- Coleta candles M1 prontos do MT5
- Envia para `POST /ingest_batch` com array puro:
  ```json
  [
    {
      "ts": "2025-10-20T10:00:00Z",
      "symbol": "EURUSD",
      "timeframe": "M1",
      "open": 1.1000,
      "high": 1.1010,
      "low": 1.0995,
      "close": 1.1005,
      "volume": 123,
      "bid": 1.1004,
      "ask": 1.1006,
      "spread": 0.0002
    }
  ]
  ```
- Headers: `X-API-Key: <sua_chave>`, `Content-Type: application/json`

**Modo alta fluidez (tick):**
- Coleta ticks em tempo real
- Envia para `POST /ingest/tick`:
  ```json
  {
    "ticks": [
      {
        "ts": "2025-10-20T10:00:00.123Z",
        "symbol": "EURUSD",
        "bid": 1.1004,
        "ask": 1.1006,
        "spread": 0.0002,
        "volume": 1
      }
    ]
  }
  ```

### 2. Backend API (FastAPI)

**Endpoints de ingestão:**
- `POST /ingest`: aceita candle único ou `{"items":[...]}`
- `POST /ingest_batch`: aceita array puro de candles
- `POST /ingest/tick`: aceita `{"ticks":[...]}` para ticks brutos

**Funcionalidades:**
- Normalização de timestamp para bucket do timeframe (M1/M5/M15/M30/H1/H4/D1)
- Deduplicação por chave `(symbol, timeframe, ts_bucket)`
- Logs estruturados por item
- Resposta detalhada com `ts_original`, `ts_bucket`, `status` (inserted|duplicate)
- Métricas Prometheus (latência, duplicados, batch size)

### 3. Tick Aggregator (Worker)

**Funcionamento:**
- Roda a cada 5 segundos (configurável via `TICK_AGG_INTERVAL`)
- Lê `market_data_raw` desde último processamento
- Agrega ticks por minuto usando SQL:
  - OHLC baseado em mid price `(bid+ask)/2`
  - Soma de volume
  - Média de spread
- Faz upsert em `market_data` com `timeframe='M1'`
- Mantém estado em `public.aggregator_state`

**Execução:**
```bash
# Standalone
python api/run_tick_aggregator.py

# Docker Compose (automático)
docker-compose up tick-aggregator
```

### 4. Indicators Worker

**Funcionamento:**
- Roda a cada 60 segundos (configurável via `INDICATORS_INTERVAL`)
- Calcula indicadores técnicos server-side para últimos 200 minutos:
  - RSI (14 períodos)
  - MACD (12/26/9)
  - ATR (14 períodos)
  - Bollinger Bands (20 períodos, 2 std)
- Atualiza colunas em `market_data`
- **Garante consistência treino/produção** (mesmos parâmetros)

**Execução:**
```bash
# Standalone
SYMBOLS=EURUSD,GBPUSD python api/run_indicators_worker.py

# Docker Compose (automático)
docker-compose up indicators-worker
```

### 5. Continuous Aggregates (TimescaleDB)

**Views materializadas automáticas:**
- `market_data_m5`: agregação de 5 minutos (refresh a cada 1 min)
- `market_data_m15`: agregação de 15 minutos (refresh a cada 5 min)
- `market_data_m30`: agregação de 30 minutos (refresh a cada 10 min)
- `market_data_h1`: agregação de 1 hora (refresh a cada 15 min)
- `market_data_h4`: agregação de 4 horas (refresh a cada 30 min)
- `market_data_d1`: agregação diária (refresh a cada 1 hora)

**Benefícios:**
- Zero processamento redundante
- Atualização incremental automática
- Queries rápidas em timeframes maiores

**Uso:**
```sql
-- Consultar M5 diretamente
SELECT * FROM market_data_m5 
WHERE symbol = 'EURUSD' 
  AND ts >= NOW() - INTERVAL '1 day'
ORDER BY ts DESC;
```

## Fluxo de Dados Completo

### 1. Candles Diretos (caminho rápido)
```
EA M1 candle → /ingest_batch → market_data (M1) → Indicators Worker → RSI/MACD/etc
                                                                         ↓
                                                            Continuous Aggregates
                                                                         ↓
                                                            M5/M15/H1/D1 views
```

### 2. Ticks Alta Fluidez (fallback)
```
EA ticks → /ingest/tick → market_data_raw → Tick Aggregator → market_data (M1)
                                                                      ↓
                                                           Indicators Worker
                                                                      ↓
                                                         Continuous Aggregates
```

## Qualidade dos Dados

### Normalização de Timestamp
- **M1**: zera segundos/microssegundos
- **M5**: bucket de 5 minutos (ex: 10:07 → 10:05)
- **M15**: bucket de 15 minutos
- **M30**: bucket de 30 minutos
- **H1**: zera minutos/segundos
- **H4**: bucket de 4 horas (ex: 13h → 12h)
- **D1**: meia-noite UTC

### Deduplicação
- Chave primária: `(symbol, timeframe, ts_bucket)`
- `ON CONFLICT DO NOTHING` para candles diretos
- `ON CONFLICT DO UPDATE` para tick aggregator (permite atualização incremental)

### Indicadores Consistentes
- Cálculo único server-side (não no EA)
- Mesmos parâmetros treino/produção
- Atualização periódica automática

### Monitoramento
- Logs estruturados por item (candle/tick)
- Métricas Prometheus:
  - `ingest_candles_inserted_total`
  - `ingest_duplicates_total{symbol,timeframe}`
  - `ingest_latency_seconds`
  - `ingest_batch_size`
- Health checks em todos os workers

## Configuração

### Variáveis de Ambiente

```bash
# API
API_KEY=supersecretkey
DATABASE_URL=postgresql+psycopg://trader:trader123@pgbouncer:5432/mt5_trading

# Tick Aggregator
TICK_AGG_INTERVAL=5  # segundos

# Indicators Worker
INDICATORS_INTERVAL=60  # segundos
SYMBOLS=EURUSD,GBPUSD,USDJPY,GOLD

# Database
POSTGRES_USER=trader
POSTGRES_PASSWORD=trader123
POSTGRES_DB=mt5_trading
```

### Inicialização

```bash
# 1. Criar volumes
docker volume create models_mt5

# 2. Criar arquivo .env (copiar de env.template)
cp env.template .env
# Editar .env com suas credenciais

# 3. Subir infraestrutura
docker-compose up -d db
docker-compose up -d pgbouncer

# 4. Aguardar DB ficar saudável
docker-compose ps

# 5. Aplicar continuous aggregates (apenas primeira vez)
docker-compose exec db psql -U trader -d mt5_trading -f /docker-entrypoint-initdb.d/04-continuous-aggregates.sql

# 6. Subir todos os serviços
docker-compose up -d
```

### Verificação

```bash
# Status dos serviços
docker-compose ps

# Logs do tick aggregator
docker-compose logs -f tick-aggregator

# Logs do indicators worker
docker-compose logs -f indicators-worker

# Verificar dados em M1
docker-compose exec db psql -U trader -d mt5_trading \
  -c "SELECT COUNT(*) FROM market_data WHERE timeframe='M1';"

# Verificar continuous aggregates
docker-compose exec db psql -U trader -d mt5_trading \
  -c "SELECT * FROM market_data_m5 ORDER BY ts DESC LIMIT 10;"
```

## Manutenção

### Refresh Manual das Views
```sql
-- Se precisar forçar refresh completo
CALL refresh_continuous_aggregate('market_data_m5', NULL, NULL);
CALL refresh_continuous_aggregate('market_data_m15', NULL, NULL);
CALL refresh_continuous_aggregate('market_data_h1', NULL, NULL);
CALL refresh_continuous_aggregate('market_data_d1', NULL, NULL);
```

### Limpeza de Ticks Antigos
```sql
-- market_data_raw cresce rapidamente; limpe ticks já processados
DELETE FROM market_data_raw 
WHERE received_at < NOW() - INTERVAL '7 days';
```

### Monitorar Aggregator State
```sql
-- Ver última execução do aggregator
SELECT * FROM aggregator_state WHERE key = 'tick_agg_last_received_at';
```

## Performance

### Benchmarks Esperados
- **Ingestão direta M1**: ~1-2ms latência, 10k candles/min
- **Ingestão ticks**: ~5-10ms latência, 50k ticks/min
- **Tick aggregator**: processa 100k ticks em ~2s
- **Indicators worker**: calcula 200 candles/símbolo em ~500ms

### Otimizações
- PgBouncer pool: 50 conexões
- TimescaleDB compression (7 dias)
- Retention policy (90 dias)
- Indexes em `(symbol, timeframe, ts)`

## Troubleshooting

### Ticks não sendo agregados
```bash
# Ver logs do aggregator
docker-compose logs tick-aggregator

# Verificar ticks em raw
docker-compose exec db psql -U trader -d mt5_trading \
  -c "SELECT COUNT(*), MAX(received_at) FROM market_data_raw;"
```

### Indicadores não calculados
```bash
# Ver logs do worker
docker-compose logs indicators-worker

# Verificar candles sem indicadores
docker-compose exec db psql -U trader -d mt5_trading \
  -c "SELECT COUNT(*) FROM market_data WHERE timeframe='M1' AND rsi IS NULL;"
```

### Continuous aggregate desatualizado
```sql
-- Ver políticas de refresh
SELECT * FROM timescaledb_information.jobs 
WHERE proc_name LIKE '%continuous%';

-- Executar refresh manual
CALL refresh_continuous_aggregate('market_data_m5', NULL, NULL);
```

## Roadmap

- [ ] Suporte a Ichimoku Cloud
- [ ] Worker de labels automático (classificação alta/baixa)
- [ ] Export incremental Parquet para treino ML
- [ ] Dashboard Grafana pré-configurado
- [ ] Alertas de qualidade (gaps, outliers)
