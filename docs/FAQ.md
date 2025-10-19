# MT5 Trading System - FAQ

Perguntas frequentes de desenvolvedores e operadores do sistema.

## Índice

- [Geral](#geral)
- [Instalação e Setup](#instalação-e-setup)
- [Development](#development)
- [Database](#database)
- [Machine Learning](#machine-learning)
- [API](#api)
- [Observabilidade](#observabilidade)
- [Troubleshooting](#troubleshooting)
- [Performance](#performance)

---

## Geral

### Q: O que é o MT5 Trading System?

Sistema de trading automatizado que:
1. Ingere dados de mercado (OHLCV) via API REST
2. Calcula features técnicas (RSI, MACD, ATR, etc.)
3. Treina modelos ML para prever direção de mercado
4. Gera sinais de BUY/SELL
5. Monitora performance via Grafana/Prometheus

### Q: Quais timeframes são suportados?

```
M1  = 1 minuto
M5  = 5 minutos
M15 = 15 minutos
M30 = 30 minutos
H1  = 1 hora
H4  = 4 horas
D1  = 1 dia
```

Cada timeframe tem modelo ML separado.

### Q: Quantos símbolos o sistema suporta?

Ilimitado (dentro da capacidade do banco de dados). Atualmente configurado para forex majors:
- EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP, EURJPY, GBPJPY

### Q: O sistema executa trades automaticamente?

**Não.** O sistema apenas:
- Armazena dados de mercado
- Gera sinais (BUY/SELL)
- Fornece predições de modelos ML

A execução de trades deve ser feita por sistema externo (EA do MT5, bot customizado, etc.).

---

## Instalação e Setup

### Q: Quais são os requisitos mínimos de hardware?

```yaml
CPU: 2 cores (4 cores recomendado)
RAM: 4 GB (8 GB recomendado)
Disk: 50 GB SSD
Network: 100 Mbps
OS: Linux (Ubuntu 20.04+, Debian 11+)
```

### Q: Como instalar o sistema pela primeira vez?

```bash
# 1. Clonar repositório
git clone https://github.com/Lysk-dot/mt5-trading-db.git
cd mt5-trading-db

# 2. Configurar variáveis de ambiente
cp .env.example .env
vim .env  # Editar DATABASE_URL, passwords, etc.

# 3. Build e start
docker compose up -d

# 4. Verificar
./scripts/health-check.sh
```

Ver documentação completa: `docs/ONBOARDING.md`

### Q: Preciso instalar Python/Node.js manualmente?

**Não.** Tudo roda em containers Docker. Apenas Docker e Docker Compose são necessários.

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh

# Instalar Docker Compose
sudo apt install docker-compose-plugin
```

### Q: Como configurar alertas de email?

Já configurado! Alertas vão para `kuramopr@gmail.com`.

Para mudar, edite:
```yaml
# grafana/provisioning/alerting/contact-points.yaml
- name: Email-Admin
  settings:
    addresses: seu-email@example.com
```

Depois:
```bash
docker compose restart grafana
```

---

## Development

### Q: Como adicionar um novo endpoint na API?

1. Definir modelo Pydantic:
```python
# api/app/models.py
class MyRequest(BaseModel):
    param1: str
    param2: int
```

2. Criar rota:
```python
# api/app/main.py
@app.post("/my-endpoint")
def my_endpoint(req: MyRequest):
    return {"result": "ok"}
```

3. Adicionar teste:
```python
# api/tests/test_api.py
def test_my_endpoint():
    response = client.post("/my-endpoint", json={...})
    assert response.status_code == 200
```

Ver exemplos completos: `docs/EXAMPLES.md#adicionar-novo-endpoint`

### Q: Como adicionar um novo símbolo?

Basta ingerir dados do novo símbolo via API. O sistema detecta automaticamente.

```python
import requests

requests.post("http://localhost:8001/ingest", json={
    "symbol": "NZDUSD",  # Novo símbolo
    "timeframe": "M1",
    "candles": [...]
})
```

O banco de dados criará registros automaticamente.

### Q: Como rodar testes localmente?

```bash
# Testes da API
docker compose exec api pytest api/tests/ -v

# Testes de ML
docker compose exec ml pytest ml/tests/ -v

# Testes de scripts
pytest scripts/tests/ -v

# Cobertura
docker compose exec api pytest --cov=api api/tests/
```

### Q: Como debug a aplicação?

```bash
# Logs em tempo real
docker compose logs -f api

# Logs de erro apenas
docker compose logs api | grep -i error

# Debug com pdb (Python debugger)
# Adicionar ao código:
import pdb; pdb.set_trace()

# Attachar ao container
docker attach mt5_api
```

---

## Database

### Q: Como acessar o banco de dados?

```bash
# Via psql
docker exec -it mt5_db psql -U trader -d mt5_trading

# Ou via pgAdmin (configurar connection)
Host: localhost
Port: 5432
User: trader
Password: (ver .env)
Database: mt5_trading
```

### Q: Quanto espaço o banco de dados ocupa?

```sql
-- Tamanho total
SELECT pg_size_pretty(pg_database_size('mt5_trading'));

-- Por tabela
SELECT 
    schemaname || '.' || tablename AS table,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

Atualmente: ~45 GB (com 6 meses de dados M1)

### Q: Como fazer backup do banco?

```bash
# Backup manual
docker exec mt5_db pg_dump -U trader -F c mt5_trading > backup.dump

# Backup automatizado (diário às 04:00)
# Já configurado via systemd timer
systemctl status mt5-remote-backup.timer
```

Backups vão para: `100.113.13.126:/backups/mt5-trading/`

### Q: Como restaurar um backup?

```bash
# Parar serviços
docker compose stop api ml

# Restore
docker exec -i mt5_db pg_restore -U trader -d mt5_trading < backup.dump

# Restart
docker compose start api ml
```

Ver procedimento completo: `docs/RUNBOOK.md#restore-de-backup`

### Q: Por que usar TimescaleDB ao invés de PostgreSQL normal?

TimescaleDB oferece:
- **10-100x** melhor performance em queries time-series
- **Compression**: 90%+ redução de storage
- **Continuous Aggregates**: Features pré-calculadas automaticamente
- **Retention Policies**: Limpeza automática de dados antigos

Ver decisão arquitetural: `docs/adr/001-timescaledb.md`

### Q: Como verificar se compression está funcionando?

```sql
-- Verificar chunks comprimidos
SELECT 
    hypertable_name,
    chunk_name,
    compression_status
FROM timescaledb_information.chunks
WHERE hypertable_name = 'market_data'
ORDER BY range_start DESC;

-- Estatísticas de compression
SELECT 
    pg_size_pretty(before_compression_total_bytes) AS uncompressed,
    pg_size_pretty(after_compression_total_bytes) AS compressed,
    pg_size_pretty(before_compression_total_bytes - after_compression_total_bytes) AS saved
FROM timescaledb_information.compression_settings
WHERE hypertable_name = 'market_data';
```

---

## Machine Learning

### Q: Quais modelos ML são usados?

- **Random Forest Classifier** (principal)
- Logistic Regression (baseline)
- LightGBM (experimental)

Ver: `docs/adr/005-random-forest.md`

### Q: Como treinar um novo modelo?

```bash
# Treinamento manual
docker compose exec ml python ml/worker/train.py

# Treinamento automatizado (diário às 04:00)
# Já configurado via systemd timer
```

Modelos salvos em: `ml/models/rf_m1.pkl`

### Q: Como avaliar performance do modelo?

```bash
# Ver métricas salvas
cat ml/models/rf_m1_metrics.json

# Dashboard Grafana
# ML/AI Dashboard: http://localhost:3000/d/mt5-ml-dashboard
```

Métricas esperadas:
- Accuracy > 0.55
- Precision > 0.60
- Recall > 0.50

### Q: Como fazer backtest de um modelo?

```python
from api.backtest import run_backtest

results = run_backtest(
    model_path='/models/rf_m1.pkl',
    symbol='EURUSD',
    timeframe='M1',
    days=30
)

print(results)
# {'total_trades': 150, 'win_rate': 0.62, 'sharpe_ratio': 1.45}
```

### Q: O modelo está performando mal. O que fazer?

**Possíveis causas:**
1. **Data drift**: Mercado mudou
2. **Overfitting**: Modelo decorou dados de treino
3. **Features ruins**: Indicadores não são preditivos

**Soluções:**
```bash
# 1. Re-treinar com dados recentes
docker compose exec ml python ml/worker/train.py

# 2. Testar diferentes hiperparâmetros
# Editar ml/worker/train.py
n_estimators = 150  # Ao invés de 100
max_depth = 12      # Ao invés de 10

# 3. Adicionar novas features
# Ver docs/EXAMPLES.md#adicionar-feature-de-ml

# 4. Rollback para modelo anterior
docker compose exec ml cp /models/backups/rf_m1_v1.0.0.pkl /models/rf_m1.pkl
docker compose restart api
```

### Q: Como adicionar novas features de ML?

1. Adicionar feature ao SQL:
```sql
-- db/init/02-features.sql
ALTER TABLE features_m1 ADD COLUMN new_feature DOUBLE PRECISION;
```

2. Atualizar script de treinamento:
```python
# ml/worker/train.py
features = [
    "close", "volume", "rsi", "macd",
    "new_feature"  # Nova feature
]
```

3. Re-treinar:
```bash
docker compose exec ml python ml/worker/train.py
```

Ver exemplo completo: `docs/EXAMPLES.md#adicionar-feature-de-ml`

---

## API

### Q: Qual a porta da API?

**8001**

- API: http://localhost:8001
- Docs (Swagger): http://localhost:8001/docs
- Metrics (Prometheus): http://localhost:8001/prometheus

### Q: Como ingerir dados de mercado?

```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "timeframe": "M1",
    "candles": [
      {
        "ts": "2025-10-18T10:00:00Z",
        "open": 1.1000,
        "high": 1.1010,
        "low": 1.0995,
        "close": 1.1005,
        "volume": 1500,
        "spread": 2.5
      }
    ]
  }'
```

### Q: Como obter sinais de trading?

```bash
# Últimos sinais de todos os símbolos
curl http://localhost:8001/signals?timeframe=M1

# Sinal de um símbolo específico
curl http://localhost:8001/signals/latest?symbol=EURUSD&timeframe=M1
```

Response:
```json
{
  "symbol": "EURUSD",
  "timeframe": "M1",
  "signal": "BUY",
  "confidence": 0.73,
  "timestamp": "2025-10-18T10:05:00Z"
}
```

### Q: A API está lenta. O que fazer?

Ver: `docs/PERFORMANCE.md#troubleshooting` e `docs/RUNBOOK.md#incidente-api-lenta`

Checklist rápido:
```bash
# 1. Verificar CPU/RAM
docker stats mt5_api

# 2. Verificar logs de erro
docker logs mt5_api | grep -i "error\|timeout"

# 3. Verificar database
docker exec mt5_db psql -U trader -c "SELECT count(*) FROM pg_stat_activity;"

# 4. Restart API
docker compose restart api
```

### Q: Como autenticar na API?

**Atualmente não há autenticação.**

Para adicionar (futuro):
```python
# api/middleware_auth.py
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Security(security)):
    if credentials.credentials != "SECRET_TOKEN":
        raise HTTPException(status_code=401)
```

---

## Observabilidade

### Q: Como acessar Grafana?

**URL:** http://localhost:3000

**Credentials:**
- User: `admin`
- Password: Ver `.env` (variável `GRAFANA_PASSWORD`)

**Dashboards principais:**
- MT5 Trading Main
- Infrastructure & Logs
- Database Metrics
- ML/AI Dashboard

### Q: Como criar um novo dashboard no Grafana?

1. Via UI: http://localhost:3000 → Dashboards → New
2. Via provisioning:
```bash
# Copiar dashboard existente como template
cp grafana/provisioning/dashboards/mt5-trading-main.json \
   grafana/provisioning/dashboards/my-dashboard.json

# Editar
vim grafana/provisioning/dashboards/my-dashboard.json

# Restart Grafana
docker compose restart grafana
```

Ver exemplo: `docs/EXAMPLES.md#criar-dashboard-personalizado`

### Q: Como acessar Prometheus?

**URL:** http://localhost:9090

**Queries úteis:**
```promql
# Requests por segundo
rate(api_requests_total[5m])

# Latência P95
histogram_quantile(0.95, api_request_duration_seconds_bucket)

# Uso de CPU
rate(process_cpu_seconds_total[5m])

# Conexões DB
pg_stat_database_numbackends
```

### Q: Como ver logs centralizados (Loki)?

Via Grafana:
1. Acesse: http://localhost:3000
2. Explore → Loki data source
3. Query:

```logql
# Logs da API
{container="mt5_api"}

# Erros apenas
{container="mt5_api"} |= "ERROR"

# Últimas 1 hora
{container="mt5_api"} [1h]
```

Ou via CLI:
```bash
# LogCLI
docker exec mt5_loki logcli query '{container="mt5_api"}' --limit=100
```

### Q: Como configurar um novo alerta?

1. Criar regra:
```yaml
# grafana/provisioning/alerting/my-alert.yaml
apiVersion: 1
groups:
  - name: My Alerts
    rules:
      - uid: my-alert-id
        title: My Alert
        condition: C
        data:
          - refId: A
            expr: my_metric > 100
```

2. Restart Grafana:
```bash
docker compose restart grafana
```

Ver exemplo completo: `docs/EXAMPLES.md#criar-alerta-customizado`

---

## Troubleshooting

### Q: Container não inicia. Como debug?

```bash
# Ver logs de erro
docker logs mt5_api

# Verificar status
docker ps -a | grep mt5

# Inspecionar container
docker inspect mt5_api

# Tentar start manual
docker start mt5_api

# Se falhar, rebuild
docker compose build api
docker compose up -d api
```

### Q: Banco de dados está cheio (disk full)

```bash
# Ver uso
df -h

# Limpar Docker
docker system prune -af --volumes

# Compress chunks manualmente
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT compress_chunk(i)
FROM show_chunks('market_data') i;
"

# Drop dados antigos (> 1 ano)
docker exec mt5_db psql -U trader -d mt5_trading -c "
SELECT drop_chunks('market_data', older_than => interval '1 year');
"
```

Ver: `docs/RUNBOOK.md#incidente-disk-full`

### Q: GitHub Actions runner está offline

```bash
# Verificar status
systemctl status actions.runner.*.service

# Start manual
sudo systemctl start actions.runner.Lysk-dot-mt5-trading-db.2v4g1.service

# Ver logs
journalctl -u actions.runner.*.service -f
```

Sistema já tem auto-start configurado:
- Boot: `github-runner-start.service`
- Monitoramento: `github-runner-check.timer` (a cada 5 minutos)

### Q: Modelo ML não está sendo carregado na API

```bash
# Verificar se modelo existe
docker exec mt5_ml ls -lh /models/

# Verificar logs da API
docker logs mt5_api | grep -i "model"

# Testar load manual
docker exec mt5_api python -c "
import joblib
model = joblib.load('/models/rf_m1.pkl')
print('Model loaded OK')
"

# Restart API
docker compose restart api
```

### Q: Alertas não estão chegando por email

```bash
# Verificar config
cat grafana/provisioning/alerting/contact-points.yaml

# Testar alerta manualmente
# No Grafana UI: Alerting → Contact Points → Test

# Verificar logs do Grafana
docker logs grafana | grep -i "notif\|alert\|email"

# Verificar se SMTP está configurado
# (atualmente usando email externo do Grafana)
```

---

## Performance

### Q: Qual é a latência esperada da API?

```
P50: < 50ms
P95: < 100ms
P99: < 200ms
```

Ver benchmarks completos: `docs/PERFORMANCE.md#benchmarks-de-performance`

### Q: Quantos requests por segundo a API suporta?

```
Ingestão (/ingest): 1000+ req/s
Consulta (/signals): 500+ req/s
```

Condições: 4 CPU cores, 8GB RAM, 100 workers

### Q: Como otimizar queries lentas no banco?

```sql
-- 1. Identificar queries lentas
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 2. Analisar query plan
EXPLAIN ANALYZE
SELECT * FROM market_data WHERE symbol='EURUSD' AND ts > now() - interval '1 day';

-- 3. Adicionar índice se necessário
CREATE INDEX idx_custom ON market_data (symbol, ts DESC);

-- 4. Vacuum
VACUUM ANALYZE market_data;
```

Ver: `docs/PERFORMANCE.md#otimizações-recomendadas`

### Q: Como reduzir uso de RAM?

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 1G  # Reduzir de 2G

# Reduzir workers Uvicorn
# api/Dockerfile
CMD ["uvicorn", "app.main:app", "--workers", "2"]  # Ao invés de 4
```

---

## Recursos Adicionais

- **Documentação Completa**: `docs/DOCUMENTATION.md`
- **Onboarding (Novos Desenvolvedores)**: `docs/ONBOARDING.md`
- **Exemplos de Código**: `docs/EXAMPLES.md`
- **Glossário**: `docs/GLOSSARY.md`
- **Performance Guidelines**: `docs/PERFORMANCE.md`
- **Runbook Operacional**: `docs/RUNBOOK.md`
- **Architecture Decision Records**: `docs/adr/`
- **OpenAPI Spec**: `openapi.yaml`
- **API Docs (Swagger)**: http://localhost:8001/docs

---

## Ainda tem dúvidas?

- **Email**: kuramopr@gmail.com
- **GitHub Issues**: https://github.com/Lysk-dot/mt5-trading-db/issues
- **Pull Requests**: Contribuições bem-vindas!
