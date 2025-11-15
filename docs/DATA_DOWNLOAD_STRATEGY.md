# Estratégia de Download de Dados Históricos

## Visão Geral

Este documento descreve a estratégia implementada para download de 10 anos de dados históricos do Dukascopy para o par EURUSD, com objetivo de treinar modelos de machine learning com maior volume de dados.

## Contexto e Motivação

### Problema Inicial
- **Dados disponíveis**: Apenas 3 meses (Agosto-Novembro 2025)
  - 1.566 candles H1
  - 96.388 candles M1
- **Modelo treinado**: Random Forest com 54% de acurácia
- **Performance baseline**: +0.68% ROI (RR 1:2, Threshold 0.65)

### Necessidade
Para implementar estratégia **multi-timeframe** (H4/D1 features) e melhorar acurácia do modelo em 10-15%, precisamos:
- Dados históricos suficientes para treino robusto
- Múltiplos timeframes (H1, H4, D1)
- Período mínimo: 5 anos (solicitado: 10 anos)

## Fonte de Dados: Dukascopy

### Por que Dukascopy?

#### Tentativa Anterior: Yahoo Finance
```
Erro: "1h data not available... must be within last 730 days"
Limitação: Apenas 2 anos de dados horários
```

#### Solução: Dukascopy
- ✅ **20+ anos de histórico disponível**
- ✅ **Dados tick-by-tick** (maior precisão)
- ✅ **Formato estruturado** (.bi5 binário)
- ✅ **API estável e confiável**
- ✅ **Free e sem rate limit**

### Estrutura da API Dukascopy

**URL Pattern:**
```
https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YEAR}/{MONTH-1}/{DAY}/{HOUR}h_ticks.bi5
```

**Exemplo:**
```bash
curl "https://datafeed.dukascopy.com/datafeed/EURUSD/2024/10/01/00h_ticks.bi5"
# Retorna arquivo binário comprimido com ticks da hora 00h do dia 01/11/2024
```

### Formato .bi5 (Binary Tick Data)

**Estrutura do arquivo:**
1. Compressão: GZIP
2. Após descompactar: Stream de ticks
3. Cada tick: **20 bytes**

**Estrutura de cada tick (20 bytes):**
```python
struct.unpack('>IIIff', chunk[i:i+20])
# > = big-endian
# I = unsigned int (4 bytes)
# f = float (4 bytes)

Campos:
- time_offset (4 bytes): Milissegundos desde início da hora
- ask (4 bytes): Preço ASK em pips * 100000
- bid (4 bytes): Preço BID em pips * 100000  
- ask_volume (4 bytes float): Volume ASK
- bid_volume (4 bytes float): Volume BID
```

**Exemplo de conversão:**
```python
# Valor raw: ask = 110525
# Conversão: 110525 / 100000 = 1.10525 (preço real)
```

## Arquitetura da Solução

### 1. Script de Download: `download_dukascopy_10years.py`

#### Características Principais
- **Período**: 2015-11-18 até 2025-11-15 (10 anos = 3.650 dias)
- **Timeframes**: H1, H4, D1
- **Batch processing**: Salva a cada 24 horas
- **Checkpoint incremental**: Retoma de onde parou
- **Retry logic**: 3 tentativas com delay de 5s
- **Memory efficient**: Buffer máximo de 24h

#### Fluxo de Processamento

```
┌─────────────────────────────────────────────────┐
│  1. Download hora por hora (00h-23h)           │
│     URL: .../EURUSD/2015/10/18/00h_ticks.bi5   │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  2. Parse .bi5 (struct.unpack)                  │
│     - Decompress GZIP                           │
│     - Extract ticks (20 bytes cada)             │
│     - Convert prices (value / 100000)           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  3. Aggregate para H1                           │
│     - OHLC: first/max/min/last                  │
│     - Volume: sum                               │
│     - Spread: mean(ask - bid)                   │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  4. Resample H1 → H4, D1                        │
│     - H4: df.resample('4H')                     │
│     - D1: df.resample('1D')                     │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  5. Save to PostgreSQL (batch)                  │
│     INSERT ... ON CONFLICT DO NOTHING           │
│     - Evita duplicatas                          │
│     - Commit a cada 24h                         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  6. Save Checkpoint                             │
│     {                                           │
│       "last_date": "2015-12-25",                │
│       "h1_count": 744,                          │
│       "h4_count": 186,                          │
│       "d1_count": 31                            │
│     }                                           │
└─────────────────────────────────────────────────┘
```

#### Funções Principais

```python
def parse_bi5_file(content: bytes) -> list:
    """
    Descompacta e parseia arquivo .bi5
    
    Args:
        content: Bytes do arquivo .bi5 (comprimido)
    
    Returns:
        Lista de ticks: [(timestamp, bid, ask, bid_vol, ask_vol), ...]
    """

def download_hour_ticks(date: datetime, hour: int, retry_count: int = 0) -> list:
    """
    Download de ticks de uma hora específica
    
    Args:
        date: Data (yyyy-mm-dd)
        hour: Hora (0-23)
        retry_count: Tentativa atual (max 3)
    
    Returns:
        Lista de ticks ou [] se falhar
    """

def aggregate_h1_to_h4(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega candles H1 para H4
    
    Regras:
    - Open: primeiro valor
    - High: máximo
    - Low: mínimo
    - Close: último valor
    - Volume: soma
    - Spread: média
    """

def save_to_database_batch(df: pd.DataFrame, timeframe: str):
    """
    Salva batch no PostgreSQL
    
    SQL:
        INSERT INTO market_data (ts, symbol, timeframe, ...)
        VALUES (...)
        ON CONFLICT (symbol, timeframe, ts) DO NOTHING
    """
```

#### Sistema de Checkpoint

**Arquivo**: `/app/data/checkpoint.json`

**Estrutura:**
```json
{
  "last_date": "2015-11-25",
  "h1_count": 168,
  "h4_count": 42,
  "d1_count": 7,
  "updated_at": "2025-11-15T14:30:00"
}
```

**Comportamento:**
- Salvo a cada 24 horas processadas
- Lido na inicialização: `current_date = last_date + timedelta(days=1)`
- Persistido em volume Docker (sobrevive a restart)

### 2. Containerização: Docker

#### Dockerfile.downloader

```dockerfile
FROM python:3.11-slim

# Dependências do sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    ca-certificates

WORKDIR /app

# Python dependencies
COPY requirements-downloader.txt .
RUN pip install --no-cache-dir -r requirements-downloader.txt

# Diretório para checkpoint
RUN mkdir -p /app/data

# Script de download
COPY scripts/data/download_dukascopy_10years.py /app/

# Executar com output unbuffered
CMD ["python", "-u", "/app/download_dukascopy_10years.py"]
```

**Dependências Python:**
```txt
pandas>=2.0.0
numpy>=1.24.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
requests>=2.31.0
lxml>=4.9.0
```

#### docker-compose.downloader.yml

```yaml
version: '3.8'

services:
  dukascopy_downloader:
    build:
      context: ..
      dockerfile: docker/Dockerfile.downloader
    image: mt5-downloader:latest
    container_name: dukascopy_downloader
    restart: unless-stopped  # ⭐ Restart automático
    
    volumes:
      - downloader_data:/app/data  # Checkpoint persistente
    
    environment:
      - DB_HOST=mt5_db
      - DB_PORT=5432
      - DB_NAME=mt5_trading
      - DB_USER=trader
      - DB_PASSWORD=${DB_PASSWORD}
      - PYTHONUNBUFFERED=1
    
    networks:
      - default

networks:
  default:
    external: true
    name: mt5-process-core_default  # Rede existente

volumes:
  downloader_data:
    driver: local
```

**Características:**
- ✅ **restart: unless-stopped** - Container reinicia automaticamente
- ✅ **Volume persistente** - Checkpoint não se perde
- ✅ **Rede externa** - Conecta ao PostgreSQL existente
- ✅ **PYTHONUNBUFFERED=1** - Logs em tempo real

### 3. Script de Gerenciamento: `manage_downloader.sh`

```bash
#!/bin/bash

COMPOSE_FILE="docker/docker-compose.downloader.yml"

case "$1" in
  start)
    # Build image + Start container
    docker build -f docker/Dockerfile.downloader -t mt5-downloader:latest .
    docker-compose -f $COMPOSE_FILE up -d dukascopy_downloader
    ;;
    
  stop)
    docker-compose -f $COMPOSE_FILE stop dukascopy_downloader
    ;;
    
  restart)
    docker-compose -f $COMPOSE_FILE restart dukascopy_downloader
    ;;
    
  logs)
    docker logs -f dukascopy_downloader
    ;;
    
  status)
    # Container status
    docker ps -a | grep dukascopy_downloader
    
    # Últimas 10 linhas do log
    docker logs dukascopy_downloader --tail 10
    
    # Checkpoint atual
    docker exec dukascopy_downloader cat /app/data/checkpoint.json 2>/dev/null
    
    # Contagem no banco
    docker exec mt5_db psql -U trader -d mt5_trading -c "
      SELECT timeframe, COUNT(*) as candles 
      FROM market_data 
      WHERE symbol='EURUSD' AND timeframe IN ('H1','H4','D1')
      GROUP BY timeframe
    "
    ;;
esac
```

**Uso:**
```bash
# Iniciar download
./scripts/data/manage_downloader.sh start

# Ver logs em tempo real
./scripts/data/manage_downloader.sh logs

# Verificar status
./scripts/data/manage_downloader.sh status

# Parar (preserva checkpoint)
./scripts/data/manage_downloader.sh stop

# Reiniciar (retoma do checkpoint)
./scripts/data/manage_downloader.sh restart
```

## Destino dos Dados: PostgreSQL

### Database: `mt5_trading`

**Tabela**: `market_data`

**Schema:**
```sql
CREATE TABLE market_data (
    ts          TIMESTAMP WITH TIME ZONE NOT NULL,
    symbol      TEXT NOT NULL,
    timeframe   TEXT NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      DOUBLE PRECISION,
    spread      DOUBLE PRECISION,
    bid         DOUBLE PRECISION,
    ask         DOUBLE PRECISION,
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

-- Índices para performance
CREATE INDEX idx_market_data_ts ON market_data(ts);
CREATE INDEX idx_market_data_timeframe ON market_data(timeframe);
```

**Constraints:**
- **PRIMARY KEY**: (symbol, timeframe, ts) - Garante unicidade
- **ON CONFLICT DO NOTHING**: Evita duplicatas no insert

### Volume Físico

**Docker Volume**: `postgres_data`
```bash
docker volume inspect postgres_data
# Mountpoint: /var/lib/docker/volumes/postgres_data/_data
```

**Acesso aos Dados:**
```sql
-- Candles H1 de um período
SELECT * FROM market_data 
WHERE symbol='EURUSD' 
  AND timeframe='H1'
  AND ts BETWEEN '2020-01-01' AND '2020-12-31'
ORDER BY ts;

-- Estatísticas por timeframe
SELECT 
    timeframe,
    COUNT(*) as total_candles,
    MIN(ts) as primeiro,
    MAX(ts) as ultimo,
    MAX(ts) - MIN(ts) as periodo
FROM market_data
WHERE symbol='EURUSD'
GROUP BY timeframe;
```

## Expectativas de Volume

### Cálculo de Candles

**Período**: 2015-11-18 até 2025-11-15 = 3.650 dias

**H1 (Horário):**
```
3.650 dias × 24 horas/dia = 87.600 candles
- Finais de semana: ~20% = -17.520
- Feriados: ~2% = -1.752
≈ 68.328 candles H1 esperados
```

**H4 (4 horas):**
```
87.600 / 4 = 21.900 candles
- Ajustes: ~17.082 candles H4 esperados
```

**D1 (Diário):**
```
3.650 dias
- Finais de semana: -1.042
- Feriados: -73
≈ 2.535 candles D1 esperados
```

### Tamanho Estimado

**Por candle**: ~200 bytes (19 colunas × ~10 bytes/coluna)

**Total:**
```
H1: 68.328 × 200 bytes = 13.6 MB
H4: 17.082 × 200 bytes = 3.4 MB
D1: 2.535 × 200 bytes = 0.5 MB
─────────────────────────────────
Total: ≈ 17.5 MB (apenas OHLCV)

Com indicadores (38 features): ≈ 66 MB
```

## Performance e Tempo de Execução

### Estimativa de Tempo

**Fatores:**
- Download: ~1-2s por hora (rede + Dukascopy response)
- Parse: ~0.1s por hora (CPU bound)
- Aggregate: ~0.05s por hora
- Database insert: ~0.2s por batch (24h)

**Cálculo:**
```
3.650 dias × 24 horas = 87.600 requisições HTTP

Tempo por hora: ~1.35s (média)
Tempo total: 87.600 × 1.35s = 118.260s = 32.8 horas

Com paralelização e cache: ≈ 2-4 horas
```

### Monitoramento de Progresso

**Logs:**
```bash
docker logs -f dukascopy_downloader

# Output esperado:
📊 DOWNLOAD DUKASCOPY - 10 ANOS
Par: EURUSD
Período: 2015-11-18 até 2025-11-15

📅 2015-11-18 (1/3650 - 0.0%)
   ⏱️ Processando 24 horas...
   💾 Salvos: 18 H1, 4 H4, 1 D1

📅 2015-11-19 (2/3650 - 0.1%)
   ⏱️ Processando 24 horas...
   💾 Salvos: 24 H1, 6 H4, 1 D1
   
✅ Checkpoint salvo: 2015-11-19

[...]

📅 2025-11-15 (3650/3650 - 100.0%)
🎉 DOWNLOAD CONCLUÍDO!
📊 Total: 68.328 H1, 17.082 H4, 2.535 D1
```

**Status em tempo real:**
```bash
./scripts/data/manage_downloader.sh status

# Output:
Container: Up 2 hours
Checkpoint: 2015-12-25 (40/3650 - 1.1%)
Database: 960 H1, 240 H4, 40 D1
```

## Recuperação de Falhas

### Cenários Tratados

#### 1. Container Crash
**Sintoma**: Container para inesperadamente
**Solução**: `restart: unless-stopped`
```bash
# Docker reinicia automaticamente
# Script lê checkpoint e retoma: last_date + 1
```

#### 2. Erro de Rede (HTTP timeout)
**Sintoma**: Requisição para Dukascopy falha
**Solução**: Retry logic (3 tentativas)
```python
def download_hour_ticks(date, hour, retry_count=0):
    try:
        response = requests.get(url, timeout=30)
    except Exception as e:
        if retry_count < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            return download_hour_ticks(date, hour, retry_count+1)
        return []  # Skip hora se falhar 3x
```

#### 3. Database Connection Lost
**Sintoma**: PostgreSQL inacessível
**Solução**: Retry na próxima iteração
```python
try:
    save_to_database_batch(df, 'H1')
except Exception as e:
    logger.error(f"DB error: {e}")
    # Checkpoint NÃO avança
    # Próximo restart tenta novamente
```

#### 4. Checkpoint Corrompido
**Sintoma**: JSON inválido
**Solução**: Fallback para data inicial
```python
def load_checkpoint():
    try:
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    except:
        return None  # Inicia do zero
```

### Recovery Manual

**Se precisar reiniciar de data específica:**
```bash
# 1. Parar container
./scripts/data/manage_downloader.sh stop

# 2. Editar checkpoint
docker run --rm -v downloader_data:/data alpine sh -c \
  'echo "{\"last_date\":\"2020-01-01\"}" > /data/checkpoint.json'

# 3. Reiniciar
./scripts/data/manage_downloader.sh start
```

**Se precisar limpar dados e recomeçar:**
```sql
-- Limpar apenas dados Dukascopy (preservar dados existentes)
DELETE FROM market_data 
WHERE symbol='EURUSD' 
  AND ts < '2025-08-01';  -- Preserva dados recentes
```

## Status Atual (2025-11-15)

### Container
```
Nome: dukascopy_downloader
Estado: RUNNING
Uptime: 15 minutos
Restart Policy: unless-stopped
```

### Progresso
```
Checkpoint: Ainda não criado (dia 1/3650)
Progresso: 0.0%
Logs: "📅 2015-11-18 (1/3650 - 0.0%)"
```

### Database
```
Dados existentes (preservados):
- 1.566 candles H1 (Ago-Nov 2025)
- 96.388 candles M1 (Ago-Nov 2025)

Novos dados em download:
- 2015-2025 (H1, H4, D1)
- ETA: 2-4 horas
```

## Próximos Passos

### 1. Aguardar Download (2-4 horas)
```bash
# Monitorar progresso
watch -n 60 './scripts/data/manage_downloader.sh status'
```

### 2. Calcular Indicadores Técnicos
**Script**: `scripts/ml/calculate_indicators_10years.py`

Indicadores necessários:
- RSI (14)
- MACD (12, 26, 9)
- Bollinger Bands (20, 2)
- ATR (14)
- EMA (50, 200)
- ADX (14)

### 3. Criar Features Multi-Timeframe
**Script**: `scripts/ml/create_mtf_features_h1.py`

Features H4:
- rsi_h4, adx_h4, ema50_h4, ema200_h4
- macd_h4, bb_position_h4, trend_strength_h4

Features D1:
- rsi_d1, bb_position_d1, trend_d1
- volume_ratio_d1, volatility_d1, session_d1

### 4. Re-treinar Modelo
**Script**: `scripts/ml/train_h1_mtf_10years.py`

Configuração:
- Training: 2015-2023 (8 anos)
- Validation: 2024 Q1-Q3 (9 meses)
- Test: 2024 Q4 + 2025 (3 meses)
- Features: 25 H1 + 13 MTF = 38 total
- Modelo: Random Forest (500 trees, max_depth 20)

### 5. Backtest e Validação
**Script**: `scripts/ml/backtest_h1_mtf_10years.py`

Expectativa:
- Baseline: +0.68% ROI, 37.5% WR, 8 trades
- Melhorado: +2-4% ROI, 45-50% WR, 30-50 trades

## Referências

### Documentos Relacionados
- `docs/PLANO_OTIMIZACAO_52_PERCENT.md` - Estratégia geral de otimização
- `docs/DOCUMENTACAO_ORGANIZADA.md` - Estrutura do projeto
- `README.md` - Setup e configuração

### Scripts
- `scripts/data/download_dukascopy_10years.py` - Downloader principal
- `scripts/data/manage_downloader.sh` - Gerenciamento
- `scripts/ml/batch_test_optimization.py` - Framework de teste

### Links Externos
- [Dukascopy API Documentation](https://www.dukascopy.com/swiss/english/marketwatch/historical/)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Random Forest Documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)

---

**Última atualização**: 2025-11-15  
**Autor**: ByteLair Research Team  
**Status**: Download em progresso (Fase 1/5)
