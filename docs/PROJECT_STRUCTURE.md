# Estrutura do Projeto MT5-Process-Core

## Visão Geral

Sistema de trading algorítmico baseado em Machine Learning para operar no par EURUSD com dados do MetaTrader 5 e broker XM.

**Objetivo**: Desenvolver estratégia de trading automatizada com ROI positivo consistente usando Random Forest e features multi-timeframe.

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    SISTEMA MT5-PROCESS                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                 │
│  │  Dukascopy   │───▶│  PostgreSQL  │                 │
│  │   Download   │    │  +TimescaleDB│                 │
│  │  (10 anos)   │    │              │                 │
│  └──────────────┘    └──────┬───────┘                 │
│                              │                          │
│                              ▼                          │
│                     ┌─────────────────┐                │
│                     │  Feature Eng.   │                │
│                     │  (MTF H1/H4/D1) │                │
│                     └────────┬────────┘                │
│                              │                          │
│                              ▼                          │
│                     ┌─────────────────┐                │
│                     │  Random Forest  │                │
│                     │   (500 trees)   │                │
│                     └────────┬────────┘                │
│                              │                          │
│                              ▼                          │
│                     ┌─────────────────┐                │
│                     │    Backtest     │                │
│                     │   Engine        │                │
│                     └────────┬────────┘                │
│                              │                          │
│                              ▼                          │
│                     ┌─────────────────┐                │
│                     │   Resultados    │                │
│                     │   ROI, WR, PF   │                │
│                     └─────────────────┘                │
└─────────────────────────────────────────────────────────┘
```

## Estrutura de Diretórios

```
MT5-Process-Core/
├── api/                          # API REST (FastAPI)
│   ├── main.py                   # Endpoints
│   └── models/                   # Pydantic models
│
├── db/                           # Database migrations
│   └── migrations/               # Alembic migrations
│
├── docker/                       # Docker configuration
│   ├── Dockerfile                # Main app image
│   ├── Dockerfile.downloader     # Dukascopy downloader image
│   ├── docker-compose.yml        # Main services
│   └── docker-compose.downloader.yml  # Downloader service
│
├── docs/                         # Documentação
│   ├── README.md                 # Visão geral do projeto
│   ├── DATA_DOWNLOAD_STRATEGY.md # Estratégia de download Dukascopy
│   ├── MULTI_TIMEFRAME_STRATEGY.md # Features multi-timeframe
│   ├── PROJECT_STRUCTURE.md      # Este arquivo
│   └── PLANO_OTIMIZACAO_52_PERCENT.md # Roadmap de otimização
│
├── ml/                           # Machine Learning models
│   ├── models/                   # Modelos treinados (.pkl)
│   │   ├── random_forest_h1_baseline.pkl
│   │   └── random_forest_h1_mtf_10years.pkl
│   ├── features/                 # Feature engineering
│   └── experiments/              # Jupyter notebooks
│
├── scripts/                      # Scripts utilitários
│   ├── data/                     # Download e processamento
│   │   ├── download_dukascopy_10years.py
│   │   ├── manage_downloader.sh
│   │   ├── calculate_indicators_10years.py
│   │   └── create_mtf_features_h1.py
│   │
│   └── ml/                       # Machine Learning
│       ├── train_h1_baseline.py
│       ├── train_h1_mtf_10years.py
│       ├── backtest_h1_conservative.py
│       ├── backtest_h1_mtf_10years.py
│       └── batch_test_optimization.py
│
├── results/                      # Resultados de backtests
│   ├── backtest_baseline_trades.csv
│   ├── backtest_baseline_equity.csv
│   ├── backtest_mtf_trades.csv
│   ├── backtest_mtf_equity.csv
│   └── feature_importance_mtf.csv
│
├── logs/                         # Application logs
│   ├── app.log
│   └── downloader.log
│
├── data/                         # Datasets processados
│   ├── h1_baseline_3months.parquet
│   └── h1_mtf_features_10years.parquet
│
├── sql/                          # SQL scripts
│   ├── create_tables.sql
│   └── queries/
│
├── requirements.txt              # Python dependencies
├── requirements-downloader.txt   # Downloader dependencies
├── requirements-ml.txt           # ML dependencies
├── docker-compose.yml            # Main compose file
└── Makefile                      # Comandos úteis
```

## Componentes Principais

### 1. Database Layer (PostgreSQL + TimescaleDB)

**Container**: `mt5_db`  
**Image**: `timescale/timescaledb:latest-pg14`  
**Port**: 5432

**Principais Tabelas**:

```sql
-- market_data: Dados de candles OHLCV + indicadores
CREATE TABLE market_data (
    ts          TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol      TEXT NOT NULL,
    timeframe   TEXT NOT NULL,  -- 'M1', 'H1', 'H4', 'D1'
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      DOUBLE PRECISION,
    spread      DOUBLE PRECISION,
    bid         DOUBLE PRECISION,
    ask         DOUBLE PRECISION,
    
    -- Indicadores técnicos
    rsi         DOUBLE PRECISION,
    macd        DOUBLE PRECISION,
    macd_signal DOUBLE PRECISION,
    macd_hist   DOUBLE PRECISION,
    atr         DOUBLE PRECISION,
    bb_upper    DOUBLE PRECISION,
    bb_middle   DOUBLE PRECISION,
    bb_lower    DOUBLE PRECISION,
    
    PRIMARY KEY (symbol, timeframe, ts)
);

CREATE INDEX idx_market_data_ts ON market_data(ts);
CREATE INDEX idx_market_data_timeframe ON market_data(timeframe);
```

**Volume de Dados Atual**:
- H1: 1.566 candles (3 meses)
- M1: 96.388 candles (3 meses)
- **Em download**: 10 anos (2015-2025) H1/H4/D1

### 2. Data Download Layer

**Script**: `scripts/data/download_dukascopy_10years.py`  
**Container**: `dukascopy_downloader`  
**Fonte**: Dukascopy (tick data .bi5)

**Características**:
- Download incremental com checkpoint
- Retry logic (3 tentativas)
- Batch processing (24h chunks)
- Restart automático (`restart: unless-stopped`)

**Output**: 
- ~68.000 candles H1
- ~17.000 candles H4
- ~2.500 candles D1

### 3. Feature Engineering Layer

**Scripts**:
1. `calculate_indicators_10years.py` - Calcula RSI, MACD, BB, ATR, etc.
2. `create_mtf_features_h1.py` - Cria dataset com features multi-timeframe

**Pipeline**:
```
market_data (OHLCV)
    ↓ calculate_indicators
market_data (+ RSI, MACD, BB, ATR, EMA, ADX)
    ↓ create_mtf_features
h1_mtf_features_10years.parquet (38 features)
```

**Features**:
- 25 features H1 (baseline)
- 7 features H4 (tendência macro)
- 6 features D1 (contexto diário)
- **Total**: 38 features

### 4. Machine Learning Layer

**Modelo Atual**: Random Forest Classifier

**Arquivos**:
- `scripts/ml/train_h1_baseline.py` - Treino baseline (3 meses)
- `scripts/ml/train_h1_mtf_10years.py` - Treino MTF (10 anos)

**Configuração**:
```python
RandomForestClassifier(
    n_estimators=500,
    max_depth=20,
    min_samples_split=100,
    min_samples_leaf=50,
    max_features='sqrt',
    class_weight='balanced',
    random_state=42,
    n_jobs=-1
)
```

**Classes**:
- 1: BUY (compra prevista rentável)
- 0: NEUTRAL (sem sinal claro)
- -1: SELL (venda prevista rentável)

### 5. Backtest Layer

**Engine**: Custom Python backtest engine

**Scripts**:
- `backtest_h1_conservative.py` - Backtest baseline
- `backtest_h1_mtf_10years.py` - Backtest MTF
- `batch_test_optimization.py` - Otimização de parâmetros

**Características**:
- Simulação realista de spread (1.5 pips)
- Slippage (0.5 pips)
- Comissão 0% (XM)
- Stop Loss e Take Profit ajustáveis
- Gestão de risco por volatilidade

**Métricas Calculadas**:
- ROI (Return on Investment)
- Win Rate
- Profit Factor
- Max Drawdown
- Sharpe Ratio
- Avg Win/Loss

## Fluxo de Trabalho

### Fase 1: Data Collection (ATUAL)

```bash
# 1. Iniciar download Dukascopy
cd /home/lair/MT5-Process-Core
./scripts/data/manage_downloader.sh start

# 2. Monitorar progresso
./scripts/data/manage_downloader.sh status
./scripts/data/manage_downloader.sh logs

# Status: Container rodando, dia 1/3650 (0.0%)
# ETA: 2-4 horas
```

### Fase 2: Feature Engineering (PRÓXIMO)

```bash
# 1. Calcular indicadores técnicos
python scripts/data/calculate_indicators_10years.py

# Output: market_data atualizada com RSI, MACD, BB, ATR, EMA, ADX

# 2. Criar features multi-timeframe
python scripts/data/create_mtf_features_h1.py

# Output: data/h1_mtf_features_10years.parquet (38 features)
```

### Fase 3: Model Training

```bash
# 1. Treinar modelo MTF
python scripts/ml/train_h1_mtf_10years.py

# Output:
# - models/random_forest_h1_mtf_10years.pkl
# - models/feature_importance_mtf.csv

# 2. Validar acurácia
# Train: 2015-2023 (80%)
# Val: 2024 Q1-Q3 (15%)
# Test: 2024 Q4 + 2025 (5%)
```

### Fase 4: Backtesting

```bash
# 1. Executar backtest
python scripts/ml/backtest_h1_mtf_10years.py

# Output:
# - results/backtest_mtf_trades.csv
# - results/backtest_mtf_equity.csv
# - results/backtest_mtf_summary.csv

# 2. Analisar resultados
# Comparar com baseline: +0.68% ROI
# Meta: +2-4% ROI, 45-50% WR
```

### Fase 5: Optimization

```bash
# 1. Grid search de parâmetros
python scripts/ml/batch_test_optimization.py

# Testa combinações de:
# - Risk/Reward Ratio (1:1, 1:1.5, 1:2, 1:2.5)
# - Threshold (0.55, 0.60, 0.65, 0.70)

# 2. Selecionar melhor configuração
# Critério: Maior ROI com Max DD < 5%
```

## Tecnologias Utilizadas

### Core Stack

- **Python 3.11**: Linguagem principal
- **PostgreSQL 14**: Database relacional
- **TimescaleDB**: Extensão para time-series
- **Docker & Docker Compose**: Containerização
- **Pandas**: Manipulação de dados
- **Scikit-learn**: Machine Learning
- **TA-Lib**: Indicadores técnicos

### ML Stack

- **Random Forest**: Modelo principal
- **XGBoost**: Alternativa (a testar)
- **LightGBM**: Alternativa (a testar)
- **Joblib**: Serialização de modelos
- **NumPy**: Computação numérica

### Data Processing

- **SQLAlchemy**: ORM
- **psycopg2**: Driver PostgreSQL
- **Requests**: HTTP client (Dukascopy)
- **struct**: Parsing binário (.bi5)
- **gzip**: Descompressão

### Monitoring & Logging

- **Grafana**: Dashboards
- **Prometheus**: Métricas
- **Python logging**: Application logs

## Configurações Importantes

### Database Connection

```python
# Connection string
DATABASE_URL = "postgresql://trader:password@mt5_db:5432/mt5_trading"

# SQLAlchemy engine
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL)
```

### Broker Configuration (XM)

```python
BROKER_CONFIG = {
    'spread': 1.5,      # pips (EURUSD)
    'slippage': 0.5,    # pips
    'commission': 0.0,  # 0% (XM Raw Spread)
    'leverage': 100,    # 1:100
    'margin': 0.01,     # 1% margin
}
```

### Model Configuration

```python
MODEL_CONFIG = {
    'n_estimators': 500,
    'max_depth': 20,
    'min_samples_split': 100,
    'min_samples_leaf': 50,
    'max_features': 'sqrt',
    'class_weight': 'balanced',
    'random_state': 42,
}
```

### Backtest Configuration

```python
BACKTEST_CONFIG = {
    'initial_balance': 10000,
    'lot_size': 1.0,            # 1 lote = $10/pip
    'risk_per_trade': 0.02,     # 2% do capital
    'max_trades': 5,            # Máx simultâneos
    'threshold': 0.65,          # Probabilidade mínima
    'stop_loss': 20,            # pips base
    'take_profit': 40,          # pips base (RR 1:2)
}
```

## Comandos Úteis

### Docker

```bash
# Build imagem downloader
docker build -f docker/Dockerfile.downloader -t mt5-downloader:latest .

# Start serviços principais
docker-compose up -d

# Start downloader
docker-compose -f docker/docker-compose.downloader.yml up -d

# Logs
docker logs -f dukascopy_downloader
docker logs -f mt5_db

# Status
docker ps -a | grep mt5
```

### Database

```bash
# Conectar ao PostgreSQL
docker exec -it mt5_db psql -U trader -d mt5_trading

# Queries úteis
SELECT timeframe, COUNT(*) FROM market_data 
WHERE symbol='EURUSD' 
GROUP BY timeframe;

SELECT MIN(ts), MAX(ts), MAX(ts) - MIN(ts) as periodo 
FROM market_data 
WHERE timeframe='H1';

# Backup
docker exec mt5_db pg_dump -U trader mt5_trading > backup.sql

# Restore
cat backup.sql | docker exec -i mt5_db psql -U trader -d mt5_trading
```

### Machine Learning

```bash
# Treinar modelo
python scripts/ml/train_h1_mtf_10years.py

# Backtest
python scripts/ml/backtest_h1_mtf_10years.py

# Otimização
python scripts/ml/batch_test_optimization.py

# Jupyter notebook (análise)
jupyter notebook ml/experiments/
```

### Makefile

```bash
# Instalar dependências
make install

# Executar testes
make test

# Limpar dados temporários
make clean

# Build all
make build

# Deploy
make deploy
```

## Métricas de Performance

### Baseline (3 meses, H1 only)

```
Modelo: Random Forest (300 trees, 25 features)
Período: Outubro-Novembro 2025 (1.5 meses)
─────────────────────────────────────────────
Acurácia:       54.0%
ROI:            +0.68%
Win Rate:       37.5%
Profit Factor:  1.15
Total Trades:   8
Max Drawdown:   ~5%
```

### Target MTF (10 anos, H1+H4+D1)

```
Modelo: Random Forest (500 trees, 38 features)
Período: 2024-Q4 + 2025 (3 meses test)
─────────────────────────────────────────────
Acurácia:       62-68% (target)
ROI:            +2-4% (target)
Win Rate:       45-50% (target)
Profit Factor:  1.5-2.0 (target)
Total Trades:   30-50 (target)
Max Drawdown:   <5% (target)
```

## Status do Projeto

### ✅ Concluído

1. **Setup Inicial**
   - PostgreSQL + TimescaleDB configurado
   - Docker compose funcionando
   - Estrutura de diretórios criada

2. **Modelo Baseline**
   - Random Forest treinado (3 meses)
   - Backtest baseline executado
   - Sistema rentável encontrado (+0.68% ROI)

3. **Otimização de Parâmetros**
   - Batch testing (10 configurações)
   - Melhor config: RR 1:2 + Threshold 0.65

4. **Estratégia Multi-Timeframe**
   - Documentação completa
   - 38 features definidas
   - Pipeline de implementação planejado

5. **Download de Dados**
   - Dukascopy downloader containerizado
   - Sistema de checkpoint funcional
   - Restart automático configurado

### ⏳ Em Progresso

1. **Download 10 Anos Dukascopy**
   - Status: Dia 1/3650 (0.0%)
   - Container: dukascopy_downloader RUNNING
   - ETA: 2-4 horas

### 📋 Próximos Passos

1. **Feature Engineering** (após download)
   - Calcular indicadores H1/H4/D1
   - Criar dataset MTF (38 features)
   - Validar qualidade dos dados

2. **Model Training**
   - Treinar Random Forest MTF
   - Validação cruzada temporal
   - Feature importance analysis

3. **Backtesting**
   - Executar backtest MTF
   - Comparar com baseline
   - Otimizar hiperparâmetros

4. **Production Ready**
   - API REST para sinais
   - Monitoring com Grafana
   - Alertas de performance
   - Paper trading (6 meses)

## Referências

### Documentação Interna
- [Data Download Strategy](DATA_DOWNLOAD_STRATEGY.md)
- [Multi-Timeframe Strategy](MULTI_TIMEFRAME_STRATEGY.md)
- [Plano de Otimização 52%](PLANO_OTIMIZACAO_52_PERCENT.md)

### Links Externos
- [Dukascopy API](https://www.dukascopy.com/swiss/english/marketwatch/historical/)
- [TimescaleDB Docs](https://docs.timescale.com/)
- [Scikit-learn Random Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- [TA-Lib Documentation](https://mrjbq7.github.io/ta-lib/)

### Research Papers
- "Random Forests for Time Series Forecasting" (Breiman, 2001)
- "Multi-Timeframe Analysis in Forex Trading" (Murphy, 1999)
- "Machine Learning for Algorithmic Trading" (Lopez de Prado, 2018)

---

**Última atualização**: 2025-11-15  
**Autor**: ByteLair Research Team  
**Status**: Fase 1 (Data Collection) em progresso  
**Versão**: 1.0
