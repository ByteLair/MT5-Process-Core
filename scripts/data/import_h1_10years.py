#!/usr/bin/env python3
"""
Importar 10 anos de dados H1 (2015-2025) para EURUSD.

Estratégia:
- H1 = 24 candles/dia
- 10 anos × 365 dias × 24 horas = ~87,600 candles
- Yahoo Finance tem dados desde 2015
"""
import os
import sys
import time
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

print("=" * 80)
print("📊 IMPORTANDO 10 ANOS DE DADOS H1 (2015-2025)")
print("=" * 80)

# Configuração do banco
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'mt5_db'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'mt5_trading'),
    'user': os.getenv('POSTGRES_USER', 'trader'),
    'password': os.getenv('POSTGRES_PASSWORD', 'trader_password')
}

connection_string = (
    f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
    f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
)

engine = create_engine(connection_string)
Session = sessionmaker(bind=engine)

# Datas
START_DATE = '2015-01-01'
END_DATE = '2025-11-14'

print(f"\n📅 Período: {START_DATE} até {END_DATE}")
print(f"   Estimativa: ~87,600 candles H1\n")

# Baixar dados do Yahoo Finance
print("🌐 Baixando dados do Yahoo Finance (EURUSD=X)...")
ticker = yf.Ticker("EURUSD=X")

try:
    # Baixar dados por ano para evitar timeouts
    all_data = []
    
    start_year = 2015
    end_year = 2025
    
    for year in range(start_year, end_year + 1):
        year_start = f"{year}-01-01"
        year_end = f"{year}-12-31" if year < 2025 else END_DATE
        
        print(f"   📥 Baixando {year}... ", end='', flush=True)
        
        try:
            df_year = ticker.history(
                start=year_start,
                end=year_end,
                interval='1h',
                auto_adjust=True
            )
            
            if len(df_year) > 0:
                all_data.append(df_year)
                print(f"✅ {len(df_year):,} candles")
            else:
                print(f"⚠️  Sem dados")
                
        except Exception as e:
            print(f"❌ Erro: {str(e)[:50]}")
            continue
        
        time.sleep(1)  # Rate limiting
    
    if not all_data:
        print("\n❌ ERRO: Nenhum dado baixado!")
        sys.exit(1)
    
    # Concatenar todos os anos
    df = pd.concat(all_data)
    df = df.sort_index()
    
    print(f"\n✅ Total baixado: {len(df):,} candles H1")
    print(f"   Período: {df.index.min()} até {df.index.max()}")
    
except Exception as e:
    print(f"\n❌ ERRO ao baixar: {str(e)}")
    sys.exit(1)

# Preparar dados para inserção
print("\n🔧 Preparando dados para inserção...")

df_insert = pd.DataFrame({
    'ts': df.index,
    'symbol': 'EURUSD',
    'timeframe': 'H1',
    'open': df['Open'],
    'high': df['High'],
    'low': df['Low'],
    'close': df['Close'],
    'volume': df['Volume'],
    'spread': 0.00015,  # 1.5 pips típico
    'bid': df['Close'] - 0.00015,
    'ask': df['Close'] + 0.00015,
})

# Remover duplicatas e NaN
df_insert = df_insert.dropna()
df_insert = df_insert.drop_duplicates(subset=['ts'])

print(f"   ✅ {len(df_insert):,} candles prontos para inserção")

# Inserir no banco em batches
print("\n💾 Inserindo no banco de dados...")

BATCH_SIZE = 1000
total_inserted = 0
session = Session()

try:
    # Deletar dados H1 existentes
    print("   🗑️  Removendo dados H1 antigos...")
    session.execute(text("""
        DELETE FROM market_data 
        WHERE symbol = 'EURUSD' AND timeframe = 'H1'
    """))
    session.commit()
    print("   ✅ Dados antigos removidos")
    
    # Inserir novos dados em batches
    for i in range(0, len(df_insert), BATCH_SIZE):
        batch = df_insert.iloc[i:i+BATCH_SIZE]
        
        # Usar executemany para performance
        records = batch.to_dict('records')
        
        session.execute(text("""
            INSERT INTO market_data (
                ts, symbol, timeframe, open, high, low, close,
                volume, spread, bid, ask
            ) VALUES (
                :ts, :symbol, :timeframe, :open, :high, :low, :close,
                :volume, :spread, :bid, :ask
            )
            ON CONFLICT (symbol, timeframe, ts) DO NOTHING
        """), records)
        
        session.commit()
        total_inserted += len(batch)
        
        progress = (i + len(batch)) / len(df_insert) * 100
        print(f"   📊 Progresso: {progress:.1f}% ({total_inserted:,}/{len(df_insert):,})", end='\r', flush=True)
    
    print(f"\n   ✅ {total_inserted:,} candles inseridos com sucesso!")
    
    # Verificar inserção
    result = session.execute(text("""
        SELECT 
            COUNT(*) as total,
            MIN(ts) as first_date,
            MAX(ts) as last_date
        FROM market_data
        WHERE symbol = 'EURUSD' AND timeframe = 'H1'
    """)).fetchone()
    
    print(f"\n📊 DADOS NO BANCO:")
    print(f"   Total: {result.total:,} candles H1")
    print(f"   Período: {result.first_date} até {result.last_date}")
    
    # Estatísticas
    years = (result.last_date - result.first_date).days / 365.25
    avg_per_year = result.total / years if years > 0 else 0
    
    print(f"\n📈 ESTATÍSTICAS:")
    print(f"   Anos de dados: {years:.1f}")
    print(f"   Candles/ano: {avg_per_year:,.0f}")
    print(f"   Candles/dia: {result.total / (result.last_date - result.first_date).days:.1f}")
    
except Exception as e:
    print(f"\n❌ ERRO ao inserir: {str(e)}")
    session.rollback()
    sys.exit(1)
finally:
    session.close()

print("\n" + "=" * 80)
print("✅ IMPORTAÇÃO CONCLUÍDA!")
print("=" * 80)
print("\n🎯 PRÓXIMOS PASSOS:")
print("   1. Calcular indicadores H1 (scripts/indicators/calculate_h1.py)")
print("   2. Treinar modelo com H1 (scripts/ml/train_h1_model.py)")
print("   3. Backtest com regras conservadoras")
print("=" * 80)
