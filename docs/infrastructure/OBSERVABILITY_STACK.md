# Sistema de Observabilidade: Loki + Jaeger + Prometheus

## 📋 Índice
- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Loki - Agregação de Logs](#loki---agregação-de-logs)
- [Jaeger - Distributed Tracing](#jaeger---distributed-tracing)
- [Prometheus - Métricas](#prometheus---métricas)
- [Grafana - Visualização](#grafana---visualização)
- [Queries Úteis](#queries-úteis)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## 🎯 Visão Geral

Stack completa de observabilidade para o MT5 Trading System:

| Componente | Função | Porta | URL |
|------------|--------|-------|-----|
| **Loki** | Agregação de logs | 3100 | http://192.168.15.20:3100 |
| **Promtail** | Coleta de logs | 9080 | - |
| **Jaeger** | Distributed tracing | 16686 | http://192.168.15.20:16686 |
| **Prometheus** | Métricas time-series | 9090 | http://192.168.15.20:9090 |
| **Grafana** | Dashboards | 3000 | http://192.168.15.20:3000 |

### Benefícios

✅ **Logs Centralizados**: Todos os logs em um único lugar  
✅ **Correlação**: Traces → Logs → Metrics  
✅ **Performance**: Identificar gargalos com tracing  
✅ **Debugging**: Rastrear requests através de microserviços  
✅ **Alertas**: Notificações proativas de problemas  

---

## 🏗️ Arquitetura

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │
       v
┌─────────────┐     Traces      ┌─────────────┐
│  MT5 API    │ ──────────────> │   Jaeger    │
│  (FastAPI)  │                 │  (Tracing)  │
└──────┬──────┘                 └─────────────┘
       │                                │
       │ Logs                           │
       v                                v
┌─────────────┐                 ┌─────────────┐
│  Promtail   │ ─────────────> │    Loki     │
│ (Collector) │    Logs        │ (Log Aggr.) │
└─────────────┘                 └─────────────┘
       ^                                │
       │                                │
   ┌───┴────┐                           │
   │ Docker │                           │
   │  Logs  │                           │
   └────────┘                           │
                                        v
┌─────────────┐     Metrics     ┌─────────────┐
│ Prometheus  │ <────────────── │  Exporters  │
│  (Metrics)  │                 └─────────────┘
└──────┬──────┘
       │
       v
┌─────────────┐
│   Grafana   │ ◀── Visualização de tudo
└─────────────┘
```

---

## 📝 Loki - Agregação de Logs

### Características

- **Storage**: Filesystem (loki_data volume)
- **Retenção**: 30 dias (720h)
- **Schema**: BoltDB Shipper + Filesystem
- **Port**: 3100

### Configuração

Arquivo: `loki/loki-config.yml`

```yaml
# Principais configurações
limits_config:
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
  max_query_length: 721h
  retention_period: 720h  # 30 dias
```

### Fontes de Logs

#### 1. Docker Containers
```yaml
# Promtail coleta logs de containers via JSON files
- job_name: docker
  __path__: /var/lib/docker/containers/*/*-json.log
```

#### 2. API MT5
```yaml
# Logs da aplicação
- job_name: mt5_api
  __path__: /app/logs/*.log
```

#### 3. Health Checks
```yaml
# Sistema de monitoramento
- job_name: health_checks
  __path__: /app/logs/health-checks/*.log
```

#### 4. PostgreSQL
```yaml
# Logs do banco de dados
- job_name: postgres
  __path__: /var/log/postgresql/*.log
```

### LogQL - Linguagem de Query

#### Queries Básicas

```logql
# Todos os logs
{job=~".+"}

# Logs de um job específico
{job="mt5_api"}

# Logs por nível
{level="ERROR"}
{level="WARNING"}
{level="INFO"}

# Logs de container específico
{container_name="mt5_api"}
```

#### Queries Avançadas

```logql
# Erros na API nos últimos 5 minutos
{job="mt5_api", level="ERROR"} |~ "error|exception|failed"

# Queries SQL lentas (> 1s)
{job="postgres"} |~ "duration: [1-9][0-9]{3,}" | json | duration > 1000

# Requests HTTP com status 5xx
{job="docker", container_name="mt5_api"} | json | status >= 500

# Logs com traceID para correlação
{job="mt5_api"} |~ "traceID=\\w+"

# Taxa de erro por minuto
sum by (job) (rate({level="ERROR"}[1m]))

# Percentual de erros
sum(rate({level="ERROR"}[5m])) / sum(rate({job=~".+"}[5m])) * 100
```

#### Filtros e Parsers

```logql
# Line filter (|=, !=, |~, !~)
{job="mt5_api"} |= "signal" != "health"

# JSON parser
{job="docker"} | json | line_format "{{.log}}"

# Regex parser
{job="mt5_api"} | regexp "(?P<level>\\w+) - (?P<msg>.*)"

# Label filter
{job="mt5_api"} | json | status >= 400
```

### Alertas no Loki

Criar arquivo `loki/rules.yml`:

```yaml
groups:
  - name: mt5_alerts
    interval: 1m
    rules:
      - alert: HighErrorRate
        expr: |
          sum by (job) (rate({level="ERROR"}[5m])) > 0.05
        annotations:
          summary: "Taxa de erro alta em {{ $labels.job }}"
          
      - alert: APIDown
        expr: |
          absent_over_time({job="mt5_api"}[5m])
        annotations:
          summary: "API não está enviando logs"
```

---

## 🔍 Jaeger - Distributed Tracing

### Características

- **Storage**: Badger (local)
- **UI Port**: 16686
- **Collector Ports**: 
  - gRPC: 14250
  - HTTP: 14268
  - OTLP gRPC: 4317
  - OTLP HTTP: 4318

### Instrumentação da API

#### 1. Configuração Automática

Já está configurado em `api/tracing.py` e `api/app/main.py`:

```python
from tracing import setup_tracing, get_tracer

# No startup da aplicação
setup_tracing(app, service_name="mt5-trading-api", service_version="1.0.0")
```

#### 2. Tracing Manual

```python
from tracing import get_tracer, traced, TracedContext

# Usando decorator
@traced("process_signal")
def process_trading_signal(symbol, timeframe):
    # código...
    pass

# Usando context manager
with TracedContext("database_query", {"table": "ohlc_data"}):
    result = db.execute(query)

# Usando tracer diretamente
tracer = get_tracer(__name__)
with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("symbol", "EURUSD")
    # código...
```

#### 3. Adicionar Atributos e Eventos

```python
from opentelemetry import trace
from tracing import add_span_attributes, add_span_event

# Obter span atual
span = trace.get_current_span()

# Adicionar atributos
add_span_attributes(span, 
    user_id=123, 
    symbol="EURUSD",
    timeframe="M1"
)

# Adicionar evento
add_span_event(span, "cache_hit", {"cache_key": "symbols_list"})
```

#### 4. Registrar Exceções

```python
from tracing import record_exception

try:
    # operação que pode falhar
    result = risky_operation()
except Exception as e:
    span = trace.get_current_span()
    record_exception(span, e)
    raise
```

### Configuração de Ambiente

Adicionar ao `.env`:

```bash
# Jaeger Configuration
JAEGER_ENABLED=true
JAEGER_ENDPOINT=http://jaeger:4317
ENVIRONMENT=production
```

### Navegação no Jaeger UI

1. **Search**: http://192.168.15.20:16686/search
   - Filtrar por serviço, operação, tags
   - Buscar traces com erros

2. **Trace View**:
   - Timeline de spans
   - Latência de cada operação
   - Attributes e events

3. **System Architecture**:
   - Grafo de dependências
   - Taxa de chamadas entre serviços

### Queries Úteis no Jaeger

```
# Traces com erros
error=true

# Traces lentos (> 1s)
minDuration=1s

# Por operação específica
operation=GET /signals/latest

# Por tag customizada
http.status_code=500
```

---

## 📊 Prometheus - Métricas

### Métricas Customizadas da API

Já configurado em `api/app/metrics.py`:

```python
from prometheus_client import Counter, Histogram, Gauge

# Contador de requests
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Histograma de latência
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Gauge de conexões ativas
active_connections = Gauge(
    'active_database_connections',
    'Number of active database connections'
)
```

### PromQL - Queries

```promql
# Taxa de requests por segundo
rate(http_requests_total[5m])

# Latência p95
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
)

# Taxa de erro
rate(http_requests_total{status=~"5.."}[5m]) /
rate(http_requests_total[5m])

# CPU dos containers
rate(container_cpu_usage_seconds_total[5m])

# Memória usada
container_memory_usage_bytes / 1024 / 1024
```

---

## 📈 Grafana - Visualização

### Dashboards Disponíveis

1. **MT5 Trading - Logs (Loki)**
   - Logs por job e nível
   - Taxa de logs
   - Painel de erros
   - Logs da API

2. **Health Check System**
   - Status dos componentes
   - Histórico de checks
   - Alertas ativos

3. **Sistema Metrics** (Prometheus)
   - CPU, memória, disco
   - Requests, latência
   - Database performance

### Correlação: Traces → Logs

No Grafana, ao visualizar um trace no Jaeger, você pode:

1. Clicar no botão "Logs" no span
2. Ver logs correlacionados automaticamente no Loki
3. Navegar entre traces e logs fluidamente

Configurado em `grafana/provisioning/datasources/datasources.yml`:

```yaml
- name: Loki
  jsonData:
    derivedFields:
      - datasourceUid: jaeger
        matcherRegex: "traceID=(\\w+)"
        name: TraceID
        url: "$${__value.raw}"
```

---

## 🔧 Queries Úteis

### Loki + Jaeger Integration

```logql
# Logs com traceID (clicável para Jaeger)
{job="mt5_api"} |~ "traceID=\\w+"

# Erros com trace context
{job="mt5_api", level="ERROR"} 
  | json 
  | line_format "{{.message}} [trace={{.traceID}}]"
```

### Troubleshooting Common Issues

#### 1. API Lenta
```logql
# Encontrar requests lentos no log
{job="mt5_api"} 
  | json 
  | duration > 1000 
  | line_format "Slow request: {{.path}} - {{.duration}}ms"
```

Então no Jaeger:
```
minDuration=1s operation=GET /signals/latest
```

#### 2. Erros no Database
```logql
# Logs de erro do PostgreSQL
{job="postgres", level="ERROR"}
  | regexp "ERROR:  (?P<error_msg>.*)"
```

#### 3. Memory Leaks
```promql
# Crescimento de memória
rate(container_memory_usage_bytes{container="mt5_api"}[1h])
```

#### 4. Rate Limiting
```logql
# Requests rejeitados
{job="mt5_api"} |~ "rate limit|too many requests"
  | json
  | __error__ != "JSONParserErr"
```

### Dashboard Queries

#### Painel: API Health Score

```json
{
  "targets": [
    {
      "expr": "100 - (sum(rate({job=\"mt5_api\", level=\"ERROR\"}[5m])) / sum(rate({job=\"mt5_api\"}[5m])) * 100)",
      "legendFormat": "Health %"
    }
  ]
}
```

#### Painel: Top 10 Slow Endpoints

```promql
topk(10, 
  histogram_quantile(0.95,
    sum by (endpoint) (
      rate(http_request_duration_seconds_bucket[5m])
    )
  )
)
```

---

## 🔍 Troubleshooting

### Loki não está recebendo logs

1. **Verificar Promtail**:
```bash
docker logs mt5_promtail
curl http://localhost:9080/metrics
```

2. **Verificar paths dos logs**:
```bash
# Promtail deve ter acesso aos logs
docker exec mt5_promtail ls -la /var/lib/docker/containers/
docker exec mt5_promtail ls -la /app/logs/
```

3. **Testar ingestão manual**:
```bash
curl -H "Content-Type: application/json" \
  -XPOST -s "http://localhost:3100/loki/api/v1/push" \
  --data-raw '{"streams": [{"stream": {"job": "test"}, "values": [["'$(date +%s)000000000'", "test message"]]}]}'
```

### Jaeger não está recebendo traces

1. **Verificar endpoint**:
```bash
# Testar collector
curl http://localhost:14268/api/traces

# Verificar health
curl http://localhost:14269/
```

2. **Verificar variáveis de ambiente da API**:
```bash
docker exec mt5_api env | grep JAEGER
```

3. **Logs da aplicação**:
```bash
docker logs mt5_api | grep -i jaeger
```

### Grafana não mostra dados

1. **Testar datasources**:
```bash
# Loki
curl http://localhost:3100/ready

# Jaeger
curl http://localhost:16686/api/services

# Prometheus
curl http://localhost:9090/-/healthy
```

2. **Verificar no Grafana**: Configuration → Data sources → Test

3. **Verificar queries**: Explore → selecionar datasource → testar query

---

## ✅ Best Practices

### Logging

1. **Structured Logging**: Use JSON format
```python
import logging
import json

logger.info(json.dumps({
    "event": "signal_generated",
    "symbol": "EURUSD",
    "side": "buy",
    "traceID": trace_id
}))
```

2. **Log Levels**:
   - `ERROR`: Erros que requerem atenção
   - `WARNING`: Situações anormais mas recuperáveis
   - `INFO`: Eventos importantes do sistema
   - `DEBUG`: Informações detalhadas para debugging

3. **Incluir TraceID**: Sempre que possível
```python
span = trace.get_current_span()
trace_id = span.get_span_context().trace_id
logger.info(f"Processing request [traceID={trace_id:032x}]")
```

### Tracing

1. **Span Names**: Usar nomes descritivos
```python
# ❌ Ruim
with tracer.start_as_current_span("func1"):

# ✅ Bom
with tracer.start_as_current_span("generate_trading_signal"):
```

2. **Attributes**: Adicionar contexto relevante
```python
span.set_attribute("symbol", symbol)
span.set_attribute("timeframe", timeframe)
span.set_attribute("user_id", user_id)
```

3. **Não exagerar**: Spans muito pequenos (<1ms) criam overhead

### Métricas

1. **Naming Convention**:
   - `<namespace>_<name>_<unit>`
   - Exemplo: `mt5_http_requests_total`

2. **Labels**: Não usar valores de alta cardinalidade
```python
# ❌ Ruim (user_id tem muitos valores)
counter.labels(user_id=123, endpoint="/signals")

# ✅ Bom
counter.labels(endpoint="/signals", method="GET")
```

3. **Histograms**: Definir buckets apropriados
```python
Histogram(
    'http_request_duration_seconds',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)
```

### Retenção de Dados

| Tipo | Retenção Recomendada | Configuração |
|------|---------------------|--------------|
| Logs (Loki) | 30 dias | `retention_period: 720h` |
| Traces (Jaeger) | 7 dias | Configurar no Jaeger |
| Metrics (Prometheus) | 90 dias | `retention.time: 90d` |

### Performance

1. **Sampling de Traces**: Em produção com alto volume
```python
# Configurar sampling ratio (ex: 10%)
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

sampler = TraceIdRatioBased(0.1)
```

2. **Batching**: Loki e Jaeger usam batching por padrão

3. **Rate Limiting**: Configurado no Loki para proteger
```yaml
limits_config:
  ingestion_rate_mb: 10
  ingestion_burst_size_mb: 20
```

---

## 🚀 Getting Started

### 1. Subir os serviços

```bash
cd /home/felipe/mt5-trading-db
docker-compose up -d loki promtail jaeger
docker-compose restart grafana
```

### 2. Verificar status

```bash
# Loki
curl http://localhost:3100/ready

# Promtail
curl http://localhost:9080/metrics

# Jaeger
curl http://localhost:14269/

# Grafana
curl http://localhost:3000/api/health
```

### 3. Acessar interfaces

- **Grafana**: http://192.168.15.20:3000 (admin/admin)
- **Jaeger UI**: http://192.168.15.20:16686
- **Prometheus**: http://192.168.15.20:9090
- **Loki** (API): http://192.168.15.20:3100

### 4. Importar dashboards no Grafana

Os dashboards são provisionados automaticamente em:
- `grafana/dashboards/loki-logs-dashboard.json`
- `grafana/dashboards/health-check-dashboard.json`

### 5. Testar integração

```bash
# Gerar logs
curl http://localhost:8001/health

# Ver logs no Loki
curl -G http://localhost:3100/loki/api/v1/query \
  --data-urlencode 'query={job="docker"}' \
  --data-urlencode 'limit=10'

# Ver traces no Jaeger
curl http://localhost:16686/api/traces?service=mt5-trading-api
```

---

## 📚 Referências

- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [LogQL Syntax](https://grafana.com/docs/loki/latest/logql/)
- [PromQL Examples](https://prometheus.io/docs/prometheus/latest/querying/examples/)

---

**Última atualização**: 2025-10-18  
**Versão**: 1.0.0  
**Autor**: MT5 Trading System Team
