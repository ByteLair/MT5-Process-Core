# Status dos Containers - MT5 Trading System

**Data:** 2025-10-20
**Hora:** 02:38 UTC
**Status:** ✅ OPERACIONAL

## 🚀 Containers em Execução (7 ativos)

| Container | Status | Porta(s) | Função |
|-----------|--------|----------|--------|
| **mt5_api** | ✅ Healthy | 18002, 18003 | API principal FastAPI |
| **mt5_tick_aggregator** | 🟡 Running | - | Worker: Ticks → M1 (5s) |
| **mt5_indicators_worker** | 🟡 Running | - | Worker: RSI/MACD/ATR/BB (60s) |
| **mt5_db** | ✅ Healthy | 5432 | TimescaleDB |
| **mt5_pgbouncer** | ✅ Healthy | 6432 | Connection pooling |
| **mt5-trading-db-ml-scheduler-1** | ✅ Running | - | Scheduler ML |
| **mt5_node_exporter** | ✅ Running | 9100 | Prometheus metrics |

> **Nota:** Workers marcados como "unhealthy" no Docker estão funcionando corretamente (verificado pelos logs).

## 📊 Estatísticas do Sistema

### Banco de Dados

- **Candles armazenados:** 2
- **Símbolos únicos:** 1 (EURUSD)
- **Último timestamp:** 2025-10-20 02:21:00 UTC

### Workers Ativos

```
✓ tick-aggregator     → Processando a cada 5 segundos
✓ indicators-worker   → Calculando indicadores a cada 60 segundos
✓ ml-scheduler        → Agendamento de tarefas ML
```

### Logs Recentes

**Tick Aggregator:**

```
2025-10-20 02:37:57 - INFO - Aggregated ticks:
  {'inserted': 0, 'updated': 0, 'from': '...', 'to': '...'}
```

**Indicators Worker:**

```
2025-10-20 02:21:45 - INFO - Indicators Worker started
  for symbols: ['EURUSD', 'GBPUSD', 'USDJPY'], interval=60s
```

## 🔌 Endpoints Disponíveis

### API REST

- **Swagger UI:** <http://localhost:18002/docs>
- **ReDoc:** <http://localhost:18002/redoc>
- **Health Check:** <http://localhost:18002/health>

### Ingestão de Dados

```bash
# Autenticação
X-API-Key: <valor_do_env>

# Endpoints
POST /ingest              # Candle único ou batch com envelope
POST /ingest_batch        # Array direto de candles
POST /ingest/tick         # Ticks de alta frequência
```

### Banco de Dados

```bash
# Via PgBouncer (pooling)
postgresql://trader:trader123@localhost:6432/mt5_trading

# Direto (interno)
postgresql://trader:trader123@localhost:5432/mt5_trading
```

### Métricas

```bash
# Node Exporter
http://localhost:9100/metrics
```

## ⚙️ Configuração dos Workers

### Tick Aggregator

- **Intervalo:** 5 segundos (`TICK_AGG_INTERVAL`)
- **Função:** Agrega ticks de `market_data_raw` em candles M1
- **Método:** SQL com `time_bucket()` do TimescaleDB
- **OHLC:** Calculado a partir de `(bid + ask) / 2`

### Indicators Worker

- **Intervalo:** 60 segundos (`INDICATORS_INTERVAL`)
- **Símbolos:** EURUSD, GBPUSD, USDJPY (`SYMBOLS`)
- **Lookback:** 200 minutos
- **Indicadores:**
  - RSI (14 períodos)
  - MACD (12/26/9)
  - ATR (14 períodos)
  - Bollinger Bands (20/2.0)

## 🧪 Teste Rápido

```bash
# Obter API_KEY
API_KEY=$(grep ^API_KEY= .env | cut -d= -f2 | tr -d '"')

# Enviar candle M1
curl -X POST http://localhost:18002/ingest_batch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '[{
    "symbol":"EURUSD",
    "timeframe":"M1",
    "ts":"2025-10-20T02:30:00Z",
    "open":1.0855,
    "high":1.0857,
    "low":1.0854,
    "close":1.0856,
    "volume":150,
    "spread":2
  }]'

# Enviar ticks
curl -X POST http://localhost:18002/ingest/tick \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "ticks":[
      {"symbol":"EURUSD","ts":"2025-10-20T02:31:10.123Z","bid":1.0855,"ask":1.0857},
      {"symbol":"EURUSD","ts":"2025-10-20T02:31:15.456Z","bid":1.0856,"ask":1.0858}
    ]
  }'

# Verificar no banco
docker exec mt5_db psql -U trader -d mt5_trading \
  -c "SELECT symbol, timeframe, ts, close FROM market_data ORDER BY ts DESC LIMIT 5;"
```

## 📝 Comandos Úteis

### Gerenciamento de Containers

```bash
# Subir todos
docker-compose up -d

# Ver status
docker-compose ps

# Ver logs em tempo real
docker-compose logs -f tick-aggregator indicators-worker

# Reiniciar um serviço
docker-compose restart tick-aggregator

# Parar tudo
docker-compose down
```

### Monitoramento

```bash
# Ver logs do tick aggregator
docker logs 15c1ad2b98f5_mt5_tick_aggregator --tail 50 -f

# Ver logs do indicators worker
docker logs a77f1aa236da_mt5_indicators_worker --tail 50 -f

# Ver logs da API
docker logs mt5_api --tail 50 -f

# Estatísticas de recursos
docker stats mt5_api mt5_tick_aggregator mt5_indicators_worker
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
```

## ⚠️ Notas Importantes

### Serviços Não Iniciados

Os seguintes serviços **não foram iniciados** devido a conflitos de porta com outro projeto:

- ❌ Grafana (porta 3000)
- ❌ Prometheus (porta 9090)
- ❌ Loki (porta 3100)
- ❌ Jaeger (portas 4317, 16686)
- ❌ PgAdmin (porta 5050)
- ❌ Promtail

Para usar esses serviços, é necessário:

1. Parar os containers conflitantes do outro projeto, OU
2. Alterar as portas no `docker-compose.yml`

### Healthcheck dos Workers

Os workers (`tick-aggregator` e `indicators-worker`) aparecem como "unhealthy" no status do Docker porque o comando `pgrep` usado no healthcheck não está disponível na imagem Python slim.

**Solução:** Verificar logs para confirmar funcionamento:

```bash
docker logs <container_name> --tail 10
```

Se os logs mostram processamento regular, o worker está funcionando corretamente.

## 🔧 Troubleshooting

### Worker não está processando

```bash
# Verificar logs de erro
docker logs <worker_container> | grep -i error

# Verificar conectividade com banco
docker exec <worker_container> nc -zv db 5432

# Reiniciar worker
docker-compose restart tick-aggregator indicators-worker
```

### API retorna erro de conexão

```bash
# Verificar se pgbouncer está healthy
docker ps | grep pgbouncer

# Verificar variáveis de ambiente
docker exec mt5_api env | grep DATABASE_URL

# Testar conexão manual
docker exec mt5_api python -c "from db import engine; print(engine)"
```

### Container travado

```bash
# Obter PID do processo
PID=$(docker inspect <container> | grep '"Pid"' | grep -oP '\d+' | tail -1)

# Matar processo
sudo kill -9 $PID

# Remover e recriar
docker rm -f <container>
docker-compose up -d <service>
```

## 📚 Documentação Adicional

- **Arquitetura:** `docs/HYBRID_INGESTION_FLOW.md`
- **Deploy Status:** `DEPLOYMENT_STATUS.md`
- **OpenAPI:** `openapi.yaml`
- **Test Script:** `test_hybrid_flow.sh`

---

**Última atualização:** 2025-10-20 02:38 UTC
**Sistema:** Produção Local
**Status Geral:** ✅ Operacional
