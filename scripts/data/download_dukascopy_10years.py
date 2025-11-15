#!/usr/bin/env python3
"""
Download de dados históricos FOREX do Dukascopy (10 anos)
Sistema robusto com checkpoint, retry e salvamento incremental

Autor: MT5-Process-Core
Data: 2025-11-15
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import requests
import struct
import gzip
import time
from pathlib import Path
import sys
import json
from io import BytesIO

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════

SYMBOL = "EURUSD"
YEARS = 10
END_DATE = datetime(2025, 11, 15)  # Data fixa para reprodutibilidade
START_DATE = END_DATE - timedelta(days=YEARS * 365)

# Conexão PostgreSQL
DB_HOST = "mt5_db"
DB_PORT = "5432"
DB_NAME = "mt5_trading"
DB_USER = "trader"
DB_PASS = "trader123"

CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Controle de progresso
CHECKPOINT_FILE = "/app/data/checkpoint.json"
BATCH_SIZE = 24  # Salvar a cada 24 horas de dados
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos

# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE CHECKPOINT
# ══════════════════════════════════════════════════════════════════════════════

def load_checkpoint():
    """Carrega checkpoint de progresso"""
    try:
        if Path(CHECKPOINT_FILE).exists():
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {'last_date': None, 'h1_count': 0, 'h4_count': 0, 'd1_count': 0}


def save_checkpoint(last_date, h1_count, h4_count, d1_count):
    """Salva checkpoint de progresso"""
    try:
        Path(CHECKPOINT_FILE).parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            'last_date': last_date.isoformat() if last_date else None,
            'h1_count': h1_count,
            'h4_count': h4_count,
            'd1_count': d1_count,
            'updated_at': datetime.now().isoformat()
        }
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    except Exception as e:
        print(f"   ⚠️  Erro ao salvar checkpoint: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE DOWNLOAD DUKASCOPY
# ══════════════════════════════════════════════════════════════════════════════

def parse_bi5_file(content: bytes) -> list:
    """
    Parseia arquivo .bi5 do Dukascopy
    
    Formato: Each tick = 20 bytes
    - Time offset (4 bytes, big-endian int): ms desde início da hora
    - Ask (4 bytes, big-endian int): preço ask * 100000
    - Bid (4 bytes, big-endian int): preço bid * 100000
    - Ask volume (4 bytes, big-endian float)
    - Bid volume (4 bytes, big-endian float)
    """
    ticks = []
    
    try:
        # Descomprimir se for gzip
        if content[:2] == b'\x1f\x8b':  # Magic bytes do gzip
            content = gzip.decompress(content)
        
        # Cada tick tem 20 bytes
        num_ticks = len(content) // 20
        
        for i in range(num_ticks):
            offset = i * 20
            chunk = content[offset:offset + 20]
            
            if len(chunk) < 20:
                break
            
            # Unpack big-endian
            time_offset, ask, bid, ask_vol, bid_vol = struct.unpack('>IIIff', chunk)
            
            ticks.append({
                'time_offset_ms': time_offset,
                'ask': ask / 100000.0,
                'bid': bid / 100000.0,
                'ask_volume': ask_vol,
                'bid_volume': bid_vol
            })
    
    except Exception as e:
        print(f"      ⚠️  Erro ao parsear: {e}")
    
    return ticks


def download_hour_ticks(date: datetime, hour: int, retry_count=0) -> list:
    """
    Baixa ticks de uma hora específica do Dukascopy
    
    Args:
        date: Data (dia)
        hour: Hora (0-23)
        retry_count: Contador de tentativas
    
    Returns:
        Lista de ticks ou lista vazia em caso de erro
    """
    url = (
        f"https://datafeed.dukascopy.com/datafeed/{SYMBOL}/"
        f"{date.year:04d}/{date.month-1:02d}/{date.day:02d}/"
        f"{hour:02d}h_ticks.bi5"
    )
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            ticks = parse_bi5_file(response.content)
            return ticks
        elif response.status_code == 404:
            # Sem dados para essa hora (normal em fins de semana)
            return []
        else:
            print(f"      ⚠️  Status {response.status_code}")
            if retry_count < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                return download_hour_ticks(date, hour, retry_count + 1)
            return []
    
    except Exception as e:
        if retry_count < MAX_RETRIES:
            print(f"      ⚠️  Erro: {e}, tentando novamente...")
            time.sleep(RETRY_DELAY)
            return download_hour_ticks(date, hour, retry_count + 1)
        else:
            print(f"      ❌ Falhou após {MAX_RETRIES} tentativas: {e}")
            return []


def ticks_to_h1_candle(date: datetime, hour: int, ticks: list) -> dict:
    """
    Converte ticks em candle H1
    
    Args:
        date: Data
        hour: Hora
        ticks: Lista de ticks
    
    Returns:
        Dicionário com dados OHLCV ou None
    """
    if not ticks:
        return None
    
    # Usar preço mid (ask + bid) / 2
    prices = [(t['ask'] + t['bid']) / 2 for t in ticks]
    volumes = [t['ask_volume'] + t['bid_volume'] for t in ticks]
    
    timestamp = datetime(date.year, date.month, date.day, hour, 0, 0)
    
    return {
        'timestamp': timestamp,
        'open': prices[0],
        'high': max(prices),
        'low': min(prices),
        'close': prices[-1],
        'volume': sum(volumes)
    }


def download_day_h1(date: datetime) -> list:
    """
    Baixa dados H1 de um dia completo (24 horas)
    
    Args:
        date: Data do dia
    
    Returns:
        Lista de candles H1
    """
    candles = []
    
    for hour in range(24):
        ticks = download_hour_ticks(date, hour)
        
        if ticks:
            candle = ticks_to_h1_candle(date, hour, ticks)
            if candle:
                candles.append(candle)
    
    return candles


# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE AGREGAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

def aggregate_h1_to_h4(df_h1: pd.DataFrame) -> pd.DataFrame:
    """Agrega H1 para H4"""
    df = df_h1.copy()
    df.set_index('timestamp', inplace=True)
    
    df_h4 = df.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return df_h4.reset_index()


def aggregate_h1_to_d1(df_h1: pd.DataFrame) -> pd.DataFrame:
    """Agrega H1 para D1"""
    df = df_h1.copy()
    df.set_index('timestamp', inplace=True)
    
    df_d1 = df.resample('1D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    return df_d1.reset_index()


# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE BANCO DE DADOS
# ══════════════════════════════════════════════════════════════════════════════

def save_to_database_batch(df: pd.DataFrame, timeframe: str, symbol: str = SYMBOL):
    """
    Salva batch de dados no PostgreSQL
    
    Args:
        df: DataFrame com dados OHLCV
        timeframe: 'H1', 'H4' ou 'D1'
        symbol: Par de moedas
    """
    if df.empty:
        return
    
    try:
        engine = create_engine(CONNECTION_STRING)
        
        # Adicionar colunas necessárias
        df_save = df.copy()
        df_save['symbol'] = symbol
        df_save['timeframe'] = timeframe
        df_save['ts'] = df_save['timestamp']
        
        # Converter timezone para UTC se necessário
        if df_save['ts'].dt.tz is None:
            df_save['ts'] = pd.to_datetime(df_save['ts']).dt.tz_localize('UTC')
        else:
            df_save['ts'] = pd.to_datetime(df_save['ts']).dt.tz_convert('UTC')
        
        # Inserir com ON CONFLICT DO NOTHING (ignorar duplicatas)
        with engine.connect() as conn:
            for _, row in df_save.iterrows():
                insert_query = text("""
                    INSERT INTO market_data (ts, symbol, timeframe, open, high, low, close, volume)
                    VALUES (:ts, :symbol, :timeframe, :open, :high, :low, :close, :volume)
                    ON CONFLICT (symbol, timeframe, ts) DO NOTHING
                """)
                conn.execute(insert_query, {
                    'ts': row['ts'],
                    'symbol': row['symbol'],
                    'timeframe': row['timeframe'],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume'])
                })
            conn.commit()
        
        engine.dispose()
        
    except Exception as e:
        print(f"   ❌ Erro ao salvar batch: {e}")
        raise


def get_database_stats(timeframe: str, symbol: str = SYMBOL):
    """Retorna estatísticas do banco de dados"""
    try:
        engine = create_engine(CONNECTION_STRING)
        
        with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) as total,
                       MIN(ts) as min_date,
                       MAX(ts) as max_date
                FROM market_data
                WHERE symbol = :symbol AND timeframe = :timeframe
            """)
            result = conn.execute(query, {'symbol': symbol, 'timeframe': timeframe})
            row = result.fetchone()
            
            engine.dispose()
            return {'total': row[0], 'min_date': row[1], 'max_date': row[2]}
    except:
        return {'total': 0, 'min_date': None, 'max_date': None}


# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Função principal"""
    
    print("=" * 80)
    print("📊 DOWNLOAD DUKASCOPY - 10 ANOS (H1, H4, D1)")
    print("=" * 80)
    print()
    print(f"Par: {SYMBOL}")
    print(f"Período: {START_DATE.date()} até {END_DATE.date()}")
    print(f"Anos: {YEARS}")
    print(f"Destino: PostgreSQL ({DB_HOST})")
    print()
    
    # Carregar checkpoint
    checkpoint = load_checkpoint()
    
    if checkpoint['last_date']:
        last_date = datetime.fromisoformat(checkpoint['last_date'])
        print(f"🔄 Continuando do checkpoint: {last_date.date()}")
        print(f"   H1: {checkpoint['h1_count']:,} candles já salvos")
        print(f"   H4: {checkpoint['h4_count']:,} candles já salvos")
        print(f"   D1: {checkpoint['d1_count']:,} candles já salvos")
        current_date = last_date + timedelta(days=1)
    else:
        print("🆕 Iniciando download do zero")
        current_date = START_DATE
    
    print()
    print("=" * 80)
    print()
    
    # Acumuladores
    h1_buffer = []
    total_days = (END_DATE - START_DATE).days
    processed_days = (current_date - START_DATE).days if checkpoint['last_date'] else 0
    
    # Loop principal
    while current_date <= END_DATE:
        processed_days += 1
        progress_pct = (processed_days / total_days) * 100
        
        print(f"📅 {current_date.date()} ({processed_days}/{total_days} - {progress_pct:.1f}%)")
        
        # Download do dia
        day_candles = download_day_h1(current_date)
        
        if day_candles:
            h1_buffer.extend(day_candles)
            print(f"   ✅ {len(day_candles)} candles H1 baixados (buffer: {len(h1_buffer)})")
        else:
            print(f"   ⚠️  Sem dados (fim de semana ou feriado)")
        
        # Salvar batch a cada BATCH_SIZE dias
        if len(h1_buffer) >= BATCH_SIZE or current_date == END_DATE:
            if h1_buffer:
                print()
                print(f"   💾 Salvando batch de {len(h1_buffer)} candles...")
                
                # Converter para DataFrame
                df_h1 = pd.DataFrame(h1_buffer)
                
                # Salvar H1
                save_to_database_batch(df_h1, 'H1')
                
                # Agregar e salvar H4
                df_h4 = aggregate_h1_to_h4(df_h1)
                save_to_database_batch(df_h4, 'H4')
                
                # Agregar e salvar D1
                df_d1 = aggregate_h1_to_d1(df_h1)
                save_to_database_batch(df_d1, 'D1')
                
                # Atualizar checkpoint
                checkpoint['h1_count'] += len(df_h1)
                checkpoint['h4_count'] += len(df_h4)
                checkpoint['d1_count'] += len(df_d1)
                save_checkpoint(current_date, checkpoint['h1_count'], checkpoint['h4_count'], checkpoint['d1_count'])
                
                print(f"   ✅ Batch salvo! Total: H1={checkpoint['h1_count']:,}, H4={checkpoint['h4_count']:,}, D1={checkpoint['d1_count']:,}")
                print()
                
                # Limpar buffer
                h1_buffer = []
        
        # Próximo dia
        current_date += timedelta(days=1)
    
    # Estatísticas finais
    print()
    print("=" * 80)
    print("✅ DOWNLOAD CONCLUÍDO!")
    print("=" * 80)
    print()
    
    for tf in ['H1', 'H4', 'D1']:
        stats = get_database_stats(tf)
        print(f"📊 {tf}:")
        print(f"   • Total: {stats['total']:,} candles")
        if stats['total'] > 0:
            print(f"   • Período: {stats['min_date']} até {stats['max_date']}")
        print()
    
    print("🎯 Próximos passos:")
    print("   1. Calcular indicadores técnicos")
    print("   2. Criar features multi-timeframe")
    print("   3. Treinar modelo com 10 anos de dados")
    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrompido. Use checkpoint para continuar.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
