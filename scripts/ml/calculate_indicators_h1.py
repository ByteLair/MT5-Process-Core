#!/usr/bin/env python3
"""
Calcular indicadores técnicos para H1
"""
import os
import sys
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'mt5_trading'),
    'user': os.getenv('DB_USER', 'trader'),
    'password': os.getenv('DB_PASSWORD', 'trader123')
}

def calculate_rsi(data, period=14):
    """Calculate RSI"""
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    ema_fast = data['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = data['close'].ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist

def calculate_bollinger_bands(data, period=20, std=2):
    """Calculate Bollinger Bands"""
    sma = data['close'].rolling(window=period).mean()
    std_dev = data['close'].rolling(window=period).std()
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    return upper, sma, lower

def calculate_atr(data, period=14):
    """Calculate ATR"""
    high_low = data['high'] - data['low']
    high_close = np.abs(data['high'] - data['close'].shift())
    low_close = np.abs(data['low'] - data['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def calculate_stochastic(data, period=14):
    """Calculate Stochastic Oscillator"""
    low_min = data['low'].rolling(window=period).min()
    high_max = data['high'].rolling(window=period).max()
    stoch_k = 100 * (data['close'] - low_min) / (high_max - low_min)
    stoch_d = stoch_k.rolling(window=3).mean()
    return stoch_k, stoch_d

def calculate_cci(data, period=20):
    """Calculate Commodity Channel Index"""
    tp = (data['high'] + data['low'] + data['close']) / 3
    sma = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
    return (tp - sma) / (0.015 * mad)

def main():
    print("\n" + "="*70)
    print("🔧 CALCULANDO INDICADORES H1")
    print("="*70 + "\n")
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        
        # Load H1 data
        print("📊 Carregando dados H1...")
        query = """
            SELECT ts, open, high, low, close, volume
            FROM market_data
            WHERE symbol = 'EURUSD'
            AND timeframe = 'H1'
            ORDER BY ts ASC
        """
        df = pd.read_sql(query, conn)
        print(f"✅ {len(df):,} candles H1 carregados\n")
        
        if len(df) == 0:
            print("❌ Nenhum dado H1 encontrado!")
            return
        
        # Calculate indicators
        print("🔢 Calculando indicadores técnicos...")
        
        # RSI
        print("  • RSI (14)...", end=" ", flush=True)
        df['rsi'] = calculate_rsi(df, 14)
        print("✓")
        
        # MACD
        print("  • MACD (12,26,9)...", end=" ", flush=True)
        df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(df)
        print("✓")
        
        # Bollinger Bands
        print("  • Bollinger Bands (20,2)...", end=" ", flush=True)
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = calculate_bollinger_bands(df)
        print("✓")
        
        # ATR
        print("  • ATR (14)...", end=" ", flush=True)
        df['atr'] = calculate_atr(df, 14)
        print("✓")
        
        # Stochastic
        print("  • Stochastic (14,3)...", end=" ", flush=True)
        df['stoch_k'], df['stoch_d'] = calculate_stochastic(df, 14)
        print("✓")
        
        # CCI
        print("  • CCI (20)...", end=" ", flush=True)
        df['cci'] = calculate_cci(df, 20)
        print("✓")
        
        # EMAs
        print("  • EMAs (9,21,50,200)...", end=" ", flush=True)
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        print("✓")
        
        # SMAs
        print("  • SMAs (20,50,200)...", end=" ", flush=True)
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['sma_200'] = df['close'].rolling(window=200).mean()
        print("✓")
        
        # ADX
        print("  • ADX (14)...", end=" ", flush=True)
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        tr = calculate_atr(df, 1)
        atr = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(14).mean()
        print("✓\n")
        
        # Remove NaN rows (warm-up period)
        df_clean = df.dropna()
        print(f"📊 Candles com indicadores completos: {len(df_clean):,}/{len(df):,}")
        print(f"📊 Coverage: {100*len(df_clean)/len(df):.1f}%\n")
        
        # Update database (only columns that exist)
        print("💾 Atualizando banco de dados...")
        cursor = conn.cursor()
        
        update_count = 0
        for idx, row in df_clean.iterrows():
            cursor.execute("""
                UPDATE market_data
                SET 
                    rsi = %s,
                    macd = %s,
                    macd_signal = %s,
                    macd_hist = %s,
                    bb_upper = %s,
                    bb_middle = %s,
                    bb_lower = %s,
                    atr = %s
                WHERE symbol = 'EURUSD'
                AND timeframe = 'H1'
                AND ts = %s
            """, (
                float(row['rsi']),
                float(row['macd']),
                float(row['macd_signal']),
                float(row['macd_hist']),
                float(row['bb_upper']),
                float(row['bb_middle']),
                float(row['bb_lower']),
                float(row['atr']),
                row['ts']
            ))
            update_count += 1
            
            if update_count % 1000 == 0:
                print(f"  📊 Progresso: {update_count:,}/{len(df_clean):,} ({100*update_count/len(df_clean):.1f}%)")
                conn.commit()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ {update_count:,} candles atualizados com sucesso!")
        
        print("\n" + "="*70)
        print("✅ INDICADORES H1 CALCULADOS COM SUCESSO!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
