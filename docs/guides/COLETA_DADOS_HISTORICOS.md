# 📊 Guia Completo: Coleta de Dados Históricos

**Data:** 14 de Novembro de 2025  
**Objetivo:** Baixar dados históricos completos do mercado Forex

---

## 🎯 Opções Disponíveis

### 1. MetaTrader 5 (Recomendado) ⭐

**Script:** `scripts/database/download_historical_mt5.py`

#### Instalação

```bash
# 1. Instalar MetaTrader 5 Python API
pip install MetaTrader5 pandas psycopg sqlalchemy

# 2. Instalar e executar o MetaTrader 5
# Download: https://www.metatrader5.com/pt/download
# Fazer login com conta demo ou real
```

#### Uso Básico

```bash
# Download EURUSD H1 dos últimos 10 anos
python scripts/database/download_historical_mt5.py \
    --symbol EURUSD \
    --timeframe H1 \
    --years 10

# Download com datas específicas
python scripts/database/download_historical_mt5.py \
    --symbol EURUSD \
    --timeframe H1 \
    --start 2010-01-01 \
    --end 2025-11-14

# Múltiplos símbolos
python scripts/database/download_historical_mt5.py \
    --symbols EURUSD,GBPUSD,USDJPY,AUDUSD \
    --timeframe H1 \
    --years 5

# Salvar também em CSV
python scripts/database/download_historical_mt5.py \
    --symbol EURUSD \
    --timeframe M15 \
    --years 3 \
    --save-csv \
    --csv-dir ./exports
```

#### Timeframes Disponíveis

- `M1` - 1 minuto
- `M5` - 5 minutos
- `M15` - 15 minutos
- `M30` - 30 minutos
- `H1` - 1 hora ⭐
- `H4` - 4 horas
- `D1` - 1 dia
- `W1` - 1 semana
- `MN1` - 1 mês

#### Vantagens

✅ **Gratuito**  
✅ **Dados oficiais das corretoras**  
✅ **Alta qualidade** (sem gaps artificiais)  
✅ **Até 15+ anos disponíveis**  
✅ **Múltiplos timeframes**  
✅ **Importação automática no banco**  

#### Limitações

⚠️ Requer MT5 instalado e rodando  
⚠️ Disponibilidade depende da corretora  

---

### 2. Yahoo Finance (Alternativa Simples)

**Uso Rápido:**

```python
import yfinance as yf

# Download histórico
ticker = yf.Ticker("EURUSD=X")
df = ticker.history(
    start="2010-01-01",
    end="2025-11-14",
    interval="1h"  # 1m, 5m, 15m, 1h, 1d
)

# Salvar CSV
df.to_csv("eurusd_yahoo.csv")
```

**Vantagens:**  
✅ Simples, sem setup  
✅ Múltiplos ativos (Forex, Stocks, Crypto)  

**Limitações:**  
⚠️ Dados podem ter gaps  
⚠️ Menor histórico (1-5 anos)  
⚠️ Rate limits  

---

### 3. Dukascopy (Tick Level Data)

**Website:** https://www.dukascopy.com/swiss/english/marketwatch/historical/

**Características:**
- ✅ Dados desde 2003
- ✅ Tick level (máxima resolução)
- ✅ Gratuito
- ✅ Download via web ou API

**Como usar:**
1. Acessar o site
2. Selecionar símbolo e período
3. Download do arquivo .bi5
4. Converter para CSV usando ferramenta deles

---

### 4. APIs Profissionais

#### Alpha Vantage

```python
import requests

API_KEY = "YOUR_KEY"  # Free: https://www.alphavantage.co/support/#api-key

url = "https://www.alphavantage.co/query"
params = {
    "function": "FX_DAILY",
    "from_symbol": "EUR",
    "to_symbol": "USD",
    "apikey": API_KEY,
    "outputsize": "full"  # Últimos 20 anos
}

response = requests.get(url, params=params)
data = response.json()
```

**Limites Free:**
- 5 requests/minuto
- 500 requests/dia

#### Twelvedata

```bash
pip install twelvedata

# Python
from twelvedata import TDClient

td = TDClient(apikey="YOUR_KEY")
df = td.time_series(
    symbol="EUR/USD",
    interval="1h",
    outputsize=5000,
    timezone="UTC",
).as_pandas()
```

**Limites Free:**
- 800 requests/dia
- Até 8 anos de histórico

---

## 🚀 Recomendação para Seu Projeto

### Opção 1: MetaTrader 5 (Ideal)

**Por quê:**
1. ✅ Dados de qualidade institucional
2. ✅ Mesma fonte que você usará em produção
3. ✅ Integração perfeita com seu EA
4. ✅ Gratuito e ilimitado
5. ✅ Já temos o script pronto!

**Passo a Passo:**

```bash
# 1. Instalar MT5
# Download: https://www.metatrader5.com/pt/download
# Fazer login com conta demo

# 2. Instalar dependências Python
pip install MetaTrader5

# 3. Baixar dados históricos completos
python scripts/database/download_historical_mt5.py \
    --symbols EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,NZDUSD,EURGBP,EURJPY \
    --timeframe H1 \
    --years 10 \
    --save-csv

# 4. Verificar no banco
docker exec mt5_db psql -U trader -d mt5_trading -c \
    "SELECT symbol, timeframe, COUNT(*), MIN(ts), MAX(ts) 
     FROM market_data 
     GROUP BY symbol, timeframe;"

# 5. Calcular indicadores
python scripts/database/calculate_all_indicators.py
```

**Resultado Esperado:**
- EURUSD H1: ~87,600 candles (10 anos)
- GBPUSD H1: ~87,600 candles
- Total: ~700k candles (8 símbolos x 10 anos)

---

### Opção 2: Híbrida (Backup)

Se MT5 não estiver disponível:

1. **Yahoo Finance** para dados recentes (1-2 anos)
2. **Dukascopy** para dados antigos (backfill)
3. **MT5** quando disponível para dados futuros

---

## 📊 Exemplo Completo: 10 Anos de Dados

```bash
# 1. Download via MT5
python scripts/database/download_historical_mt5.py \
    --symbol EURUSD \
    --timeframe H1 \
    --start 2015-01-01 \
    --end 2025-11-14

# Saída esperada:
# ✅ 87,600 candles baixados
# ✅ 87,600 registros inseridos
# 📊 Período: 2015-01-01 até 2025-11-14

# 2. Calcular indicadores
docker exec -it mt5_api python /tmp/calculate_all_indicators.py

# 3. Verificar
docker exec mt5_db psql -U trader -d mt5_trading -c \
    "SELECT 
        COUNT(*) as total,
        COUNT(rsi) as with_indicators,
        MIN(ts) as first,
        MAX(ts) as last
     FROM market_data 
     WHERE symbol = 'EURUSD' AND timeframe = 'H1';"
```

---

## 🎯 Símbolos Recomendados para Trading

### Majors (Alta Liquidez)
- EURUSD ⭐
- GBPUSD
- USDJPY
- AUDUSD
- USDCAD
- NZDUSD
- USDCHF

### Crosses
- EURGBP
- EURJPY
- GBPJPY
- AUDNZD

### Commodities
- XAUUSD (Ouro)
- XAGUSD (Prata)
- USOIL (Petróleo)

---

## 📈 Volumes de Dados Esperados

| Timeframe | 1 Ano | 5 Anos | 10 Anos |
|-----------|-------|--------|---------|
| M1 | 525k | 2.6M | 5.2M |
| M5 | 105k | 525k | 1.0M |
| M15 | 35k | 175k | 350k |
| H1 | 8.7k | 44k | 87k |
| H4 | 2.2k | 11k | 22k |
| D1 | 365 | 1.8k | 3.6k |

**Recomendação:** H1 é ideal para:
- ✅ Backtesting robusto
- ✅ ML training com volume adequado
- ✅ Performance aceitável
- ✅ 10 anos = ~87k candles por símbolo

---

## 🔧 Troubleshooting

### "MT5 não inicializa"
```bash
# Verificar se MT5 está rodando
ps aux | grep terminal64

# Reinstalar MT5 Python API
pip uninstall MetaTrader5
pip install MetaTrader5
```

### "Símbolo não encontrado"
```python
# Listar símbolos disponíveis
import MetaTrader5 as mt5
mt5.initialize()
symbols = mt5.symbols_get()
for s in symbols:
    print(s.name)
```

### "Erro de conexão com banco"
```bash
# Verificar se containers estão rodando
docker ps | grep mt5

# Testar conexão
docker exec mt5_db psql -U trader -d mt5_trading -c "SELECT 1;"
```

---

## 🎉 Próximos Passos

Após baixar os dados históricos:

1. ✅ **Calcular Indicadores**
   ```bash
   python scripts/database/calculate_all_indicators.py
   ```

2. ✅ **Executar Testes**
   ```bash
   docker exec mt5_api pytest -v
   ```

3. ✅ **Treinar Modelos ML**
   ```bash
   python ml/train_informer_advanced.py
   ```

4. ✅ **Backtest Estratégias**
   ```python
   # Usar dados históricos para validar estratégias
   ```

---

## 📚 Recursos Adicionais

- **MT5 Python Docs:** https://www.mql5.com/en/docs/python_metatrader5
- **Yahoo Finance:** https://github.com/ranaroussi/yfinance
- **Dukascopy:** https://www.dukascopy.com/swiss/english/marketwatch/historical/
- **Alpha Vantage:** https://www.alphavantage.co/documentation/

---

**Quer que eu execute o download de dados históricos completos agora?**

Posso baixar:
- EURUSD H1 dos últimos 10 anos (~87k candles)
- Múltiplos símbolos
- Qualquer timeframe que preferir
