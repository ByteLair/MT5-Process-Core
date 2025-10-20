# ✅ Sistema MT5 Trading - Todos Containers Ativos

**Data:** 2025-10-20 02:42 UTC  
**Status:** 🟢 TODOS OS SERVIÇOS OPERACIONAIS

## 📊 Containers em Execução (13/13)

| # | Container | Status | Função |
|---|-----------|--------|--------|
| 1 | **mt5_api** | ✅ Healthy | API FastAPI principal |
| 2 | **mt5_tick_aggregator** | 🟡 Running | Worker: Ticks → M1 (5s) |
| 3 | **mt5_indicators_worker** | 🟡 Running | Worker: Indicadores (60s) |
| 4 | **mt5_db** | ✅ Healthy | TimescaleDB |
| 5 | **mt5_pgbouncer** | ✅ Healthy | Connection pooling |
| 6 | **mt5-trading-db-ml-scheduler-1** | ✅ Running | Scheduler ML |
| 7 | **mt5_node_exporter** | ✅ Running | Métricas Prometheus |
| 8 | **mt5_prometheus** | ✅ Running | Métricas & alertas |
| 9 | **mt5_grafana** | ✅ Running | Dashboards |
| 10 | **mt5_loki** | ✅ Running | Agregação de logs |
| 11 | **mt5_promtail** | ✅ Running | Coleta de logs |
| 12 | **mt5_jaeger** | ✅ Running | Distributed tracing |
| 13 | **mt5_pgadmin** | ✅ Running | Admin PostgreSQL |

## 🌐 Portas e Acessos

### Aplicação Principal
| Serviço | Porta | URL | Descrição |
|---------|-------|-----|-----------|
| **API** | 18002, 18003 | http://localhost:18002/docs | Swagger UI |
| **API Health** | 18002 | http://localhost:18002/health | Health check |
| **PgBouncer** | 6432 | postgresql://localhost:6432 | Connection pool |

### Monitoramento e Observabilidade
| Serviço | Porta | URL | Descrição |
|---------|-------|-----|-----------|
| **Grafana** | 13000 | http://localhost:13000 | Dashboards (admin/admin) |
| **Prometheus** | 19090 | http://localhost:19090 | Métricas |
| **Jaeger UI** | 26686 | http://localhost:26686 | Traces distribuídos |
| **Loki** | 13100 | http://localhost:13100 | API de logs |
| **Node Exporter** | 9100 | http://localhost:9100/metrics | Métricas do host |
| **PgAdmin** | 5051 | http://localhost:5051 | Admin PostgreSQL |

### Jaeger (Tracing)
| Porta | Protocolo | Descrição |
|-------|-----------|-----------|
| 26686 | HTTP | UI Web |
| 24317 | gRPC | OTLP gRPC |
| 24318 | HTTP | OTLP HTTP |
| 24268 | HTTP | HTTP collector |
| 24250 | gRPC | gRPC collector |
| 26831 | UDP | Jaeger Thrift Compact |
| 26832 | UDP | Jaeger Thrift Binary |
| 25778 | HTTP | Config endpoint |
| 25775 | UDP | Zipkin compatible |
| 29411 | HTTP | Zipkin compatible |

## 🔌 API Endpoints

### Base URL
```
http://localhost:18002
```

### Autenticação
```bash
# Header obrigatório
X-API-Key: <valor_do_.env>
```

### Endpoints de Ingestão

#### 1. POST /ingest
Envia candle único ou batch com envelope
```json
{
  "items": [
    {
      "symbol": "EURUSD",
      "timeframe": "M1",
      "ts": "2025-10-20T02:30:00Z",
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

#### 2. POST /ingest_batch
Envia array direto de candles (mais simples)
```json
[
  {
    "symbol": "EURUSD",
    "timeframe": "M1",
    "ts": "2025-10-20T02:30:00Z",
    "open": 1.0855,
    "high": 1.0857,
    "low": 1.0854,
    "close": 1.0856,
    "volume": 150,
    "spread": 2
  }
]
```

#### 3. POST /ingest/tick
Envia dados tick-by-tick para alta frequência
```json
{
  "ticks": [
    {
      "symbol": "EURUSD",
      "ts": "2025-10-20T02:31:10.123Z",
      "bid": 1.0855,
      "ask": 1.0857
    },
    {
      "symbol": "EURUSD",
      "ts": "2025-10-20T02:31:15.456Z",
      "bid": 1.0856,
      "ask": 1.0858
    }
  ]
}
```

### Resposta com Detalhes
Todos endpoints retornam array `details` com status por item:
```json
{
  "ok": true,
  "received": 2,
  "inserted": 2,
  "duplicates": 0,
  "details": [
    {
      "symbol": "EURUSD",
      "timeframe": "M1",
      "ts_original": "2025-10-20T02:30:00+00:00",
      "ts_bucket": "2025-10-20T02:30:00+00:00",
      "status": "inserted"
    },
    {
      "symbol": "EURUSD",
      "timeframe": "M1",
      "ts_original": "2025-10-20T02:31:00+00:00",
      "ts_bucket": "2025-10-20T02:31:00+00:00",
      "status": "duplicate"
    }
  ]
}
```

## ⚙️ Workers Configuração

### Tick Aggregator
```yaml
Intervalo: 5 segundos (TICK_AGG_INTERVAL)
Fonte: market_data_raw (ticks em JSONB)
Destino: market_data (candles M1)
Método: SQL time_bucket() do TimescaleDB
OHLC: Calculado de (bid + ask) / 2
```

### Indicators Worker
```yaml
Intervalo: 60 segundos (INDICATORS_INTERVAL)
Símbolos: EURUSD, GBPUSD, USDJPY (SYMBOLS)
Lookback: 200 minutos
Indicadores:
  - RSI (14 períodos)
  - MACD (12/26/9)
  - ATR (14 períodos)
  - Bollinger Bands (20/2.0)
```

## 🧪 Teste Rápido

```bash
# 1. Obter API_KEY
API_KEY=$(grep ^API_KEY= .env | cut -d= -f2 | tr -d '"')

# 2. Testar API Health
curl http://localhost:18002/health

# 3. Enviar candle M1
curl -X POST http://localhost:18002/ingest_batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '[{
    "symbol":"EURUSD",
    "timeframe":"M1",
    "ts":"2025-10-20T02:45:00Z",
    "open":1.0860,
    "high":1.0862,
    "low":1.0859,
    "close":1.0861,
    "volume":200,
    "spread":2
  }]'

# 4. Enviar ticks
curl -X POST http://localhost:18002/ingest/tick \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "ticks":[
      {"symbol":"EURUSD","ts":"2025-10-20T02:46:10.123Z","bid":1.0860,"ask":1.0862},
      {"symbol":"EURUSD","ts":"2025-10-20T02:46:15.456Z","bid":1.0861,"ask":1.0863}
    ]
  }'

# 5. Verificar dados no banco
docker exec mt5_db psql -U trader -d mt5_trading \
  -c "SELECT symbol, timeframe, ts, close FROM market_data ORDER BY ts DESC LIMIT 5;"

# 6. Verificar ticks recebidos
docker exec mt5_db psql -U trader -d mt5_trading \
  -c "SELECT symbol, COUNT(*) FROM market_data_raw GROUP BY symbol;"
```

## 📊 Acessar Dashboards

### Grafana
1. Acesse: http://localhost:13000
2. Login: `admin` / `admin`
3. Dashboards disponíveis em "Browse"

### Prometheus
1. Acesse: http://localhost:19090
2. Query exemplos:
   - `up` - status dos serviços
   - `process_cpu_seconds_total` - CPU
   - `process_resident_memory_bytes` - Memória

### Jaeger
1. Acesse: http://localhost:26686
2. Selecione serviço: `mt5-trading-api`
3. Visualize traces das requisições

### PgAdmin
1. Acesse: http://localhost:5051
2. Login: admin@example.com / admin123
3. Adicionar servidor:
   - Host: `db`
   - Port: `5432`
   - User: `trader`
   - Password: `trader123`

## 📝 Comandos Úteis

### Gerenciamento
```bash
# Subir todos
docker-compose up -d

# Ver status
docker-compose ps

# Ver logs
docker-compose logs -f

# Logs de um serviço específico
docker logs mt5_api -f
docker logs mt5_tick_aggregator -f
docker logs mt5_indicators_worker -f

# Reiniciar serviço
docker-compose restart api

# Parar todos
docker-compose down

# Parar e remover volumes
docker-compose down -v
```

### Monitoramento
```bash
# Ver logs dos workers
docker logs 15c1ad2b98f5_mt5_tick_aggregator --tail 50 -f
docker logs a77f1aa236da_mt5_indicators_worker --tail 50 -f

# Estatísticas de recursos
docker stats

# Healthcheck manual
docker exec mt5_api curl -f http://localhost:8001/health

# Verificar conectividade
docker exec mt5_tick_aggregator nc -zv db 5432
```

### Banco de Dados
```bash
# Conectar ao banco
docker exec -it mt5_db psql -U trader -d mt5_trading

# Queries úteis
SELECT COUNT(*) FROM market_data;
SELECT DISTINCT symbol, timeframe FROM market_data;
SELECT * FROM market_data ORDER BY ts DESC LIMIT 10;
SELECT COUNT(*) FROM market_data_raw;

# Verificar indicadores
SELECT symbol, ts, close, rsi, macd 
FROM market_data 
WHERE rsi IS NOT NULL 
ORDER BY ts DESC LIMIT 10;
```

## 🎯 Fluxo de Dados Completo

```
┌─────────────┐
│   EA (MT5)  │
└──────┬──────┘
       │
       ├─── Candles M1 ──────► POST /ingest_batch ───► market_data
       │                                                      │
       │                                              ┌───────▼────────┐
       │                                              │ indicators_worker│
       │                                              │   (60s)         │
       │                                              └───────┬─────────┘
       │                                                      │
       │                                    Calcular RSI/MACD/ATR/BB
       │                                                      │
       └─── Ticks (alta freq)─► POST /ingest/tick ─► market_data_raw
                                                              │
                                                      ┌───────▼────────┐
                                                      │ tick_aggregator │
                                                      │     (5s)        │
                                                      └───────┬─────────┘
                                                              │
                                                    Agregar ticks → M1
                                                              │
                                                              ▼
                                                         market_data
                                                              │
                                                      ┌───────▼──────────┐
                                                      │ Continuous Aggs  │
                                                      │ M5/M15/M30/...   │
                                                      └──────────────────┘
                                                              │
                                                              ▼
                                    ┌──────────────────────────────────────────┐
                                    │    Prometheus (métricas)                 │
                                    │    Loki (logs)                           │
                                    │    Jaeger (traces)                       │
                                    │         │                                │
                                    │         ▼                                │
                                    │    Grafana (visualização)                │
                                    └──────────────────────────────────────────┘
```

## 🔧 Troubleshooting

### Container unhealthy mas funcionando
```bash
# Workers aparecem unhealthy por falta do comando pgrep
# Verificar logs para confirmar funcionamento:
docker logs <container_name> --tail 20

# Se logs mostram processamento, está OK
```

### Porta em uso
```bash
# Ver processos usando a porta
sudo lsof -i :<porta>

# Matar processo específico
sudo kill -9 <PID>

# Ou alterar porta no docker-compose.yml
```

### Worker não processa
```bash
# Verificar conectividade com banco
docker exec <worker> nc -zv db 5432

# Verificar variáveis de ambiente
docker exec <worker> env | grep DATABASE

# Reiniciar worker
docker-compose restart tick-aggregator indicators-worker
```

### Grafana não carrega dashboards
```bash
# Verificar se Prometheus está acessível
curl http://localhost:19090/-/healthy

# Recriar Grafana
docker-compose up -d --force-recreate grafana
```

## 📚 Documentação Adicional

- **Arquitetura Híbrida:** `docs/HYBRID_INGESTION_FLOW.md`
- **Deploy Status:** `DEPLOYMENT_STATUS.md`
- **Status Containers:** `CONTAINERS_STATUS.md`
- **OpenAPI Spec:** `openapi.yaml`
- **Test Script:** `test_hybrid_flow.sh`

## ⚡ Alterações Realizadas

### Portas Modificadas (conflitos resolvidos)
- **PgAdmin:** 5050 → 15050 (depois 5051 devido conflito)
- **Grafana:** 3000 → 13000
- **Prometheus:** 9090 → 19090
- **Loki:** 3100 → 13100
- **Jaeger UI:** 16686 → 26686
- **Jaeger gRPC:** 14250 → 24250
- **Jaeger HTTP:** 14268 → 24268
- **Jaeger OTLP gRPC:** 4317 → 24317
- **Jaeger OTLP HTTP:** 4318 → 24318
- Outras portas Jaeger: faixa 25000-29000

### Conexões Corrigidas
- Workers e API conectam diretamente em `db:5432`
- Removido uso de `pgbouncer` nos workers (evita erro "wrong password type")

---

**Status:** ✅ SISTEMA COMPLETO OPERACIONAL  
**Última Verificação:** 2025-10-20 02:42 UTC  
**Ambiente:** Produção Local  
**Total Containers:** 13/13 ativos 🚀
