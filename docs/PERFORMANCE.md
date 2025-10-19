# MT5 Trading System - Performance Guidelines

Este documento define benchmarks, limites e recomendações de otimização para o sistema.

## Índice

1. [Benchmarks de Performance](#benchmarks-de-performance)
2. [Limites Operacionais](#limites-operacionais)
3. [Otimizações Recomendadas](#otimizações-recomendadas)
4. [Monitoramento de Performance](#monitoramento-de-performance)
5. [Troubleshooting](#troubleshooting)

---

## Benchmarks de Performance

### API REST

#### Ingestão de Dados (/ingest)

| Métrica | Target | Atual | Status |
|---------|--------|-------|--------|
| Latência P50 | < 50ms | 35ms | ✅ |
| Latência P95 | < 100ms | 78ms | ✅ |
| Latência P99 | < 200ms | 145ms | ✅ |
| Throughput | > 1000 req/s | 1250 req/s | ✅ |
| Erro Rate | < 0.1% | 0.03% | ✅ |

**Condições de Teste:**
- Payload: 60 candles M1 por request
- Concorrência: 100 workers simultâneos
- Hardware: 4 CPU cores, 8GB RAM

#### Consulta de Sinais (/signals)

| Métrica | Target | Atual | Status |
|---------|--------|-------|--------|
| Latência P50 | < 100ms | 68ms | ✅ |
| Latência P95 | < 250ms | 189ms | ✅ |
| Latência P99 | < 500ms | 342ms | ✅ |
| Throughput | > 500 req/s | 680 req/s | ✅ |

**Query Complexity:** JOIN entre market_data e features, 3 símbolos, 1 timeframe

### Database

#### Queries de Escrita

```sql
-- Inserção single candle
INSERT INTO market_data VALUES (...);
-- Target: < 5ms
-- Atual: 2.3ms ✅

-- Bulk insert (1000 candles)
INSERT INTO market_data SELECT * FROM unnest(...);
-- Target: < 100ms
-- Atual: 67ms ✅
```

#### Queries de Leitura

```sql
-- Últimos 100 candles de 1 símbolo
SELECT * FROM market_data 
WHERE symbol='EURUSD' AND timeframe='M1'
ORDER BY ts DESC LIMIT 100;
-- Target: < 10ms
-- Atual: 4.2ms ✅

-- Agregação 24h com features
SELECT * FROM features_m1
WHERE ts >= now() - interval '24 hours';
-- Target: < 50ms
-- Atual: 28ms ✅
```

#### Compression Performance

| Métrica | Antes Compressão | Depois Compressão | Redução |
|---------|------------------|-------------------|---------|
| Espaço em Disco | 12.5 GB | 1.1 GB | 91.2% |
| Query Latency (avg) | 45ms | 52ms | +15.6% |
| Write Latency | 3.2ms | 3.8ms | +18.8% |

**Recomendação:** Comprimir dados > 7 dias (current policy)

### Machine Learning

#### Treinamento de Modelos

| Modelo | Dataset Size | Training Time | CPU Usage | RAM Usage |
|--------|--------------|---------------|-----------|-----------|
| Random Forest (100 trees) | 500k samples | 12 min | 90% (4 cores) | 3.2 GB |
| Logistic Regression | 500k samples | 2 min | 60% (1 core) | 1.5 GB |
| LightGBM (200 trees) | 500k samples | 8 min | 85% (4 cores) | 2.8 GB |

**Hardware:** Intel i5-8250U (4 cores), 8GB RAM

#### Inferência (Prediction)

| Modelo | Batch Size | Latência | Throughput |
|--------|------------|----------|------------|
| Random Forest | 1 | 2.5ms | 400 pred/s |
| Random Forest | 100 | 45ms | 2222 pred/s |
| Random Forest | 1000 | 380ms | 2631 pred/s |
| Logistic Regression | 1 | 0.8ms | 1250 pred/s |
| LightGBM | 1 | 1.9ms | 526 pred/s |

**Recomendação:** Usar batch prediction (100-500 samples) para throughput

### Observability Stack

#### Prometheus

| Métrica | Target | Atual |
|---------|--------|-------|
| Scrape Duration | < 500ms | 280ms |
| Query Latency (simple) | < 100ms | 65ms |
| Query Latency (complex) | < 1s | 740ms |
| Storage Size (30d) | < 10GB | 6.2GB |

#### Grafana Dashboards

| Dashboard | Load Time | Queries | Status |
|-----------|-----------|---------|--------|
| MT5 Trading Main | 1.8s | 12 | ✅ |
| Infrastructure & Logs | 2.4s | 18 | ✅ |
| Database Metrics | 1.2s | 8 | ✅ |
| ML/AI Dashboard | 1.5s | 10 | ✅ |

**Target Load Time:** < 3s

#### Loki (Logs)

| Métrica | Target | Atual |
|---------|--------|-------|
| Ingestion Rate | > 1MB/s | 1.8MB/s |
| Query Latency (1h) | < 2s | 1.3s |
| Query Latency (24h) | < 5s | 3.8s |
| Storage Size (30d) | < 50GB | 28GB |

---

## Limites Operacionais

### Capacidade do Sistema

#### Database

```yaml
Max Connections: 200 (PostgreSQL) + 1000 (PgBouncer pool)
Max DB Size: 500 GB (current: 45 GB = 9% utilizado)
Max Table Size (market_data): 100 GB (current: 38 GB)
Max Inserts/sec: 10,000 (current avg: 1,200)
Max Queries/sec: 5,000 (current avg: 450)

# Compression Impact
Compression Ratio: 10:1 (avg)
Decompression Overhead: +15-20% query latency
Compression Delay: 7 days after insertion
```

#### API

```yaml
Max Concurrent Requests: 1000
Max Request Size: 10 MB
Max Response Size: 50 MB
Rate Limit: 1000 req/min por IP (não implementado ainda)
Timeout: 30s
Workers (Uvicorn): 4
```

#### Machine Learning

```yaml
Max Training Dataset: 5M samples (RAM limit)
Max Model Size: 500 MB
Max Concurrent Trainings: 1 (CPU-bound)
Max Inference Batch: 10,000 samples
Model Retention: 30 versions (auto-cleanup)
```

### Resource Limits (Docker)

```yaml
# docker-compose.yml
services:
  db:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          memory: 2G

  api:
    deploy:
      resources:
        limits:
          cpus: '1.5'
          memory: 2G
        reservations:
          memory: 512M

  ml:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          memory: 1G

  prometheus:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
```

### Alertas de Capacidade

Configure alertas no Grafana quando:

```yaml
# CPU
cpu_usage > 80% por 5 minutos

# Memória
memory_usage > 85% por 3 minutos

# Disco
disk_usage > 80%
disk_iops > 5000

# Database
db_connections > 150 (75% do limite)
db_query_duration_p95 > 500ms
db_size > 400GB (80% do limite)

# API
api_latency_p95 > 200ms
api_error_rate > 1%
api_requests_per_sec > 800
```

---

## Otimizações Recomendadas

### Database

#### 1. Índices Eficientes

```sql
-- Índice principal (já implementado)
CREATE INDEX idx_market_data_symbol_timeframe 
ON market_data (symbol, timeframe, ts DESC);

-- Índice para queries de agregação
CREATE INDEX idx_market_data_ts_bucket 
ON market_data (time_bucket('1 hour', ts), symbol);

-- Índice para features lookup
CREATE INDEX idx_features_symbol_ts 
ON features_m1 (symbol, ts_bucket DESC);

-- Remover índices não utilizados
DROP INDEX IF EXISTS idx_market_data_volume;  -- Não usado
```

#### 2. Connection Pooling

```yaml
# PgBouncer config (já implementado)
pool_mode: transaction  # Melhor para múltiplos clientes
max_client_conn: 1000
default_pool_size: 25
reserve_pool_size: 10
reserve_pool_timeout: 5
```

#### 3. Vacuum e Analyze

```bash
# Executar semanalmente
docker exec mt5_db psql -U trader -d mt5_trading -c "VACUUM ANALYZE market_data;"
docker exec mt5_db psql -U trader -d mt5_trading -c "VACUUM ANALYZE features_m1;"

# Adicionar ao cron
0 3 * * 0 docker exec mt5_db psql -U trader -d mt5_trading -c "VACUUM ANALYZE;"
```

#### 4. Partition Maintenance

```sql
-- Verificar chunks (partições)
SELECT * FROM timescaledb_information.chunks
WHERE hypertable_name = 'market_data'
ORDER BY range_start DESC;

-- Drop chunks antigos manualmente (se necessário)
SELECT drop_chunks('market_data', INTERVAL '1 year');
```

### API

#### 1. Async Database Queries

```python
# Usar asyncpg ao invés de psycopg2
import asyncpg

async def get_signals(symbol: str):
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("""
        SELECT * FROM features_m1
        WHERE symbol = $1
        ORDER BY ts_bucket DESC
        LIMIT 100
    """, symbol)
    await conn.close()
    return rows
```

#### 2. Caching

```python
# Redis cache para queries frequentes
import redis
import json

cache = redis.Redis(host='redis', port=6379)

def get_latest_signals(symbol: str):
    key = f"signals:{symbol}:latest"
    cached = cache.get(key)
    
    if cached:
        return json.loads(cached)
    
    # Query DB
    signals = fetch_from_db(symbol)
    
    # Cache por 1 minuto
    cache.setex(key, 60, json.dumps(signals))
    return signals
```

#### 3. Response Compression

```python
# FastAPI middleware para gzip
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

#### 4. Pagination

```python
@app.get("/signals/history")
def get_signals_history(
    symbol: str,
    limit: int = 100,
    offset: int = 0
):
    # Limitar response size
    limit = min(limit, 1000)
    
    signals = query_db(symbol, limit, offset)
    return {
        "data": signals,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": count_total(symbol)
        }
    }
```

### Machine Learning

#### 1. Incremental Learning

```python
# Re-treinar apenas com novos dados
from sklearn.ensemble import RandomForestClassifier

# Carregar modelo existente
model = joblib.load("/models/rf_m1.pkl")

# Partial fit com novos dados (últimas 24h)
new_data = fetch_recent_data(hours=24)
X_new, y_new = prepare_features(new_data)

# Nota: Random Forest não suporta partial_fit
# Alternativa: usar SGDClassifier ou retreinar full
```

#### 2. Feature Caching

```python
# Cachear features computadas
import joblib

def get_or_compute_features(symbol, timeframe):
    cache_key = f"{symbol}_{timeframe}_features"
    cache_path = f"/tmp/{cache_key}.pkl"
    
    if os.path.exists(cache_path):
        # Check se não expirou (1 hora)
        if time.time() - os.path.getmtime(cache_path) < 3600:
            return joblib.load(cache_path)
    
    features = compute_features(symbol, timeframe)
    joblib.dump(features, cache_path)
    return features
```

#### 3. Model Compression

```python
# Reduzir tamanho do modelo (menos árvores)
model = RandomForestClassifier(
    n_estimators=50,  # Ao invés de 100
    max_depth=8,      # Ao invés de 10
)

# Ou usar joblib compression
joblib.dump(model, "/models/rf_m1.pkl", compress=3)
```

### Observability

#### 1. Log Sampling

```python
# Não logar todos os requests, apenas amostra
import random

if random.random() < 0.1:  # 10% dos requests
    logger.info("Request processed", extra={...})
```

#### 2. Metrics Aggregation

```yaml
# Prometheus recording rules (pré-calcular agregações)
# prometheus/rules.yml
groups:
  - name: precomputed
    interval: 30s
    rules:
      - record: api:requests:rate5m
        expr: rate(api_requests_total[5m])
      
      - record: api:latency:p95
        expr: histogram_quantile(0.95, api_request_duration_seconds_bucket)
```

---

## Monitoramento de Performance

### Dashboards Grafana

#### 1. Performance Overview

```
Painel: MT5 Performance
- API Latency P50/P95/P99 (time series)
- Database Query Duration (heatmap)
- ML Training Time (bar chart)
- Resource Usage (CPU, RAM, Disk)
```

#### 2. Alertas Críticos

```yaml
# grafana/provisioning/alerting/performance-alerts.yaml
- alert: HighAPILatency
  expr: api_request_duration_seconds{quantile="0.95"} > 0.2
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "API latency P95 acima de 200ms"

- alert: SlowDatabaseQueries
  expr: pg_stat_statements_mean_time_ms > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Queries lentas detectadas no banco"

- alert: HighCPUUsage
  expr: rate(process_cpu_seconds_total[5m]) > 0.8
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "CPU usage acima de 80%"
```

### Profiling

#### Python (API/ML)

```bash
# cProfile
python -m cProfile -o profile.stats api/app/main.py

# Analisar
python -m pstats profile.stats
>>> sort cumtime
>>> stats 20

# py-spy (live profiling)
py-spy top --pid $(pgrep -f uvicorn)
py-spy record -o profile.svg --pid $(pgrep -f uvicorn)
```

#### Database

```sql
-- Habilitar pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Queries mais lentas
SELECT 
    query,
    calls,
    mean_exec_time,
    max_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;

-- Reset stats
SELECT pg_stat_statements_reset();
```

---

## Troubleshooting

### API Lenta

**Sintomas:**
- Latência P95 > 200ms
- Timeouts frequentes

**Diagnóstico:**
```bash
# Verificar logs
docker logs mt5_api | grep -i "slow"

# Verificar CPU/RAM
docker stats mt5_api

# Verificar conexões DB
docker exec mt5_db psql -U trader -c "SELECT count(*) FROM pg_stat_activity;"
```

**Soluções:**
1. Aumentar workers Uvicorn: `--workers 8`
2. Otimizar queries SQL (adicionar índices)
3. Implementar caching (Redis)
4. Aumentar recursos Docker (`cpus`, `memory`)

### Database Lento

**Sintomas:**
- Queries > 500ms
- Lock waits

**Diagnóstico:**
```sql
-- Queries bloqueadas
SELECT * FROM pg_stat_activity 
WHERE wait_event_type IS NOT NULL;

-- Locks
SELECT * FROM pg_locks WHERE NOT granted;

-- Cache hit ratio
SELECT 
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) AS cache_ratio
FROM pg_statio_user_tables;
-- Target: > 0.99
```

**Soluções:**
1. Aumentar `shared_buffers` no PostgreSQL
2. Vacuum/Analyze
3. Adicionar índices
4. Compression policy

### ML Training Lento

**Sintomas:**
- Treinamento > 30 minutos
- OOM (Out of Memory)

**Diagnóstico:**
```bash
# RAM usage durante treinamento
docker stats mt5_ml

# Tamanho do dataset
docker exec mt5_db psql -U trader -c "SELECT count(*) FROM trainset_m1;"
```

**Soluções:**
1. Reduzir dataset (sample ou time window menor)
2. Reduzir hiperparâmetros (`n_estimators`, `max_depth`)
3. Usar modelo mais simples (Logistic Regression)
4. Aumentar RAM Docker

---

## Recursos Adicionais

- **Documentação**: `docs/DOCUMENTATION.md`
- **Runbook**: `docs/RUNBOOK.md`
- **Troubleshooting**: `docs/DOCUMENTATION.md#troubleshooting`
- **Prometheus Queries**: `prometheus/prometheus.yml`
- **Grafana Dashboards**: `grafana/provisioning/dashboards/`
