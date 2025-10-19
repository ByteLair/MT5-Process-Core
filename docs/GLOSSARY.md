# MT5 Trading System - Glossário

Termos técnicos e de negócio utilizados no sistema.

## Índice

- [Trading e Finanças](#trading-e-finanças)
- [Indicadores Técnicos](#indicadores-técnicos)
- [Machine Learning](#machine-learning)
- [Infraestrutura](#infraestrutura)
- [Database](#database)
- [Observabilidade](#observabilidade)

---

## Trading e Finanças

### Ask
Preço de venda (seller's price). O preço pelo qual um trader pode COMPRAR um ativo.

### Bid
Preço de compra (buyer's price). O preço pelo qual um trader pode VENDER um ativo.

### Candle / Candlestick
Representação visual de movimento de preço em um período específico. Contém:
- **Open**: Preço de abertura
- **High**: Maior preço do período
- **Low**: Menor preço do período
- **Close**: Preço de fechamento

### Drawdown
Queda percentual do valor de uma conta desde seu pico máximo até o ponto mais baixo. Mede o risco downside.

```
Drawdown = (Peak Value - Trough Value) / Peak Value × 100%
```

### Equity
Valor total da conta incluindo posições abertas (realized + unrealized P&L).

### Leverage / Alavancagem
Multiplicador que permite controlar posições maiores que o capital disponível.

```
Exemplo: Leverage 1:100
Capital: $1,000
Posição máxima: $100,000
```

### Long Position
Posição de COMPRA. Lucro quando o preço sobe.

### Lot
Unidade de volume de negociação.
- **Standard Lot**: 100,000 unidades da moeda base
- **Mini Lot**: 10,000 unidades
- **Micro Lot**: 1,000 unidades

```python
# Exemplo: EURUSD
1 lot = 100,000 EUR
0.1 lot = 10,000 EUR
0.01 lot = 1,000 EUR (micro lot)
```

### OHLCV
**Open, High, Low, Close, Volume** - Dados básicos de uma candle.

### Pip
**Point in Percentage** - Menor unidade de mudança de preço em forex.

```
EURUSD: 1 pip = 0.0001
USDJPY: 1 pip = 0.01
```

### Short Position
Posição de VENDA. Lucro quando o preço cai.

### Slippage
Diferença entre preço esperado e preço executado de uma ordem.

```
Ordem: Comprar EURUSD @ 1.1000
Executado: 1.1002
Slippage: +2 pips
```

### Spread
Diferença entre Ask e Bid.

```
Ask: 1.1003
Bid: 1.1000
Spread: 3 pips
```

Custo implícito de uma operação.

### Stop Loss (SL)
Ordem automática para fechar posição com prejuízo limitado.

```python
# Long position EURUSD @ 1.1000
stop_loss = 1.0950  # Perda máxima: 50 pips
```

### Take Profit (TP)
Ordem automática para fechar posição com lucro garantido.

```python
# Long position EURUSD @ 1.1000
take_profit = 1.1100  # Ganho: 100 pips
```

### Timeframe
Período de tempo de cada candle.

```
M1  = 1 minuto
M5  = 5 minutos
M15 = 15 minutos
M30 = 30 minutos
H1  = 1 hora
H4  = 4 horas
D1  = 1 dia
W1  = 1 semana
MN  = 1 mês
```

### Tick
Mudança individual de preço. Dados mais granulares que candles.

---

## Indicadores Técnicos

### ATR (Average True Range)
Mede volatilidade do mercado. Quanto maior o ATR, maior a volatilidade.

```python
# Cálculo simplificado
true_range = max(high - low, abs(high - close_prev), abs(low - close_prev))
atr = moving_average(true_range, period=14)
```

**Uso:** 
- Stop loss dinâmico: `SL = entry_price - (2 * ATR)`
- Position sizing baseado em volatilidade

### Bollinger Bands
Bandas de volatilidade baseadas em desvio padrão.

```python
middle_band = SMA(close, 20)
upper_band = middle_band + (2 * std_dev)
lower_band = middle_band - (2 * std_dev)
```

**Interpretação:**
- Preço na upper band: Possivelmente sobrecomprado
- Preço na lower band: Possivelmente sobrevendido
- Bandas estreitas: Baixa volatilidade (possível breakout)

### EMA (Exponential Moving Average)
Média móvel que dá mais peso aos preços recentes.

```python
ema_today = (close_today * multiplier) + (ema_yesterday * (1 - multiplier))
# multiplier = 2 / (period + 1)
```

### MACD (Moving Average Convergence Divergence)
Indicador de momentum baseado em médias móveis.

```python
macd_line = EMA(close, 12) - EMA(close, 26)
signal_line = EMA(macd_line, 9)
histogram = macd_line - signal_line
```

**Sinais:**
- MACD cruza acima da signal: Sinal de COMPRA
- MACD cruza abaixo da signal: Sinal de VENDA
- Divergência: Momentum fraco (possível reversão)

### RSI (Relative Strength Index)
Oscilador de momentum (0-100).

```python
rsi = 100 - (100 / (1 + RS))
# RS = Average Gain / Average Loss (14 períodos)
```

**Interpretação:**
- RSI > 70: Sobrecomprado (possível venda)
- RSI < 30: Sobrevendido (possível compra)
- RSI = 50: Equilíbrio

### SMA (Simple Moving Average)
Média aritmética dos preços em N períodos.

```python
sma = sum(close[-n:]) / n
```

**Uso:**
- Identificar tendência (preço acima SMA = uptrend)
- Suporte/resistência dinâmica

### Stochastic Oscillator
Mede momentum comparando preço de fechamento com range do período.

```python
%K = (close - lowest_low) / (highest_high - lowest_low) × 100
%D = SMA(%K, 3)
```

**Interpretação:**
- > 80: Sobrecomprado
- < 20: Sobrevendido

---

## Machine Learning

### Accuracy
Percentual de predições corretas.

```python
accuracy = (TP + TN) / (TP + TN + FP + FN)
```

### Backtest
Teste de estratégia usando dados históricos para avaliar performance.

```python
# Exemplo
initial_balance = 10000
for signal in historical_signals:
    if signal == "BUY":
        execute_trade()
    balance = calculate_pnl()
```

### Confusion Matrix
Matriz que mostra TP, FP, TN, FN.

```
                 Predicted
              BUY      SELL
Actual BUY    TP       FN
       SELL   FP       TN
```

### Data Drift
Mudança na distribuição dos dados ao longo do tempo. Causa degradação do modelo.

```python
# Exemplo
train_data: Mean=0.5, Std=0.2 (2024)
test_data:  Mean=0.7, Std=0.3 (2025)
# Drift detectado!
```

### Feature Engineering
Processo de criar novas features a partir de dados brutos.

```python
# Exemplo
df['ret_1'] = df['close'].pct_change(1)  # Retorno 1 período
df['volatility_10'] = df['close'].rolling(10).std()  # Volatilidade
```

### F1 Score
Média harmônica entre Precision e Recall.

```python
f1 = 2 * (precision * recall) / (precision + recall)
```

### Label / Target
Variável que o modelo tenta prever.

```python
# Classificação binária (direção)
y = (df['fwd_ret_5'] > 0).astype(int)
# 1 = BUY, 0 = SELL
```

### Overfitting
Modelo "memoriza" dados de treino mas falha em generalizar para novos dados.

```
Train accuracy: 99%  ← Suspeito!
Test accuracy: 55%
```

**Mitigação:**
- Regularização (max_depth, min_samples_leaf)
- Cross-validation
- Mais dados de treino

### Precision
Percentual de predições positivas que estavam corretas.

```python
precision = TP / (TP + FP)
```

**Interpretação:** Dos trades que o modelo sugeriu BUY, quantos foram lucrativos?

### Recall
Percentual de casos positivos que foram detectados.

```python
recall = TP / (TP + FN)
```

**Interpretação:** De todos os trades lucrativos possíveis, quantos o modelo identificou?

### Time-Series Split
Cross-validation respeitando ordem temporal dos dados.

```
Fold 1: Train [1-100] | Test [101-150]
Fold 2: Train [1-150] | Test [151-200]
Fold 3: Train [1-200] | Test [201-250]
```

---

## Infraestrutura

### Blue-Green Deployment
Estratégia de deploy com zero downtime.

```
Blue (old): v1.0 ← Traffic
Green (new): v1.1 ← Testing

Switch:
Blue: v1.0
Green: v1.1 ← Traffic (switchover)

Rollback:
Blue: v1.0 ← Traffic (switch back)
Green: v1.1
```

### Container
Unidade isolada de software (Docker).

```bash
docker run -d --name my_api -p 8000:8000 api:latest
```

### Docker Compose
Orquestrador de múltiplos containers.

```yaml
services:
  db:
    image: postgres
  api:
    depends_on:
      - db
```

### Healthcheck
Verificação automática de saúde de um serviço.

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Load Balancer
Distribui tráfego entre múltiplas instâncias de um serviço.

### Volume
Storage persistente para containers.

```bash
docker volume create db_data
docker run -v db_data:/var/lib/postgresql/data postgres
```

---

## Database

### Connection Pool
Pool de conexões reutilizáveis para evitar overhead de criar conexões.

```
PgBouncer: 1000 client connections → 25 database connections
```

### Continuous Aggregate
View materializada incremental (TimescaleDB).

```sql
CREATE MATERIALIZED VIEW features_m1
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 minute', ts), symbol, avg(close)
FROM market_data
GROUP BY 1, 2;
```

### Compression
Redução de espaço em disco comprimindo chunks antigos.

```sql
ALTER TABLE market_data SET (timescaledb.compress);
SELECT add_compression_policy('market_data', INTERVAL '7 days');
```

**Resultado:** 90%+ redução de storage, +15% query latency.

### Hypertable
Tabela particionada automaticamente por tempo (TimescaleDB).

```sql
CREATE TABLE market_data (...);
SELECT create_hypertable('market_data', 'ts');
```

Internamente cria múltiplos chunks (partições).

### Index
Estrutura de dados para acelerar queries.

```sql
CREATE INDEX idx_symbol_ts ON market_data (symbol, ts DESC);

-- Query usa o índice:
SELECT * FROM market_data WHERE symbol='EURUSD' ORDER BY ts DESC LIMIT 100;
```

### Partition / Chunk
Subdivisão de uma hypertable por intervalo de tempo.

```
Chunk 1: 2025-10-01 to 2025-10-07
Chunk 2: 2025-10-08 to 2025-10-14
Chunk 3: 2025-10-15 to 2025-10-21
```

### Retention Policy
Regra para deletar dados antigos automaticamente.

```sql
SELECT add_retention_policy('market_data', INTERVAL '1 year');
```

### VACUUM
Operação de limpeza para recuperar espaço de dead tuples.

```sql
VACUUM ANALYZE market_data;
```

---

## Observabilidade

### Alert
Notificação automática quando métrica cruza threshold.

```yaml
alert: HighAPILatency
expr: api_latency_p95 > 0.2
for: 5m
```

### Dashboard
Interface visual de métricas (Grafana).

### Log
Registro de eventos do sistema.

```python
logger.info("Order created", extra={"order_id": 123, "symbol": "EURUSD"})
```

### Metric
Medida quantitativa de um aspecto do sistema.

```
Tipos:
- Counter: Valor incremental (requests_total)
- Gauge: Valor que sobe/desce (cpu_usage)
- Histogram: Distribuição de valores (latency)
```

### Prometheus
Sistema de monitoramento baseado em time-series metrics.

```
Scrape ← Targets (API, DB) @ 15s intervals
Store → TSDB
Query ← PromQL
```

### PromQL
Linguagem de query do Prometheus.

```promql
# Requests por segundo (últimos 5 minutos)
rate(api_requests_total[5m])

# Latência P95
histogram_quantile(0.95, api_request_duration_seconds_bucket)

# Alertas ativos
ALERTS{alertstate="firing"}
```

### SLI (Service Level Indicator)
Métrica quantitativa de performance de um serviço.

```
Exemplos:
- Latency P95 < 200ms
- Availability > 99.9%
- Error rate < 0.1%
```

### SLO (Service Level Objective)
Target/objetivo para um SLI.

```
SLO: 99.9% uptime
= Max downtime: 43 minutes/month
```

### Trace
Rastreamento de uma request através de múltiplos serviços (Jaeger).

```
Client → API → PgBouncer → DB
   |       |        |         |
   └───────┴────────┴─────────┘
         Single Trace
```

### Uptime
Percentual de tempo que o sistema está operacional.

```
Uptime = (Total Time - Downtime) / Total Time × 100%
```

---

## Abreviações Comuns

```
ADR  = Architecture Decision Record
API  = Application Programming Interface
ATR  = Average True Range
CPU  = Central Processing Unit
DB   = Database
DR   = Disaster Recovery
EMA  = Exponential Moving Average
ETL  = Extract, Transform, Load
HTTP = Hypertext Transfer Protocol
JSON = JavaScript Object Notation
K8s  = Kubernetes
MACD = Moving Average Convergence Divergence
ML   = Machine Learning
ORM  = Object-Relational Mapping
P&L  = Profit & Loss
P50  = 50th Percentile (Median)
P95  = 95th Percentile
P99  = 99th Percentile
RAM  = Random Access Memory
RCA  = Root Cause Analysis
REST = Representational State Transfer
RPO  = Recovery Point Objective
RSI  = Relative Strength Index
RTO  = Recovery Time Objective
SL   = Stop Loss
SLA  = Service Level Agreement
SLI  = Service Level Indicator
SLO  = Service Level Objective
SMA  = Simple Moving Average
SQL  = Structured Query Language
SSH  = Secure Shell
TP   = Take Profit
TSDB = Time-Series Database
UI   = User Interface
UUID = Universally Unique Identifier
YAML = YAML Ain't Markup Language
```

---

## Recursos Adicionais

- **Documentação Técnica**: `docs/DOCUMENTATION.md`
- **Exemplos de Código**: `docs/EXAMPLES.md`
- **Performance Guidelines**: `docs/PERFORMANCE.md`
- **Runbook Operacional**: `docs/RUNBOOK.md`
