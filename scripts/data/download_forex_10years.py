#!/usr/bin/env python3
"""
Download de dados históricos FOREX (10 anos)
Baixa H4 e D1 diretamente usando yfinance (rápido e confiável)
Salva direto no PostgreSQL

Autor: MT5-Process-Core
Data: 2025-11-15
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import yfinance as yf
import time
from pathlib import Path
import sys

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ══════════════════════════════════════════════════════════════════════════════

SYMBOL = "EURUSD=X"  # Yahoo Finance ticker para EUR/USD
PAIR = "EURUSD"
YEARS = 10
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=YEARS * 365)

# Conexão PostgreSQL
DB_HOST = "mt5_db"
DB_PORT = "5432"
DB_NAME = "mt5_trading"
DB_USER = "trader"
DB_PASS = "trader123"

CONNECTION_STRING = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════

def download_data(symbol: str, start: datetime, end: datetime, interval: str) -> pd.DataFrame:
    """
    Baixa dados históricos do Yahoo Finance
    
    Args:
        symbol: Ticker do Yahoo Finance (EURUSD=X)
        start: Data inicial
        end: Data final
        interval: '1h' para H1, '1d' para D1
    
    Returns:
        DataFrame com dados OHLCV
    """
    print(f"📥 Baixando {interval} de {start.date()} até {end.date()}...")
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start, end=end, interval=interval, auto_adjust=False)
        
        if df.empty:
            print(f"   ⚠️  Nenhum dado retornado")
            return pd.DataFrame()
        
        # Renomear colunas para padrão
        df = df.reset_index()
        df.columns = df.columns.str.lower()
        
        # Ajustar nome da coluna de timestamp
        if 'datetime' in df.columns:
            df.rename(columns={'datetime': 'timestamp'}, inplace=True)
        elif 'date' in df.columns:
            df.rename(columns={'date': 'timestamp'}, inplace=True)
        
        # Garantir timezone UTC
        if df['timestamp'].dt.tz is None:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize('UTC')
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('UTC')
        
        # Selecionar e ordenar colunas
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"   ✅ Baixados {len(df):,} candles")
        print(f"   📅 {df['timestamp'].min()} até {df['timestamp'].max()}")
        
        return df
        
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        return pd.DataFrame()


def save_to_database(df: pd.DataFrame, timeframe: str, symbol: str = PAIR):
    """
    Salva dados no PostgreSQL
    
    Args:
        df: DataFrame com dados OHLCV
        timeframe: 'H4' ou 'D1'
        symbol: Par de moedas (EURUSD)
    """
    if df.empty:
        print(f"   ⚠️  DataFrame vazio, nada para salvar")
        return
    
    print(f"💾 Salvando {len(df):,} candles {timeframe} no PostgreSQL...")
    
    try:
        engine = create_engine(CONNECTION_STRING)
        
        # Adicionar colunas necessárias
        df_save = df.copy()
        df_save['symbol'] = symbol
        df_save['timeframe'] = timeframe
        df_save['ts'] = df_save['timestamp']
        
        # Remover duplicatas antes de inserir
        with engine.connect() as conn:
            # Deletar dados existentes desse timeframe
            delete_query = text("""
                DELETE FROM market_data 
                WHERE symbol = :symbol 
                  AND timeframe = :timeframe
            """)
            result = conn.execute(delete_query, {'symbol': symbol, 'timeframe': timeframe})
            deleted = result.rowcount
            conn.commit()
            
            if deleted > 0:
                print(f"   🗑️  Removidos {deleted} candles antigos")
        
        # Inserir novos dados
        df_save.to_sql(
            'market_data',
            engine,
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )
        
        print(f"   ✅ {len(df):,} candles salvos com sucesso!")
        
        # Verificar
        with engine.connect() as conn:
            verify_query = text("""
                SELECT COUNT(*) as total,
                       MIN(ts) as min_date,
                       MAX(ts) as max_date
                FROM market_data
                WHERE symbol = :symbol AND timeframe = :timeframe
            """)
            result = conn.execute(verify_query, {'symbol': symbol, 'timeframe': timeframe})
            row = result.fetchone()
            
            print(f"   📊 Verificação: {row[0]:,} candles no banco")
            print(f"   📅 Período: {row[1]} até {row[2]}")
        
        engine.dispose()
        
    except Exception as e:
        print(f"   ❌ ERRO ao salvar: {e}")
        import traceback
        traceback.print_exc()


def aggregate_h1_to_h4(df_h1: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega dados H1 para H4
    
    Args:
        df_h1: DataFrame com dados H1
    
    Returns:
        DataFrame com dados H4
    """
    print(f"🔄 Agregando H1 → H4...")
    
    df = df_h1.copy()
    df.set_index('timestamp', inplace=True)
    
    # Resample para 4 horas
    df_h4 = df.resample('4H').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_h4 = df_h4.reset_index()
    
    print(f"   ✅ {len(df_h4):,} candles H4 criados")
    
    return df_h4


# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Função principal"""
    
    print("=" * 80)
    print("📊 DOWNLOAD DE DADOS HISTÓRICOS FOREX - 10 ANOS")
    print("=" * 80)
    print()
    print(f"Par: {PAIR} ({SYMBOL})")
    print(f"Período: {START_DATE.date()} até {END_DATE.date()}")
    print(f"Anos: {YEARS}")
    print(f"Timeframes: H1, H4, D1")
    print(f"Destino: PostgreSQL ({DB_HOST})")
    print()
    print("=" * 80)
    print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 1: Download H1 (10 anos)
    # ─────────────────────────────────────────────────────────────────────────
    
    print("🔹 ETAPA 1/4: Download H1")
    print("─" * 80)
    
    df_h1 = download_data(SYMBOL, START_DATE, END_DATE, interval='1h')
    
    if df_h1.empty:
        print("\n❌ ERRO: Não foi possível baixar dados H1!")
        print("💡 Dica: Verifique conexão com internet e disponibilidade do Yahoo Finance")
        return
    
    print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 2: Agregar H4
    # ─────────────────────────────────────────────────────────────────────────
    
    print("🔹 ETAPA 2/4: Agregação H1 → H4")
    print("─" * 80)
    
    df_h4 = aggregate_h1_to_h4(df_h1)
    print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 3: Download D1 (10 anos)
    # ─────────────────────────────────────────────────────────────────────────
    
    print("🔹 ETAPA 3/4: Download D1")
    print("─" * 80)
    
    df_d1 = download_data(SYMBOL, START_DATE, END_DATE, interval='1d')
    
    if df_d1.empty:
        print("   ⚠️  Falha no download D1, mas continuando...")
    
    print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # ETAPA 4: Salvar no PostgreSQL
    # ─────────────────────────────────────────────────────────────────────────
    
    print("🔹 ETAPA 4/4: Salvando no PostgreSQL")
    print("─" * 80)
    print()
    
    # Salvar H1
    print("💾 H1:")
    save_to_database(df_h1, 'H1')
    print()
    
    # Salvar H4
    print("💾 H4:")
    save_to_database(df_h4, 'H4')
    print()
    
    # Salvar D1
    if not df_d1.empty:
        print("💾 D1:")
        save_to_database(df_d1, 'D1')
        print()
    
    # ─────────────────────────────────────────────────────────────────────────
    # RESUMO FINAL
    # ─────────────────────────────────────────────────────────────────────────
    
    print("=" * 80)
    print("✅ DOWNLOAD E IMPORTAÇÃO CONCLUÍDOS!")
    print("=" * 80)
    print()
    print("📊 RESUMO:")
    print(f"   • H1: {len(df_h1):,} candles")
    print(f"   • H4: {len(df_h4):,} candles")
    print(f"   • D1: {len(df_d1):,} candles" if not df_d1.empty else "   • D1: 0 candles (falha)")
    print()
    print(f"📅 Período: {df_h1['timestamp'].min().date()} até {df_h1['timestamp'].max().date()}")
    print(f"⏱️  Anos: {(df_h1['timestamp'].max() - df_h1['timestamp'].min()).days / 365.25:.2f}")
    print()
    print("🎯 Próximos passos:")
    print("   1. Calcular indicadores técnicos (RSI, MACD, BB, ATR, EMA, ADX)")
    print("   2. Criar features multi-timeframe")
    print("   3. Treinar modelo com 10 anos de dados")
    print("   4. Backtest e validação")
    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelado pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
