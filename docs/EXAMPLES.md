# MT5 Trading System - Exemplos Práticos

Este documento contém exemplos de código para casos de uso comuns no sistema.

## Índice

1. [Adicionar Novo Símbolo](#adicionar-novo-símbolo)
2. [Criar Novo Modelo ML](#criar-novo-modelo-ml)
3. [Adicionar Novo Endpoint](#adicionar-novo-endpoint)
4. [Criar Dashboard Personalizado](#criar-dashboard-personalizado)
5. [Adicionar Nova Métrica](#adicionar-nova-métrica)
6. [Criar Alerta Customizado](#criar-alerta-customizado)
7. [Adicionar Feature de ML](#adicionar-feature-de-ml)
8. [Integrar Novo Serviço](#integrar-novo-serviço)

---

## Adicionar Novo Símbolo

### 1. Ingerir Dados via API

```python
import requests
from datetime import datetime, timezone

# Dados de exemplo para GBPJPY
data = {
    "symbol": "GBPJPY",
    "timeframe": "M1",
    "candles": [
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "open": 192.450,
            "high": 192.480,
            "low": 192.440,
            "close": 192.470,
            "volume": 1500,
            "spread": 2.5
        }
    ]
}

response = requests.post("http://localhost:8001/ingest", json=data)
print(response.json())
```

### 2. Verificar Dados no Banco

```bash
docker exec -it mt5_db psql -U trader -d mt5_trading -c \
  "SELECT * FROM market_data WHERE symbol='GBPJPY' ORDER BY ts DESC LIMIT 5;"
```

### 3. Gerar Sinais para o Novo Símbolo

```bash
# API automaticamente reconhece novos símbolos
curl "http://localhost:8001/signals?timeframe=M1"
```

---

## Criar Novo Modelo ML

### 1. Criar Script de Treinamento

```python
# ml/worker/train_lgbm.py
import os
import joblib
import pandas as pd
import lightgbm as lgb
from sqlalchemy import create_engine

DB_URL = os.environ["DATABASE_URL"]
MODELS_DIR = os.environ.get("MODELS_DIR", "./models")
os.makedirs(MODELS_DIR, exist_ok=True)
engine = create_engine(DB_URL, pool_pre_ping=True, future=True)

# Buscar dados
df = pd.read_sql("""
    SELECT * FROM public.trainset_m1
    WHERE ts >= now() - interval '60 days'
    ORDER BY ts
""", engine)

if df.empty:
    raise SystemExit("dataset vazio")

# Preparar features
features = [
    "close", "volume", "spread", "rsi", "macd", "macd_signal",
    "macd_hist", "atr", "ma60", "ret_1"
]
X = df[features].fillna(0)
y = (df["fwd_ret_5"] > 0).astype(int)

# Treinar LightGBM
model = lgb.LGBMClassifier(
    n_estimators=200,
    learning_rate=0.05,
    max_depth=7,
    random_state=42
)
model.fit(X, y)

# Salvar modelo
path = os.path.join(MODELS_DIR, "lgbm_m1.pkl")
joblib.dump(model, path)
print(f"Modelo salvo: {path}")

# Avaliar
from sklearn.metrics import accuracy_score, precision_score, recall_score
y_pred = model.predict(X)
print(f"Accuracy: {accuracy_score(y, y_pred):.4f}")
print(f"Precision: {precision_score(y, y_pred):.4f}")
print(f"Recall: {recall_score(y, y_pred):.4f}")
```

### 2. Executar Treinamento

```bash
docker compose exec ml python ml/worker/train_lgbm.py
```

### 3. Usar Novo Modelo na API

```python
# api/predict.py
import joblib
from pathlib import Path

MODELS_DIR = Path("/models")

def get_model(model_name="lgbm_m1"):
    path = MODELS_DIR / f"{model_name}.pkl"
    if not path.exists():
        raise FileNotFoundError(f"Modelo {model_name} não encontrado")

    model = joblib.load(path)
    features = [
        "close", "volume", "spread", "rsi", "macd", "macd_signal",
        "macd_hist", "atr", "ma60", "ret_1"
    ]
    return model, features
```

### 4. Adicionar Testes

```python
# ml/tests/test_lgbm.py
import pytest
import joblib
from pathlib import Path

def test_lgbm_model_exists():
    model_path = Path("ml/models/lgbm_m1.pkl")
    assert model_path.exists()

def test_lgbm_model_predict():
    model = joblib.load("ml/models/lgbm_m1.pkl")
    import numpy as np
    X_test = np.random.rand(10, 10)
    preds = model.predict(X_test)
    assert len(preds) == 10
    assert all(p in [0, 1] for p in preds)
```

---

## Adicionar Novo Endpoint

### 1. Criar Modelo Pydantic

```python
# api/app/models.py
from pydantic import BaseModel
from typing import List

class TradeRequest(BaseModel):
    symbol: str
    action: str  # "BUY" or "SELL"
    lots: float
    sl: float
    tp: float

class TradeResponse(BaseModel):
    order_id: int
    status: str
    message: str
```

### 2. Adicionar Rota

```python
# api/app/main.py
from .models import TradeRequest, TradeResponse

@app.post("/trades", response_model=TradeResponse)
def create_trade(trade: TradeRequest):
    """
    Cria uma nova ordem de trade

    - **symbol**: Par de moedas (ex: EURUSD)
    - **action**: BUY ou SELL
    - **lots**: Volume da ordem
    - **sl**: Stop Loss
    - **tp**: Take Profit
    """
    # Lógica de criação de ordem
    order_id = 12345  # Simulated

    return TradeResponse(
        order_id=order_id,
        status="PENDING",
        message=f"Order created for {trade.symbol}"
    )
```

### 3. Adicionar Testes

```python
# api/tests/test_trades.py
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)

def test_create_trade():
    payload = {
        "symbol": "EURUSD",
        "action": "BUY",
        "lots": 0.1,
        "sl": 1.1000,
        "tp": 1.1100
    }
    response = client.post("/trades", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "order_id" in data
    assert data["status"] == "PENDING"
```

### 4. Documentar

```python
# Adicione docstring detalhada
# FastAPI gera docs automaticamente em /docs
```

---

## Criar Dashboard Personalizado

### 1. Criar JSON do Dashboard

```json
{
  "title": "My Custom Dashboard",
  "uid": "my-custom-dash",
  "panels": [
    {
      "id": 1,
      "title": "Custom Metric",
      "type": "graph",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "my_custom_metric",
          "refId": "A"
        }
      ],
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      }
    }
  ]
}
```

### 2. Salvar e Provisionar

```bash
# Salve em grafana/provisioning/dashboards/
cp my-dashboard.json grafana/provisioning/dashboards/

# Reinicie Grafana
docker compose restart grafana
```

### 3. Verificar

```bash
# Acesse http://localhost:3000
# Dashboard deve aparecer automaticamente
```

---

## Adicionar Nova Métrica

### 1. Instrumentar Código (Python)

```python
# api/app/main.py
from prometheus_client import Counter, Histogram

# Criar métricas
trades_created_total = Counter(
    'trades_created_total',
    'Total de trades criados',
    ['symbol', 'action']
)

trade_processing_time = Histogram(
    'trade_processing_seconds',
    'Tempo de processamento de trades'
)

@app.post("/trades")
@trade_processing_time.time()
def create_trade(trade: TradeRequest):
    # Incrementar contador
    trades_created_total.labels(
        symbol=trade.symbol,
        action=trade.action
    ).inc()

    # Lógica de trade
    return {"status": "ok"}
```

### 2. Adicionar ao Prometheus

```yaml
# prometheus/prometheus.yml (já configurado)
# Métricas da API são coletadas automaticamente em /prometheus
```

### 3. Criar Painel no Grafana

```
Query: rate(trades_created_total[5m])
Legend: {{symbol}} - {{action}}
Visualization: Time series
```

---

## Criar Alerta Customizado

### 1. Definir Regra de Alerta

```yaml
# grafana/provisioning/alerting/custom-alert.yaml
apiVersion: 1
groups:
  - orgId: 1
    name: Custom Alerts
    folder: Alerts
    interval: 1m
    rules:
      - uid: high-trade-volume
        title: High Trade Volume
        condition: C
        data:
          - refId: A
            relativeTimeRange:
              from: 300
              to: 0
            datasourceUid: prometheus
            model:
              expr: sum(rate(trades_created_total[5m])) > 10
              refId: A
        noDataState: NoData
        execErrState: Alerting
        for: 5m
        annotations:
          summary: "Volume de trades muito alto"
          description: "Mais de 10 trades por minuto nos últimos 5 minutos"
        labels:
          severity: warning
```

### 2. Configurar Notificação

```yaml
# grafana/provisioning/alerting/notification-policies.yaml
# Adicione rota para o novo alerta
- receiver: Email-Admin
  object_matchers:
    - ["alertname", "=", "High Trade Volume"]
```

### 3. Testar Alerta

```bash
# Gere trades para disparar o alerta
for i in {1..20}; do
  curl -X POST http://localhost:8001/trades \
    -H "Content-Type: application/json" \
    -d '{"symbol":"EURUSD","action":"BUY","lots":0.1,"sl":1.1,"tp":1.12}'
done
```

---

## Adicionar Feature de ML

### 1. Criar Feature SQL

```sql
-- db/init/02-features.sql
-- Adicionar nova feature: RSI de 21 períodos

CREATE OR REPLACE VIEW features_m1_extended AS
SELECT
    m.ts,
    m.symbol,
    m.timeframe,
    m.close,
    m.volume,
    m.spread,
    -- Features existentes
    ...,
    -- Nova feature: RSI 21
    (SELECT
        100 - (100 / (1 +
            AVG(CASE WHEN close > LAG(close) OVER w THEN close - LAG(close) OVER w ELSE 0 END) OVER (ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) /
            AVG(CASE WHEN close < LAG(close) OVER w THEN LAG(close) OVER w - close ELSE 0 END) OVER (ROWS BETWEEN 20 PRECEDING AND CURRENT ROW)
        ))
    FROM market_data m2
    WHERE m2.symbol = m.symbol
        AND m2.timeframe = m.timeframe
        AND m2.ts <= m.ts
    WINDOW w AS (ORDER BY ts)
    ) AS rsi_21
FROM market_data m;
```

### 2. Atualizar Script de Treinamento

```python
# ml/worker/train.py
features = [
    "close", "volume", "spread", "rsi", "macd", "macd_signal",
    "macd_hist", "atr", "ma60", "ret_1",
    "rsi_21"  # Nova feature
]
X = df[features].fillna(0)
```

### 3. Retreinar Modelo

```bash
docker compose exec ml python ml/worker/train.py
```

---

## Integrar Novo Serviço

### 1. Adicionar ao Docker Compose

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    container_name: mt5_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - mt5_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

volumes:
  redis_data:
```

### 2. Configurar na API

```python
# api/app/main.py
import redis

redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

@app.get("/cache/{key}")
def get_cache(key: str):
    value = redis_client.get(key)
    if value is None:
        return {"error": "Key not found"}
    return {"key": key, "value": value}

@app.post("/cache/{key}")
def set_cache(key: str, value: str):
    redis_client.set(key, value, ex=3600)  # 1 hora
    return {"key": key, "value": value}
```

### 3. Adicionar Métricas

```yaml
# prometheus/prometheus.yml
- job_name: 'redis'
  static_configs:
    - targets: ['redis:6379']
```

### 4. Atualizar Health Check

```bash
# scripts/health-check.sh
# Adicionar verificação do Redis
check_redis() {
    echo -e "\n${BLUE}📦 Checking Redis...${NC}"
    if docker exec mt5_redis redis-cli ping | grep -q "PONG"; then
        echo -e "${GREEN}✓${NC} Redis: OK"
    else
        echo -e "${RED}✗${NC} Redis: FAILED"
    fi
}

# Adicionar ao main
check_redis
```

---

## Dicas e Boas Práticas

### Versionamento de Modelos

```python
# ml/models/manifest.json
{
  "model_name": "rf_m1",
  "version": "2.0.0",
  "created_at": "2025-10-18T10:00:00Z",
  "features": [...],
  "metrics": {...},
  "config": {...}
}
```

### Logging Estruturado

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("Trade created", extra={"symbol": "EURUSD", "order_id": 123})
```

### Testes de Integração

```python
# tests/integration/test_full_flow.py
def test_ingest_to_signal():
    # 1. Ingest data
    response = client.post("/ingest", json=sample_data)
    assert response.status_code == 200

    # 2. Wait for processing
    import time
    time.sleep(2)

    # 3. Get signals
    response = client.get("/signals?timeframe=M1")
    assert response.status_code == 200
    assert len(response.json()) > 0
```

---

## Recursos Adicionais

- **Documentação**: `docs/DOCUMENTATION.md`
- **Diagramas**: `docs/DIAGRAMS.md`
- **Onboarding**: `docs/ONBOARDING.md`
- **API Docs**: <http://localhost:8001/docs>
