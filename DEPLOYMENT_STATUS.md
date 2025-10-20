# Status do Deploy - Sistema MT5 Trading

**Data:** 20 de Outubro de 2025  
**Status:** ✅ PRODUÇÃO

## 🎯 Sistema Híbrido de Ingestão - ATIVO

### Containers em Produção

```
✓ mt5_api                              (healthy)   - API principal
✓ mt5_tick_aggregator                  (running)   - Agregador de ticks
✓ mt5_indicators_worker                (running)   - Calculador de indicadores
✓ mt5_db                               (healthy)   - TimescaleDB
✓ mt5_pgbouncer                        (healthy)   - Connection pooling
✓ mt5-trading-db-ml-scheduler-1        (running)   - Scheduler ML
✓ mt5_node_exporter                    (running)   - Métricas Prometheus
```

### 🔌 Endpoints Disponíveis

**Base URL:** `http://localhost:18002`

#### Ingestão de Dados

1. **POST /ingest** - Candle único ou batch com envelope
   ```json
   {"items": [{"symbol":"EURUSD", "timeframe":"M1", ...}]}
   ```

2. **POST /ingest_batch** - Array direto de candles
   ```json
   [{"symbol":"EURUSD", "timeframe":"M1", ...}]
   ```

3. **POST /ingest/tick** - Dados tick-by-tick
   ```json
   {"ticks": [{"symbol":"EURUSD", "ts":"...", "bid":1.0850, "ask":1.0852}]}
   ```

**Autenticação:** Header `X-API-Key` (valor em `.env`)

**Resposta Detalhada:** Todos endpoints retornam array `details` com status por item:
```json
{
  "ok": true,
  "received": 3,
  "inserted": 2,
  "duplicates": 1,
  "details": [
    {
      "symbol": "EURUSD",
      "timeframe": "M1",
      "ts_original": "2025-10-20T02:20:00+00:00",
      "ts_bucket": "2025-10-20T02:20:00+00:00",
      "status": "inserted"
    }
  ]
}
```

### ⚙️ Workers Ativos

#### 1. Tick Aggregator
- **Intervalo:** 5 segundos (configurável via `TICK_AGG_INTERVAL`)
- **Função:** Converte ticks de `market_data_raw` em candles M1 em `market_data`
- **Método:** Agregação SQL com `time_bucket` do TimescaleDB
- **OHLC:** Calculado a partir do mid price `(bid + ask) / 2`
- **Logs:** Estruturados com contador de inserted/updated

#### 2. Indicators Worker
- **Intervalo:** 60 segundos (configurável via `INDICATORS_INTERVAL`)
- **Símbolos:** EURUSD, GBPUSD, USDJPY (configurável via `SYMBOLS`)
- **Lookback:** 200 minutos (garantir períodos suficientes)
- **Indicadores Calculados:**
  - RSI (14 períodos)
  - MACD (12/26/9)
  - ATR (14 períodos)
  - Bollinger Bands (20/2.0)
- **Consistência:** Mesmos cálculos em treino e produção

### 💾 Banco de Dados

- **Engine:** TimescaleDB 2.14.2-pg16
- **Tabelas Principais:**
  - `market_data` - Candles OHLC com indicadores técnicos
  - `market_data_raw` - Ticks brutos (JSONB)
  - `aggregator_state` - Estado do agregador
- **Hypertable:** `market_data` particionado por tempo
- **Continuous Aggregates:** SQL criado em `db/init/04-continuous-aggregates.sql`
  - M5, M15, M30, H1, H4, D1 (views materializadas)

### 📊 Fluxo de Dados

```
┌─────────────┐
│   EA (MT5)  │
└──────┬──────┘
       │
       ├─── Candles M1 ──────► POST /ingest_batch ───► market_data
       │                                                      │
       └─── Ticks (alta freq)─► POST /ingest/tick ─► market_data_raw
                                                              │
                                                      ┌───────▼────────┐
                                                      │ tick_aggregator │
                                                      │   (a cada 5s)   │
                                                      └───────┬─────────┘
                                                              │
                                                    Agregar ticks → M1
                                                              │
                                                      ┌───────▼────────────┐
                                                      │ indicators_worker  │
                                                      │   (a cada 60s)     │
                                                      └───────┬────────────┘
                                                              │
                                           Calcular RSI/MACD/ATR/BB → market_data
                                                              │
                                                      ┌───────▼──────────┐
                                                      │ Continuous Aggs  │
                                                      │ M5/M15/M30/...   │
                                                      └──────────────────┘
```

### 🧪 Validação em Produção

**Testes Realizados:**

✅ POST /ingest_batch com candle M1
```bash
curl -X POST http://localhost:18002/ingest_batch \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '[{"symbol":"EURUSD","timeframe":"M1","ts":"2025-10-20T02:20:00Z",...}]'
```
**Resultado:** `{"ok":true,"inserted":1,"details":[{"status":"inserted"}]}`

✅ POST /ingest/tick com 3 ticks
```bash
curl -X POST http://localhost:18002/ingest/tick \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"ticks":[{"symbol":"EURUSD","ts":"...","bid":1.0850,"ask":1.0852}]}'
```
**Resultado:** `{"ok":true,"received":3,"details":[...]}`

✅ Agregação de ticks → M1
**Log:** `Aggregated ticks: {'inserted': 1, 'updated': 0, ...}`

✅ Dados no banco
```sql
SELECT symbol, timeframe, ts, open, high, low, close 
FROM market_data 
WHERE symbol='EURUSD' AND timeframe='M1' 
ORDER BY ts DESC LIMIT 5;
```
**Resultado:** 2 candles encontrados (1 via /ingest_batch, 1 via tick_aggregator)

### 📝 Logging

Todos componentes com logging estruturado:
- **API:** Logs por request com detalhes de ingestão
- **tick_aggregator:** INFO logs a cada execução com contadores
- **indicators_worker:** INFO logs por símbolo processado

**Formato:**
```
2025-10-20 02:20:09,940 - app.tick_aggregator - INFO - Aggregated ticks: {'inserted': 1, 'updated': 0, 'from': '...', 'to': '...'}
```

### 🔧 Configuração

**Variáveis de Ambiente:**
- `DATABASE_URL` - Conexão direta ao PostgreSQL (não pgbouncer)
- `TICK_AGG_INTERVAL` - Intervalo do agregador em segundos (padrão: 5)
- `INDICATORS_INTERVAL` - Intervalo do worker de indicadores (padrão: 60)
- `SYMBOLS` - Lista de símbolos separados por vírgula (padrão: EURUSD,GBPUSD,USDJPY)
- `API_KEY` - Token para autenticação nos endpoints

### 📚 Documentação

- **Fluxo Híbrido:** `docs/HYBRID_INGESTION_FLOW.md`
- **OpenAPI:** `openapi.yaml` (atualizado com novos endpoints)
- **Test Script:** `test_hybrid_flow.sh`

### 🚀 Próximos Passos

1. **Aplicar Continuous Aggregates**
   ```bash
   docker exec mt5_db psql -U trader -d mt5_trading -f /docker-entrypoint-initdb.d/04-continuous-aggregates.sql
   ```

2. **Configurar ML Pipeline** para usar indicadores server-side

3. **Monitorar Performance** dos workers em produção

4. **Configurar Alertas** no Prometheus para falhas de ingestão

### 🐛 Troubleshooting

**Workers marcados como unhealthy:**
- Verificar logs: `docker logs mt5_tick_aggregator`
- Healthcheck usa `pgrep` que pode não estar disponível na imagem
- Se logs mostram processamento, workers estão OK

**Erro "wrong password type":**
- Workers conectam direto no DB, não no pgbouncer
- API também conecta direto no DB
- Verificar `DATABASE_URL` aponta para `@db:5432`

**Containers travados:**
- Obter PID: `docker inspect <container> | grep '"Pid"'`
- Matar processo: `sudo kill -9 <PID>`
- Remover: `docker rm -f <container>`
- Recriar: `docker-compose up -d <service>`

---

**Última Atualização:** 2025-10-20 02:35 UTC  
**Desenvolvedor:** IA + Felipe  
**Ambiente:** Produção Local
