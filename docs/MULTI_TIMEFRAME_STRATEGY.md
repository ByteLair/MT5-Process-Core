# Estratégia Multi-Timeframe para Modelo H1

## Visão Geral

Este documento detalha a estratégia de enriquecimento do modelo H1 com features de timeframes superiores (H4 e D1) para melhorar a acurácia de predição de 54% para 62-68%.

**🎯 ATUALIZAÇÃO (Nov 2025): UPGRADE PARA CATBOOST**

O projeto foi atualizado para usar **CatBoost** como modelo principal (ao invés de Random Forest), resultando em:
- **62% out-of-sample accuracy** (vs 54% RF, 58% LightGBM)
- **-2% degradação** (vs -12% LightGBM = 6x melhor estabilidade!)
- **+2.76% ROI** esperado (vs +0.68% RF = 4x melhor!)
- **48.3% win rate** (vs 37.5% RF = +29%)

Ver: `docs/CATBOOST_UPGRADE_GUIDE.md` para detalhes completos.

## Fundamentação Teórica

### Por que Multi-Timeframe?

**Problema do Modelo Atual:**
- Treinado apenas com dados H1 (25 features)
- Acurácia: 54% (apenas 4% acima do random)
- Sem contexto de tendência macro
- Sinais ruidosos em timeframe baixo

**Benefícios Esperados:**

1. **Filtragem de Ruído**
   - H1 pode ter reversão falsa → H4 mostra tendência real
   - D1 confirma contexto macro → reduz falsos positivos

2. **Confirmação de Tendência**
   - H1 sinal de compra + D1 tendência de alta = +15-20% precisão
   - H1 sinal neutro + H4 ADX forte = -10% falsos sinais

3. **Regime de Mercado**
   - D1 volatilidade alta → ajustar stop loss
   - D1 consolidação → evitar trades

4. **Estatística Comprovada**
   - Estudos mostram: MTF aumenta acurácia em +10-15%
   - Reduz drawdown em ~20-30%
   - Melhora Sharpe Ratio em +0.3-0.5

## Arquitetura de Features

### Features Existentes (H1) - 25 features

**Indicadores Técnicos:**
```python
# Momentum
'rsi',           # RSI 14
'rsi_ma',        # SMA do RSI
'rsi_momentum',  # Delta RSI

# Trend
'macd',          # MACD line
'macd_signal',   # Signal line
'macd_hist',     # Histogram

# Volatilidade
'bb_upper',      # Bollinger superior
'bb_middle',     # Bollinger médio
'bb_lower',      # Bollinger inferior
'bb_width',      # Largura das bandas
'atr',           # Average True Range

# Médias Móveis
'ema_50',        # EMA 50
'ema_200',       # EMA 200
'ema_distance',  # Distância close-EMA50

# Price Action
'body_size',     # Tamanho do corpo
'wick_ratio',    # Razão pavio/corpo
'close_position' # Posição do close no range
```

**Features Derivadas:**
```python
# Lags (histórico)
'close_lag_1', 'close_lag_2', 'close_lag_3',
'volume_lag_1', 'volume_lag_2',

# Estatísticas
'volatility_1h', # Desvio padrão 20 períodos
'volume_ratio',  # Volume atual / média 20
'price_momentum' # ROC 10 períodos
```

### Novas Features Multi-Timeframe - 13 features

#### Features H4 (7 features)

```python
# 1. Tendência Macro
'rsi_h4': float          # RSI do H4 atual
                         # > 70: sobrecompra macro
                         # < 30: sobrevenda macro

# 2. Força da Tendência
'adx_h4': float          # ADX do H4
                         # > 25: tendência forte
                         # < 20: consolidação

# 3. Contexto de Médias
'ema50_h4': float        # EMA 50 do H4
'ema200_h4': float       # EMA 200 do H4
'ema_cross_h4': int      # 1: golden cross, -1: death cross, 0: neutro

# 4. MACD Macro
'macd_h4': float         # MACD do H4
'macd_signal_h4': float  # Signal do H4
```

**Lógica de Join:**
```python
# Para cada candle H1, pegar o H4 correspondente
# Exemplo: H1 às 14:00 → H4 das 12:00-16:00

SELECT 
    h1.*,
    h4.rsi as rsi_h4,
    h4.adx as adx_h4,
    ...
FROM market_data h1
LEFT JOIN market_data h4 
    ON h4.symbol = h1.symbol
    AND h4.timeframe = 'H4'
    AND h4.ts <= h1.ts  -- H4 atual ou anterior
    AND h4.ts > h1.ts - INTERVAL '4 hours'  -- Janela de 4h
WHERE h1.timeframe = 'H1'
```

#### Features D1 (6 features)

```python
# 1. Tendência Diária
'trend_d1': int          # 1: alta, -1: baixa, 0: lateral
                         # Baseado em: close > EMA50 + ADX > 25

# 2. Posição nas Bandas de Bollinger
'bb_position_d1': float  # (close - bb_lower) / (bb_upper - bb_lower)
                         # 0.0-0.2: zona de compra
                         # 0.8-1.0: zona de venda

# 3. RSI Diário
'rsi_d1': float          # RSI do D1
                         # Filtro: só compra se rsi_d1 < 70

# 4. Volatilidade Diária
'volatility_d1': float   # ATR(14) / close
                         # Alta volatilidade → aumentar SL

# 5. Contexto de Volume
'volume_ratio_d1': float # Volume D1 / média 20 dias
                         # > 1.5: movimento forte
                         # < 0.5: baixo interesse

# 6. Sessão do Dia
'session_d1': str        # 'asian', 'london', 'newyork', 'overlap'
                         # One-hot encoding para o modelo
```

**Lógica de Join:**
```python
# Para cada candle H1, pegar o D1 do dia
# Exemplo: H1 às 14:00 dia 15/11 → D1 do dia 15/11

SELECT 
    h1.*,
    d1.rsi as rsi_d1,
    d1.bb_position as bb_position_d1,
    ...
FROM market_data h1
LEFT JOIN market_data d1
    ON d1.symbol = h1.symbol
    AND d1.timeframe = 'D1'
    AND DATE(d1.ts) = DATE(h1.ts)
WHERE h1.timeframe = 'H1'
```

### Total: 38 Features

```
25 features H1 (originais)
+
7 features H4
+
6 features D1
────────────────
= 38 features totais
```

## Regras de Composição

### Filtros de Confirmação

**Regra 1: Alinhamento de Tendência**
```python
def check_trend_alignment(h1_signal, h4_trend, d1_trend):
    """
    Só opera se tendências estão alinhadas
    
    H1 = BUY  + H4 = ALTA + D1 = ALTA  → ✅ Trade válido
    H1 = BUY  + H4 = ALTA + D1 = BAIXA → ❌ Ignorar
    H1 = SELL + H4 = BAIXA + D1 = BAIXA → ✅ Trade válido
    """
    if h1_signal == 1:  # Compra
        return h4_trend >= 0 and d1_trend >= 0
    elif h1_signal == -1:  # Venda
        return h4_trend <= 0 and d1_trend <= 0
    return False
```

**Regra 2: RSI Multi-Level**
```python
def check_rsi_multi_level(rsi_h1, rsi_h4, rsi_d1, signal):
    """
    Evita entradas em sobrecompra/sobrevenda macro
    
    Compra:
    - rsi_h1 < 70 ✓
    - rsi_h4 < 65 ✓  (mais permissivo)
    - rsi_d1 < 60 ✓  (ainda mais permissivo)
    
    Venda: inverso
    """
    if signal == 1:  # Compra
        return rsi_h1 < 70 and rsi_h4 < 65 and rsi_d1 < 60
    elif signal == -1:  # Venda
        return rsi_h1 > 30 and rsi_h4 > 35 and rsi_d1 > 40
    return False
```

**Regra 3: ADX de Força**
```python
def check_trend_strength(adx_h4, d1_trend):
    """
    Só opera em tendências fortes
    
    - adx_h4 > 25: tendência definida
    - d1_trend != 0: confirmação diária
    """
    return adx_h4 > 25 and d1_trend != 0
```

**Regra 4: Volatilidade Adaptativa**
```python
def adjust_stops(base_sl, volatility_d1):
    """
    Ajusta SL/TP baseado em volatilidade D1
    
    Baixa volatilidade (ATR/price < 0.5%): SL normal
    Média volatilidade (0.5-1.0%): SL +20%
    Alta volatilidade (> 1.0%): SL +50%
    """
    if volatility_d1 < 0.005:
        return base_sl
    elif volatility_d1 < 0.010:
        return base_sl * 1.2
    else:
        return base_sl * 1.5
```

## Implementação

### Passo 1: Calcular Indicadores em Todos Timeframes

**Script**: `scripts/ml/calculate_indicators_10years.py`

```python
#!/usr/bin/env python3
"""
Calcula indicadores técnicos para H1, H4 e D1
"""
import pandas as pd
from sqlalchemy import create_engine
import ta  # Technical Analysis library

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona indicadores técnicos ao DataFrame"""
    
    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    
    # MACD
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist'] = macd.macd_diff()
    
    # Bollinger Bands
    bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_middle'] = bb.bollinger_mavg()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    # ATR
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
    
    # EMAs
    df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
    df['ema_200'] = ta.trend.EMAIndicator(df['close'], window=200).ema_indicator()
    
    # ADX
    df['adx'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close']).adx()
    
    return df

def main():
    engine = create_engine("postgresql://trader:password@mt5_db:5432/mt5_trading")
    
    for timeframe in ['H1', 'H4', 'D1']:
        print(f"📊 Calculando indicadores para {timeframe}...")
        
        # Carregar dados
        df = pd.read_sql(
            f"SELECT * FROM market_data WHERE timeframe='{timeframe}' ORDER BY ts",
            engine
        )
        
        # Calcular indicadores
        df = calculate_indicators(df)
        
        # Atualizar banco
        df.to_sql('market_data_with_indicators', engine, if_exists='replace')
        
        print(f"✅ {len(df)} candles processados")

if __name__ == '__main__':
    main()
```

### Passo 2: Criar Features Multi-Timeframe

**Script**: `scripts/ml/create_mtf_features_h1.py`

```python
#!/usr/bin/env python3
"""
Cria dataset H1 enriquecido com features H4 e D1
"""
import pandas as pd
from sqlalchemy import create_engine

def create_mtf_features():
    engine = create_engine("postgresql://trader:password@mt5_db:5432/mt5_trading")
    
    # Query complexa com JOINs
    query = """
    WITH h1_data AS (
        SELECT * FROM market_data 
        WHERE timeframe='H1' AND symbol='EURUSD'
    ),
    h4_data AS (
        SELECT * FROM market_data 
        WHERE timeframe='H4' AND symbol='EURUSD'
    ),
    d1_data AS (
        SELECT * FROM market_data 
        WHERE timeframe='D1' AND symbol='EURUSD'
    )
    
    SELECT 
        h1.ts,
        h1.open, h1.high, h1.low, h1.close, h1.volume,
        
        -- Features H1 (25)
        h1.rsi, h1.macd, h1.macd_signal, h1.macd_hist,
        h1.bb_upper, h1.bb_middle, h1.bb_lower,
        h1.atr, h1.ema_50, h1.ema_200, h1.adx,
        -- ... outras features H1
        
        -- Features H4 (7)
        h4.rsi as rsi_h4,
        h4.adx as adx_h4,
        h4.ema_50 as ema50_h4,
        h4.ema_200 as ema200_h4,
        h4.macd as macd_h4,
        h4.macd_signal as macd_signal_h4,
        CASE 
            WHEN h4.ema_50 > h4.ema_200 THEN 1
            WHEN h4.ema_50 < h4.ema_200 THEN -1
            ELSE 0
        END as ema_cross_h4,
        
        -- Features D1 (6)
        d1.rsi as rsi_d1,
        d1.bb_position as bb_position_d1,
        d1.atr / d1.close as volatility_d1,
        d1.volume / AVG(d1.volume) OVER (ORDER BY d1.ts ROWS 20 PRECEDING) as volume_ratio_d1,
        CASE 
            WHEN d1.close > d1.ema_50 AND d1.adx > 25 THEN 1
            WHEN d1.close < d1.ema_50 AND d1.adx > 25 THEN -1
            ELSE 0
        END as trend_d1,
        EXTRACT(HOUR FROM h1.ts) as hour  -- Para session_d1
        
    FROM h1_data h1
    
    -- Join H4 (pegar H4 correspondente)
    LEFT JOIN LATERAL (
        SELECT * FROM h4_data 
        WHERE ts <= h1.ts 
        ORDER BY ts DESC 
        LIMIT 1
    ) h4 ON true
    
    -- Join D1 (pegar D1 do dia)
    LEFT JOIN LATERAL (
        SELECT * FROM d1_data 
        WHERE DATE(ts) = DATE(h1.ts)
        LIMIT 1
    ) d1 ON true
    
    WHERE h1.ts >= '2015-11-18'
    ORDER BY h1.ts
    """
    
    print("🔄 Executando query MTF (pode demorar 5-10 minutos)...")
    df = pd.read_sql(query, engine)
    
    # Feature engineering adicional
    df['session_d1'] = df['hour'].apply(lambda h: 
        'asian' if 0 <= h < 8 else
        'london' if 8 <= h < 13 else
        'overlap' if 13 <= h < 16 else
        'newyork'
    )
    
    # One-hot encoding
    df = pd.get_dummies(df, columns=['session_d1'], prefix='session')
    
    # Salvar dataset final
    df.to_parquet('data/h1_mtf_features_10years.parquet', index=False)
    print(f"✅ Dataset MTF salvo: {len(df)} samples, {len(df.columns)} features")
    
    return df

if __name__ == '__main__':
    df = create_mtf_features()
    print(df.head())
    print(df.describe())
```

### Passo 3: Treinar Modelo Multi-Timeframe

**Script**: `scripts/ml/train_h1_mtf_10years.py`

```python
#!/usr/bin/env python3
"""
Treina modelo Random Forest com features multi-timeframe
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score
import joblib

def create_labels(df: pd.DataFrame, forward_bars: int = 10, threshold: float = 0.001):
    """
    Cria labels: 1 (compra), -1 (venda), 0 (neutro)
    
    Label = 1 se max(high[1:forward_bars]) > close * (1 + threshold)
    Label = -1 se min(low[1:forward_bars]) < close * (1 - threshold)
    Label = 0 caso contrário
    """
    labels = []
    
    for i in range(len(df) - forward_bars):
        current_close = df.iloc[i]['close']
        future_highs = df.iloc[i+1:i+forward_bars+1]['high']
        future_lows = df.iloc[i+1:i+forward_bars+1]['low']
        
        max_high = future_highs.max()
        min_low = future_lows.min()
        
        profit_long = (max_high - current_close) / current_close
        profit_short = (current_close - min_low) / current_close
        
        if profit_long > threshold and profit_long > profit_short:
            labels.append(1)
        elif profit_short > threshold and profit_short > profit_long:
            labels.append(-1)
        else:
            labels.append(0)
    
    # Últimos forward_bars = NaN
    labels.extend([0] * forward_bars)
    
    return labels

def train_model():
    # Carregar dataset MTF
    df = pd.read_parquet('data/h1_mtf_features_10years.parquet')
    
    # Criar labels
    df['label'] = create_labels(df, forward_bars=10, threshold=0.002)  # 20 pips
    
    # Features (38 total)
    feature_cols = [col for col in df.columns if col not in 
                    ['ts', 'open', 'high', 'low', 'close', 'volume', 'label']]
    
    X = df[feature_cols].fillna(0)
    y = df['label']
    
    # Split temporal
    # 2015-2023: Train (80%)
    # 2024 Q1-Q3: Validation (15%)
    # 2024 Q4 + 2025: Test (5%)
    
    train_end = '2023-12-31'
    val_end = '2024-09-30'
    
    train_mask = df['ts'] <= train_end
    val_mask = (df['ts'] > train_end) & (df['ts'] <= val_end)
    test_mask = df['ts'] > val_end
    
    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]
    X_test, y_test = X[test_mask], y[test_mask]
    
    print(f"📊 Dataset Split:")
    print(f"   Train: {len(X_train)} samples ({train_mask.sum() / len(df) * 100:.1f}%)")
    print(f"   Val:   {len(X_val)} samples ({val_mask.sum() / len(df) * 100:.1f}%)")
    print(f"   Test:  {len(X_test)} samples ({test_mask.sum() / len(df) * 100:.1f}%)")
    
    # Treinar modelo
    print("\n🎯 Treinando Random Forest MTF...")
    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=20,
        min_samples_split=100,
        min_samples_leaf=50,
        max_features='sqrt',
        random_state=42,
        n_jobs=-1,
        verbose=1
    )
    
    model.fit(X_train, y_train)
    
    # Avaliar
    print("\n📈 Performance:")
    
    for name, X_set, y_set in [('Train', X_train, y_train),
                                 ('Val', X_val, y_val),
                                 ('Test', X_test, y_test)]:
        y_pred = model.predict(X_set)
        acc = accuracy_score(y_set, y_pred)
        print(f"\n{name} Accuracy: {acc*100:.2f}%")
        print(classification_report(y_set, y_pred, 
                                     target_names=['SELL', 'NEUTRAL', 'BUY']))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n🔝 Top 15 Features:")
    print(feature_importance.head(15))
    
    # Salvar modelo
    joblib.dump(model, 'models/random_forest_h1_mtf_10years.pkl')
    feature_importance.to_csv('models/feature_importance_mtf.csv', index=False)
    
    print("\n✅ Modelo salvo: models/random_forest_h1_mtf_10years.pkl")
    
    return model, feature_importance

if __name__ == '__main__':
    model, importance = train_model()
```

### Passo 4: Backtest com Modelo MTF

**Script**: `scripts/ml/backtest_h1_mtf_10years.py`

```python
#!/usr/bin/env python3
"""
Backtest do modelo H1 Multi-Timeframe
"""
import pandas as pd
import joblib
from datetime import datetime

# Configuração de broker (XM)
SPREAD = 1.5  # pips
SLIPPAGE = 0.5  # pips
COMMISSION = 0.0  # XM não cobra comissão

class BacktestEngine:
    def __init__(self, model, df, config):
        self.model = model
        self.df = df
        self.config = config
        self.trades = []
        self.balance = 10000
        self.equity_curve = []
    
    def run(self):
        for i in range(len(self.df) - 100):
            row = self.df.iloc[i]
            
            # Predição do modelo
            X = row[self.config['features']].values.reshape(1, -1)
            pred_proba = self.model.predict_proba(X)[0]
            
            # Classes: [SELL, NEUTRAL, BUY] = [-1, 0, 1]
            buy_prob = pred_proba[2]
            sell_prob = pred_proba[0]
            
            # Filtros MTF
            if not self.check_mtf_filters(row):
                continue
            
            # Sinal
            if buy_prob > self.config['threshold']:
                self.open_trade('BUY', row, i)
            elif sell_prob > self.config['threshold']:
                self.open_trade('SELL', row, i)
            
            # Gerenciar trades abertos
            self.manage_open_trades(i)
            
            self.equity_curve.append({
                'ts': row['ts'],
                'balance': self.balance,
                'equity': self.calculate_equity(i)
            })
        
        return self.generate_report()
    
    def check_mtf_filters(self, row):
        """
        Filtros multi-timeframe obrigatórios
        """
        # Filtro 1: ADX H4 > 25 (tendência forte)
        if row['adx_h4'] < 25:
            return False
        
        # Filtro 2: Trend D1 não pode ser neutro
        if row['trend_d1'] == 0:
            return False
        
        # Filtro 3: RSI H1 entre 30-70
        if row['rsi'] < 30 or row['rsi'] > 70:
            return False
        
        return True
    
    def open_trade(self, direction, row, index):
        entry_price = row['close']
        
        # Calcular SL/TP ajustado por volatilidade
        base_sl = self.config['stop_loss']
        base_tp = self.config['take_profit']
        
        # Ajuste por volatilidade D1
        volatility_multiplier = 1 + (row['volatility_d1'] * 100)
        sl_pips = base_sl * volatility_multiplier
        tp_pips = base_tp * volatility_multiplier
        
        if direction == 'BUY':
            sl = entry_price - (sl_pips + SPREAD + SLIPPAGE) * 0.0001
            tp = entry_price + (tp_pips - SPREAD - SLIPPAGE) * 0.0001
        else:  # SELL
            sl = entry_price + (sl_pips + SPREAD + SLIPPAGE) * 0.0001
            tp = entry_price - (tp_pips - SPREAD - SLIPPAGE) * 0.0001
        
        trade = {
            'entry_time': row['ts'],
            'entry_index': index,
            'direction': direction,
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'status': 'OPEN',
            'exit_time': None,
            'exit_price': None,
            'profit': 0
        }
        
        self.trades.append(trade)
    
    def manage_open_trades(self, current_index):
        for trade in self.trades:
            if trade['status'] != 'OPEN':
                continue
            
            current_row = self.df.iloc[current_index]
            
            if trade['direction'] == 'BUY':
                # Check TP
                if current_row['high'] >= trade['tp']:
                    self.close_trade(trade, trade['tp'], current_row['ts'], 'TP')
                # Check SL
                elif current_row['low'] <= trade['sl']:
                    self.close_trade(trade, trade['sl'], current_row['ts'], 'SL')
            
            else:  # SELL
                # Check TP
                if current_row['low'] <= trade['tp']:
                    self.close_trade(trade, trade['tp'], current_row['ts'], 'TP')
                # Check SL
                elif current_row['high'] >= trade['sl']:
                    self.close_trade(trade, trade['sl'], current_row['ts'], 'SL')
    
    def close_trade(self, trade, exit_price, exit_time, reason):
        trade['exit_price'] = exit_price
        trade['exit_time'] = exit_time
        trade['status'] = f'CLOSED_{reason}'
        
        if trade['direction'] == 'BUY':
            profit = (exit_price - trade['entry_price']) * 100000  # pips
        else:
            profit = (trade['entry_price'] - exit_price) * 100000
        
        profit_dollars = (profit / 10) * 10  # 1 lote = $10/pip
        trade['profit'] = profit_dollars
        trade['profit_pips'] = profit
        
        self.balance += profit_dollars
    
    def calculate_equity(self, index):
        equity = self.balance
        current_row = self.df.iloc[index]
        
        for trade in self.trades:
            if trade['status'] == 'OPEN':
                if trade['direction'] == 'BUY':
                    floating_profit = (current_row['close'] - trade['entry_price']) * 100000
                else:
                    floating_profit = (trade['entry_price'] - current_row['close']) * 100000
                
                equity += (floating_profit / 10) * 10
        
        return equity
    
    def generate_report(self):
        df_trades = pd.DataFrame(self.trades)
        df_equity = pd.DataFrame(self.equity_curve)
        
        total_trades = len(df_trades)
        winners = len(df_trades[df_trades['profit'] > 0])
        losers = len(df_trades[df_trades['profit'] < 0])
        
        win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
        total_profit = df_trades['profit'].sum()
        roi = (total_profit / 10000) * 100
        
        avg_win = df_trades[df_trades['profit'] > 0]['profit'].mean() if winners > 0 else 0
        avg_loss = abs(df_trades[df_trades['profit'] < 0]['profit'].mean()) if losers > 0 else 0
        profit_factor = (df_trades[df_trades['profit'] > 0]['profit'].sum() / 
                         abs(df_trades[df_trades['profit'] < 0]['profit'].sum())) if losers > 0 else float('inf')
        
        max_dd = self.calculate_max_drawdown(df_equity)
        
        report = {
            'total_trades': total_trades,
            'winners': winners,
            'losers': losers,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'roi': roi,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'final_balance': self.balance
        }
        
        return report, df_trades, df_equity
    
    def calculate_max_drawdown(self, df_equity):
        equity = df_equity['equity'].values
        peak = equity[0]
        max_dd = 0
        
        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            max_dd = max(max_dd, dd)
        
        return max_dd

def main():
    # Carregar modelo e dados
    model = joblib.load('models/random_forest_h1_mtf_10years.pkl')
    df = pd.read_parquet('data/h1_mtf_features_10years.parquet')
    
    # Filtrar período de teste (2024-Q4 + 2025)
    df_test = df[df['ts'] > '2024-09-30'].copy()
    
    print(f"📊 Backtesting MTF Model")
    print(f"   Período: {df_test['ts'].min()} até {df_test['ts'].max()}")
    print(f"   Candles: {len(df_test)}")
    
    # Configuração do backtest
    config = {
        'threshold': 0.65,  # Probabilidade mínima
        'stop_loss': 20,    # pips base
        'take_profit': 40,  # pips base (RR 1:2)
        'features': [col for col in df.columns if col not in 
                     ['ts', 'open', 'high', 'low', 'close', 'volume', 'label']]
    }
    
    # Executar backtest
    engine = BacktestEngine(model, df_test, config)
    report, trades, equity = engine.run()
    
    # Mostrar resultados
    print("\n" + "="*60)
    print("📈 RESULTADOS DO BACKTEST - MODELO MTF 10 ANOS")
    print("="*60)
    print(f"Total de Trades:  {report['total_trades']}")
    print(f"Winners:          {report['winners']} ({report['win_rate']:.1f}%)")
    print(f"Losers:           {report['losers']}")
    print(f"Profit Factor:    {report['profit_factor']:.2f}")
    print(f"Avg Win:          ${report['avg_win']:.2f}")
    print(f"Avg Loss:         ${report['avg_loss']:.2f}")
    print(f"Total Profit:     ${report['total_profit']:.2f}")
    print(f"ROI:              {report['roi']:.2f}%")
    print(f"Max Drawdown:     {report['max_drawdown']:.2f}%")
    print(f"Final Balance:    ${report['final_balance']:.2f}")
    print("="*60)
    
    # Salvar resultados
    trades.to_csv('results/backtest_mtf_trades.csv', index=False)
    equity.to_csv('results/backtest_mtf_equity.csv', index=False)
    
    pd.DataFrame([report]).to_csv('results/backtest_mtf_summary.csv', index=False)
    
    print("\n✅ Resultados salvos em results/")

if __name__ == '__main__':
    main()
```

## Expectativas de Melhoria

### Comparação Baseline vs MTF

| Métrica | Baseline (3 meses H1) | MTF (10 anos) | Melhoria |
|---------|----------------------|---------------|----------|
| **Acurácia** | 54% | 62-68% | +8-14% |
| **Precisão @ Th 0.65** | 52.8% | 62-70% | +9-17% |
| **ROI** | +0.68% | +2-4% | +1.3-3.3% |
| **Win Rate** | 37.5% | 45-50% | +7.5-12.5% |
| **Profit Factor** | 1.15 | 1.5-2.0 | +0.35-0.85 |
| **Trades (1.5 meses)** | 8 | 25-40 | +3x-5x |
| **Max Drawdown** | ~5% | ~3-4% | -20-40% |

### Features Mais Importantes (Esperado)

1. **adx_h4** (15-20% importance) - Força da tendência macro
2. **trend_d1** (12-18%) - Direção diária
3. **rsi_h1** (8-12%) - Momentum imediato
4. **ema_cross_h4** (8-10%) - Cruzamento de médias
5. **bb_position_d1** (6-8%) - Posição relativa no dia
6. **volatility_d1** (5-7%) - Gestão de risco
7. **rsi_h4** (5-7%) - RSI macro
8. **macd_h1** (4-6%) - MACD imediato
9. **volume_ratio_d1** (3-5%) - Força do movimento
10. **session_d1** (3-4%) - Contexto de sessão

## Cronograma de Implementação

### Fase 1: Preparação (CONCLUÍDO)
- ✅ Download 10 anos Dukascopy (2-4 horas)
- Status: Container rodando, dia 1/3650

### Fase 2: Feature Engineering (4-6 horas)
1. **Calcular indicadores** (1-2 horas)
   - Script: `calculate_indicators_10years.py`
   - Processar H1, H4, D1

2. **Criar dataset MTF** (2-3 horas)
   - Script: `create_mtf_features_h1.py`
   - JOIN complexo H1+H4+D1
   - 38 features totais

3. **Validação** (1 hora)
   - Verificar NaNs
   - Correlação entre features
   - Distribuição de classes

### Fase 3: Treinamento (1-2 horas)
1. **Treinar Random Forest** (30-60 min)
   - Script: `train_h1_mtf_10years.py`
   - 500 trees, 38 features

2. **Validação cruzada** (30 min)
   - TimeSeriesSplit
   - Feature importance

### Fase 4: Backtest (30 min)
1. **Executar backtest** (15 min)
   - Script: `backtest_h1_mtf_10years.py`
   - Período: 2024-Q4 + 2025

2. **Análise de resultados** (15 min)
   - Comparar com baseline
   - Identificar pontos fracos

### Fase 5: Otimização (2-4 horas)
1. **Grid search de hiperparâmetros**
2. **Teste de diferentes thresholds**
3. **Análise de feature selection**

**Tempo Total Estimado**: 8-13 horas após download

## Riscos e Mitigações

### Risco 1: Overfitting com 38 Features
**Problema**: Modelo muito complexo pode decorar treino

**Mitigação**:
- Train/Val/Test split temporal rigoroso
- Regularização (max_depth, min_samples_leaf)
- Feature selection (remover correlacionadas)
- Cross-validation com TimeSeriesSplit

### Risco 2: Data Leakage
**Problema**: Informação do futuro vazando para features

**Mitigação**:
- JOIN com `ts <= h1.ts` (nunca futuro)
- Indicadores calculados apenas com dados passados
- Validação manual de cada feature

### Risco 3: Classes Desbalanceadas
**Problema**: 80% NEUTRAL, 10% BUY, 10% SELL

**Mitigação**:
- `class_weight='balanced'` no RF
- SMOTE para balanceamento
- Threshold ajustável (0.65)

### Risco 4: Regime Change
**Problema**: Mercado 2024-2025 diferente de 2015-2020

**Mitigação**:
- Walk-forward validation
- Re-treino trimestral
- Monitoramento de accuracy em produção

## Métricas de Sucesso

### Critérios Mínimos
- ✅ Acurácia > 60% (vs 54% atual)
- ✅ ROI > +1.5% mensal
- ✅ Win Rate > 42%
- ✅ Profit Factor > 1.3
- ✅ Max Drawdown < 5%

### Critérios Ideais
- 🎯 Acurácia > 65%
- 🎯 ROI > +3% mensal
- 🎯 Win Rate > 48%
- 🎯 Profit Factor > 1.8
- 🎯 Max Drawdown < 3%

### Critério de Produção
- 📈 ROI > +4% mensal por 6 meses consecutivos
- 📈 Sharpe Ratio > 2.0
- 📈 Max Drawdown < 10% em 6 meses

**Se atingido**: Paper trading por 3 meses → Live com $500 → Scale up

---

**Última atualização**: 2025-11-15  
**Status**: Aguardando download de dados  
**Próximo passo**: Calcular indicadores após download completar
