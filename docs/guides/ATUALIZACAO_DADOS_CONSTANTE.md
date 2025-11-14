# 🔄 Atualização Constante de Dados Forex

## ⚠️ Limitações da Yahoo Finance API

A **yfinance** (Yahoo Finance) tem **restrições severas** para dados intraday:

### 📊 Limites por Timeframe:

| Timeframe | Limite Máximo | Ideal Para |
|-----------|---------------|------------|
| **M1** | 7 dias | ❌ Inviável para 5 anos |
| **M5** | 60 dias | ❌ Limitado |
| **M15** | 60 dias | ❌ Limitado |
| **H1** | 730 dias (2 anos) | ⚠️ Parcial |
| **D1** | Ilimitado | ✅ OK |

### 🚨 Problemas Identificados:

1. **M1 limitado a 7 dias** - Impossível obter 5 anos
2. **Rate limiting** - Muitas requisições bloqueiam IP
3. **Dados incompletos** - Gaps frequentes nos dados
4. **Sem garantia de continuidade** - API pode mudar a qualquer momento
5. **Forex limitado** - Apenas pares principais (EURUSD, GBPUSD, etc)

---

## ✅ Soluções Recomendadas

### 1️⃣ **MetaTrader 5 (MELHOR OPÇÃO)**

**Vantagens:**
- ✅ Dados históricos completos (10+ anos)
- ✅ Atualização em tempo real
- ✅ Todos os timeframes (M1 até MN1)
- ✅ Centenas de símbolos
- ✅ Dados de qualidade institucional
- ✅ Gratuito via brokers

**Como usar:**

```python
import MetaTrader5 as mt5
from datetime import datetime

# Conectar
mt5.initialize()

# Download histórico completo
rates = mt5.copy_rates_range("EURUSD", mt5.TIMEFRAME_M1, 
                             datetime(2020, 1, 1), 
                             datetime(2025, 11, 14))

print(f"Downloaded: {len(rates)} candles")
mt5.shutdown()
```

**Setup:**
```bash
# Instalar MT5
pip install MetaTrader5

# Configurar conexão com broker
# Veja: docs/guides/COLETA_DADOS_HISTORICOS.md
```

---

### 2️⃣ **Dukascopy (Alternativa Gratuita)**

**Vantagens:**
- ✅ Dados desde 2003
- ✅ API HTTP pública
- ✅ Tick data disponível
- ✅ Sem necessidade de conta

**Limitações:**
- ⚠️ Formato proprietário (.bi5)
- ⚠️ Requer parsing complexo
- ⚠️ Rate limiting por IP

**Biblioteca:**
```bash
pip install dukascopy
```

**Exemplo:**
```python
from dukascopy import fetch

# Download M1
df = fetch("EURUSD", 
           start_date="2020-01-01", 
           end_date="2025-11-14",
           timeframe="M1")
```

---

### 3️⃣ **Alpha Vantage (API Comercial)**

**Vantagens:**
- ✅ API REST oficial
- ✅ Dados ajustados
- ✅ Suporte comercial

**Limitações:**
- ⚠️ 5 requisições/minuto (free tier)
- ⚠️ M1 limitado a 30 dias
- 💰 Planos pagos para mais dados

---

## 🔄 Estratégia de Atualização Contínua

### Abordagem Híbrida (RECOMENDADA):

```
┌─────────────────────────────────────────────┐
│   ESTRATÉGIA DE ATUALIZAÇÃO DE DADOS        │
├─────────────────────────────────────────────┤
│                                             │
│  1️⃣ HISTÓRICO (5 anos)                      │
│     ├─ MetaTrader 5 ou Dukascopy           │
│     ├─ Download único inicial              │
│     └─ ~2M candles M1                      │
│                                             │
│  2️⃣ ATUALIZAÇÃO DIÁRIA (últimos 7 dias)    │
│     ├─ Yahoo Finance (grátis)              │
│     ├─ Cron job diário às 00:05            │
│     └─ ~10k candles/dia                    │
│                                             │
│  3️⃣ REAL-TIME (streaming)                  │
│     ├─ WebSocket broker                    │
│     ├─ MT5 tick stream                     │
│     └─ Atualização a cada tick             │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 📝 Scripts de Atualização

### Script 1: Atualização Diária via Yahoo Finance

```python
#!/usr/bin/env python3
"""
Atualização diária dos últimos 7 dias via Yahoo Finance.
Roda como cron job diário.
"""

import yfinance as yf
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

def update_recent_data(symbol="EURUSD", days=7):
    """Atualiza dados dos últimos N dias."""
    
    ticker = yf.Ticker(f"{symbol}=X")
    
    # Download últimos 7 dias (M1)
    df = ticker.history(period=f"{days}d", interval="1m")
    
    if df.empty:
        print(f"⚠️ Sem dados novos")
        return 0
    
    # Conectar ao banco
    engine = create_engine("postgresql://trader:trader123@db:5432/mt5_trading")
    
    inserted = 0
    with engine.begin() as conn:
        for idx, row in df.iterrows():
            try:
                result = conn.execute(
                    text("""
                        INSERT INTO market_data 
                        (ts, symbol, timeframe, open, high, low, close, volume)
                        VALUES (:ts, :symbol, 'M1', :open, :high, :low, :close, :volume)
                        ON CONFLICT (symbol, timeframe, ts) DO UPDATE
                        SET open=EXCLUDED.open, high=EXCLUDED.high, 
                            low=EXCLUDED.low, close=EXCLUDED.close, volume=EXCLUDED.volume
                    """),
                    {
                        "ts": idx,
                        "symbol": symbol,
                        "open": row['Open'],
                        "high": row['High'],
                        "low": row['Low'],
                        "close": row['Close'],
                        "volume": row['Volume']
                    }
                )
                inserted += result.rowcount
            except Exception as e:
                print(f"Erro: {e}")
    
    print(f"✅ {inserted} candles atualizados/inseridos")
    return inserted

if __name__ == "__main__":
    update_recent_data()
```

### Script 2: Cron Job Configuration

```bash
# Adicionar ao crontab
# crontab -e

# Atualizar dados diariamente às 00:05
5 0 * * * /usr/bin/docker exec mt5_api python /app/scripts/update_daily.py >> /var/log/mt5_update.log 2>&1

# Calcular indicadores após atualização (00:10)
10 0 * * * /usr/bin/docker exec mt5_api python /app/scripts/calculate_indicators_recent.py >> /var/log/mt5_indicators.log 2>&1
```

---

## 🚀 Script Completo de Atualização

Vou criar um script otimizado que:
1. Verifica última data no banco
2. Baixa apenas dados novos
3. Evita duplicatas
4. Calcula indicadores automaticamente

**Arquivo:** `scripts/database/update_forex_data.py`

```python
#!/usr/bin/env python3
"""
Atualização automática de dados Forex.
Detecta automaticamente o que está faltando.
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import yfinance as yf
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger(__name__)

DB_URL = "postgresql://trader:trader123@db:5432/mt5_trading"

def get_last_timestamp(symbol: str, timeframe: str) -> datetime:
    """Retorna última timestamp no banco."""
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT MAX(ts) as last_ts 
                FROM market_data 
                WHERE symbol=:symbol AND timeframe=:timeframe
            """),
            {"symbol": symbol, "timeframe": timeframe}
        )
        row = result.fetchone()
        return row[0] if row[0] else datetime(2020, 1, 1)

def download_missing_data(symbol: str, last_ts: datetime) -> pd.DataFrame:
    """Download dados desde última timestamp."""
    
    # Yahoo Finance: máximo 7 dias para M1
    days_missing = (datetime.now() - last_ts).days
    
    if days_missing > 7:
        logger.warning(f"⚠️ {days_missing} dias faltando (Yahoo suporta max 7 dias M1)")
        logger.info("💡 Use MetaTrader 5 para histórico completo")
        days_missing = 7
    
    logger.info(f"📥 Baixando últimos {days_missing} dias...")
    
    ticker = yf.Ticker(f"{symbol}=X")
    df = ticker.history(period=f"{days_missing}d", interval="1m")
    
    if df.empty:
        logger.warning("Sem dados novos")
        return pd.DataFrame()
    
    # Filtrar apenas dados após última timestamp
    df = df[df.index > last_ts]
    
    logger.info(f"✅ {len(df)} novos candles encontrados")
    return df

def insert_new_data(df: pd.DataFrame, symbol: str, timeframe: str) -> int:
    """Insere dados novos no banco."""
    
    if df.empty:
        return 0
    
    engine = create_engine(DB_URL)
    inserted = 0
    
    with engine.begin() as conn:
        for idx, row in df.iterrows():
            try:
                result = conn.execute(
                    text("""
                        INSERT INTO market_data 
                        (ts, symbol, timeframe, open, high, low, close, volume)
                        VALUES (:ts, :symbol, :timeframe, :open, :high, :low, :close, :volume)
                        ON CONFLICT (symbol, timeframe, ts) DO NOTHING
                    """),
                    {
                        "ts": idx,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close']),
                        "volume": float(row['Volume'])
                    }
                )
                inserted += result.rowcount
            except Exception as e:
                logger.error(f"Erro: {e}")
    
    logger.info(f"✅ {inserted} candles inseridos")
    return inserted

def main():
    logger.info("=" * 60)
    logger.info("🔄 ATUALIZAÇÃO AUTOMÁTICA DE DADOS FOREX")
    logger.info("=" * 60)
    
    symbol = "EURUSD"
    timeframe = "M1"
    
    # 1. Verificar última data
    last_ts = get_last_timestamp(symbol, timeframe)
    logger.info(f"📅 Última data no banco: {last_ts}")
    
    days_missing = (datetime.now() - last_ts).days
    logger.info(f"⏱️  Dias faltando: {days_missing}")
    
    if days_missing == 0:
        logger.info("✅ Dados já estão atualizados!")
        return
    
    # 2. Download dados novos
    df = download_missing_data(symbol, last_ts)
    
    if df.empty:
        logger.info("Nada a atualizar")
        return
    
    # 3. Inserir no banco
    inserted = insert_new_data(df, symbol, timeframe)
    
    # 4. Calcular indicadores
    if inserted > 0:
        logger.info("🔢 Calculando indicadores...")
        # TODO: Chamar calculate_indicators apenas para novos dados
    
    logger.info("=" * 60)
    logger.info("✅ ATUALIZAÇÃO CONCLUÍDA")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
```

---

## 📋 Recomendação Final

### Para seu caso (5 anos de M1):

**Solução Ideal:**

1. **Histórico completo**: Use **MetaTrader 5**
   - Download único de 5 anos: ~2M candles
   - Script: `scripts/database/download_historical_mt5.py`

2. **Atualização diária**: Use **Yahoo Finance**
   - Cron job para últimos 7 dias
   - ~10k candles/dia

3. **Real-time (opcional)**: WebSocket do broker
   - Para trading ao vivo
   - Latência < 100ms

**Comando para setup completo:**

```bash
# 1. Download histórico via MT5 (uma vez)
docker exec mt5_api python scripts/database/download_historical_mt5.py \
    --symbol EURUSD --timeframe M1 --years 5

# 2. Configurar atualização diária
crontab -e
# Adicionar: 5 0 * * * /path/to/update_forex_data.py

# 3. Calcular indicadores
docker exec mt5_api python scripts/database/calculate_all_indicators.py EURUSD M1
```

---

## 📊 Comparação de Fontes

| Fonte | M1 Histórico | Atualização | Custo | Qualidade |
|-------|--------------|-------------|-------|-----------|
| **MT5** | ✅ 10+ anos | ✅ Real-time | 🆓 Free | ⭐⭐⭐⭐⭐ |
| **Dukascopy** | ✅ Desde 2003 | ⚠️ Manual | 🆓 Free | ⭐⭐⭐⭐ |
| **Yahoo Finance** | ❌ 7 dias | ✅ Automático | 🆓 Free | ⭐⭐⭐ |
| **Alpha Vantage** | ⚠️ 30 dias | ✅ API | 💰 Paid | ⭐⭐⭐⭐ |

**Veredicto:** Use **MT5 para histórico** + **Yahoo para updates diários**
