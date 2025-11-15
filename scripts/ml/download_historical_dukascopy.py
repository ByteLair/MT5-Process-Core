#!/usr/bin/env python3
"""
Download de dados históricos de 5 anos do Dukascopy
Para pesquisa de ML com dados institucionais de alta qualidade

Dukascopy fornece dados FOREX gratuitos com qualidade institucional
Período: 2020-2025 (5 anos)
Timeframes: H1, H4, D1
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import time
import os
from pathlib import Path
import json
import gzip
import struct
from io import BytesIO

# Configurações
SYMBOL = "EURUSD"
START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2025, 11, 15)
OUTPUT_DIR = Path("/app/data/historical")

# Criar diretórios
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("📥 DOWNLOAD DE DADOS HISTÓRICOS - DUKASCOPY")
print("=" * 80)
print()
print(f"Símbolo: {SYMBOL}")
print(f"Período: {START_DATE.strftime('%Y-%m-%d')} até {END_DATE.strftime('%Y-%m-%d')}")
print(f"Anos: {(END_DATE - START_DATE).days / 365.25:.1f}")
print()


def download_dukascopy_ticks(symbol, start_date, end_date):
    """
    Baixa dados tick do Dukascopy e agrega para H1
    
    Dukascopy URL pattern:
    https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YEAR}/{MONTH}/{DAY}/{HOUR}h_ticks.bi5
    """
    
    print("🔍 Método: Dukascopy Datafeed API")
    print()
    
    # Converter símbolo para formato Dukascopy
    duka_symbol = symbol  # EURUSD já está no formato correto
    
    all_candles = []
    current_date = start_date
    
    total_hours = int((end_date - start_date).total_seconds() / 3600)
    hours_processed = 0
    
    print(f"Total de horas para processar: {total_hours:,}")
    print()
    print("Iniciando download...")
    print()
    
    while current_date < end_date:
        year = current_date.year
        month = current_date.month - 1  # Dukascopy usa 0-11
        day = current_date.day
        hour = current_date.hour
        
        # URL do Dukascopy
        url = f"https://datafeed.dukascopy.com/datafeed/{duka_symbol}/{year:04d}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                # Processar dados binários (.bi5 format)
                data = gzip.decompress(response.content)
                
                # Cada tick é 20 bytes: timestamp(4), ask(4), bid(4), ask_volume(4), bid_volume(4)
                num_ticks = len(data) // 20
                
                if num_ticks > 0:
                    ticks = []
                    for i in range(num_ticks):
                        chunk = data[i*20:(i+1)*20]
                        timestamp_ms, ask, bid, ask_vol, bid_vol = struct.unpack('>IIIff', chunk)
                        
                        # Converter timestamp para datetime
                        tick_time = current_date + timedelta(milliseconds=timestamp_ms)
                        
                        # Preço médio (bid+ask)/2 e converter de points para price
                        # Dukascopy armazena em points (100000 = 1.0000 para EURUSD)
                        mid_price = ((bid + ask) / 2) / 100000
                        
                        ticks.append({
                            'timestamp': tick_time,
                            'price': mid_price,
                            'volume': ask_vol + bid_vol
                        })
                    
                    if ticks:
                        # Agregar para candle de 1 hora
                        df_ticks = pd.DataFrame(ticks)
                        
                        candle = {
                            'timestamp': current_date,
                            'open': df_ticks['price'].iloc[0],
                            'high': df_ticks['price'].max(),
                            'low': df_ticks['price'].min(),
                            'close': df_ticks['price'].iloc[-1],
                            'volume': df_ticks['volume'].sum()
                        }
                        
                        all_candles.append(candle)
            
            hours_processed += 1
            
            # Progress report a cada 100 horas
            if hours_processed % 100 == 0:
                progress = (hours_processed / total_hours) * 100
                candles_collected = len(all_candles)
                print(f"  Progresso: {hours_processed:,}/{total_hours:,} horas ({progress:.1f}%) | "
                      f"Candles: {candles_collected:,}")
            
        except Exception as e:
            # Silenciosamente pular erros (fins de semana, feriados, etc)
            pass
        
        # Próxima hora
        current_date += timedelta(hours=1)
        
        # Rate limiting gentil
        time.sleep(0.05)  # 50ms entre requests
    
    return pd.DataFrame(all_candles)


def download_via_yfinance_alternative(symbol, start_date, end_date):
    """
    Alternativa: Usar yfinance para dados históricos
    Mais rápido mas menos preciso
    """
    import yfinance as yf
    
    print("🔍 Método Alternativo: Yahoo Finance (yfinance)")
    print()
    
    # Yahoo Finance usa formato diferente
    yf_symbol = f"{symbol}=X"  # EURUSD=X
    
    print(f"Baixando {yf_symbol} de {start_date.date()} até {end_date.date()}...")
    
    # Download H1 (1 hora)
    df_h1 = yf.download(
        yf_symbol,
        start=start_date,
        end=end_date,
        interval='1h',
        progress=True,
        auto_adjust=True
    )
    
    if df_h1.empty:
        print("⚠️  Nenhum dado retornado!")
        return pd.DataFrame()
    
    # Renomear colunas para nosso formato
    df_h1 = df_h1.reset_index()
    df_h1.columns = [col.lower() for col in df_h1.columns]
    df_h1 = df_h1.rename(columns={'datetime': 'timestamp', 'date': 'timestamp'})
    
    return df_h1[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


def aggregate_to_h4(df_h1):
    """Agregar H1 para H4"""
    print("\n🔄 Agregando H1 → H4...")
    
    df_h1['timestamp'] = pd.to_datetime(df_h1['timestamp'])
    df_h1 = df_h1.set_index('timestamp')
    
    df_h4 = df_h1.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_h4 = df_h4.reset_index()
    
    print(f"  H4 candles criados: {len(df_h4):,}")
    
    return df_h4


def aggregate_to_d1(df_h1):
    """Agregar H1 para D1"""
    print("\n🔄 Agregando H1 → D1...")
    
    df_h1['timestamp'] = pd.to_datetime(df_h1['timestamp'])
    df_h1 = df_h1.set_index('timestamp')
    
    df_d1 = df_h1.resample('1D').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_d1 = df_d1.reset_index()
    
    print(f"  D1 candles criados: {len(df_d1):,}")
    
    return df_d1


def save_to_csv(df, timeframe):
    """Salvar dados em CSV"""
    output_file = OUTPUT_DIR / f"{SYMBOL}_{timeframe}_5years.csv"
    df.to_csv(output_file, index=False)
    
    size_mb = os.path.getsize(output_file) / (1024 * 1024)
    
    print(f"  ✅ Salvo: {output_file}")
    print(f"  📊 Tamanho: {size_mb:.2f} MB")
    print(f"  📈 Candles: {len(df):,}")
    print()


def main():
    """Função principal"""
    
    print("━" * 80)
    print("ETAPA 1: Download de dados H1")
    print("━" * 80)
    print()
    
    # Tentar Dukascopy primeiro (mais preciso)
    print("⚠️  AVISO: Dukascopy pode ser MUITO lento (horas/dias)")
    print("          Recomendo usar yfinance para pesquisa rápida")
    print()
    
    use_yfinance = input("Usar yfinance (rápido) em vez de Dukascopy (lento)? [S/n]: ").strip().lower()
    
    if use_yfinance != 'n':
        print("\n✅ Usando Yahoo Finance (yfinance) - RÁPIDO")
        print()
        df_h1 = download_via_yfinance_alternative(SYMBOL, START_DATE, END_DATE)
    else:
        print("\n⚠️  Usando Dukascopy - PODE DEMORAR DIAS!")
        print("    Pressione Ctrl+C para cancelar")
        time.sleep(3)
        df_h1 = download_dukascopy_ticks(SYMBOL, START_DATE, END_DATE)
    
    if df_h1.empty:
        print("\n❌ ERRO: Nenhum dado foi baixado!")
        return
    
    print("\n" + "=" * 80)
    print("📊 DADOS H1 BAIXADOS")
    print("=" * 80)
    print(f"Candles H1: {len(df_h1):,}")
    print(f"Período: {df_h1['timestamp'].min()} até {df_h1['timestamp'].max()}")
    print(f"Dias: {(df_h1['timestamp'].max() - df_h1['timestamp'].min()).days}")
    print()
    
    # Salvar H1
    save_to_csv(df_h1, 'H1')
    
    # Agregar para H4
    print("━" * 80)
    print("ETAPA 2: Agregação para H4")
    print("━" * 80)
    df_h4 = aggregate_to_h4(df_h1)
    save_to_csv(df_h4, 'H4')
    
    # Agregar para D1
    print("━" * 80)
    print("ETAPA 3: Agregação para D1")
    print("━" * 80)
    df_d1 = aggregate_to_d1(df_h1)
    save_to_csv(df_d1, 'D1')
    
    # Resumo final
    print("=" * 80)
    print("✅ DOWNLOAD CONCLUÍDO!")
    print("=" * 80)
    print()
    print(f"📁 Arquivos salvos em: {OUTPUT_DIR}")
    print()
    print(f"📊 H1: {len(df_h1):,} candles")
    print(f"📊 H4: {len(df_h4):,} candles")
    print(f"📊 D1: {len(df_d1):,} candles")
    print()
    print(f"📅 Período: {df_h1['timestamp'].min().date()} até {df_h1['timestamp'].max().date()}")
    print(f"⏱️  Anos: {(df_h1['timestamp'].max() - df_h1['timestamp'].min()).days / 365.25:.2f}")
    print()
    print("🎯 Próximo passo: Importar para PostgreSQL")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelado pelo usuário")
    except Exception as e:
        print(f"\n\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
