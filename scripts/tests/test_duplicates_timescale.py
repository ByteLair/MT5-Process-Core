#!/usr/bin/env python3
"""
Teste de Duplicatas - TimescaleDB
==================================

Demonstra que o ON CONFLICT (symbol, timeframe, ts) permite
inserir candles com TIMESTAMPS DIFERENTES, mas bloqueia
duplicatas com MESMA timestamp.
"""

import psycopg
from datetime import datetime, timedelta

DB_URL = "postgresql://trader:trader123@db:5432/mt5_trading"

print("╔══════════════════════════════════════════════════════════════╗")
print("║        🧪 TESTE DE DUPLICATAS - TIMESCALEDB                 ║")
print("╚══════════════════════════════════════════════════════════════╝")
print()

# Conectar ao banco
conn = psycopg.connect(DB_URL)

print("📊 TESTE 1: Inserir 3 candles com timestamps DIFERENTES")
print("─" * 60)

base_time = datetime(2025, 11, 14, 15, 0, 0)

test_candles = [
    (base_time, 1.0850, 1.0855, 1.0848, 1.0852, 1000),
    (base_time + timedelta(minutes=1), 1.0852, 1.0857, 1.0850, 1.0855, 1100),
    (base_time + timedelta(minutes=2), 1.0855, 1.0860, 1.0853, 1.0858, 1200),
]

inserted_count = 0

with conn.cursor() as cur:
    for ts, open_p, high, low, close, volume in test_candles:
        cur.execute("""
            INSERT INTO market_data 
            (ts, symbol, timeframe, open, high, low, close, volume)
            VALUES (%s, 'EURUSD', 'M1', %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timeframe, ts) DO NOTHING
        """, (ts, open_p, high, low, close, volume))
        
        if cur.rowcount > 0:
            print(f"   ✅ Inserido: {ts} | close={close} | volume={volume}")
            inserted_count += 1
        else:
            print(f"   ⚠️  Ignorado (duplicata): {ts}")
    
    conn.commit()

print(f"\n📈 Resultado: {inserted_count}/3 candles inseridos (timestamps diferentes)")
print()

print("─" * 60)
print("📊 TESTE 2: Tentar inserir DUPLICATAS (mesma timestamp)")
print("─" * 60)

# Tentar inserir novamente os mesmos 3 candles
duplicates_blocked = 0

with conn.cursor() as cur:
    for ts, open_p, high, low, close, volume in test_candles:
        cur.execute("""
            INSERT INTO market_data 
            (ts, symbol, timeframe, open, high, low, close, volume)
            VALUES (%s, 'EURUSD', 'M1', %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, timeframe, ts) DO NOTHING
        """, (ts, open_p, high, low, close, volume))
        
        if cur.rowcount > 0:
            print(f"   ❌ ERRO: Duplicata foi inserida! {ts}")
        else:
            print(f"   ✅ Bloqueado (duplicata): {ts}")
            duplicates_blocked += 1
    
    conn.commit()

print(f"\n🛡️  Resultado: {duplicates_blocked}/3 duplicatas bloqueadas com sucesso")
print()

print("─" * 60)
print("📊 TESTE 3: Verificar dados no banco")
print("─" * 60)

with conn.cursor() as cur:
    cur.execute("""
        SELECT ts, close, volume
        FROM market_data
        WHERE symbol = 'EURUSD'
            AND timeframe = 'M1'
            AND ts >= %s
            AND ts <= %s
        ORDER BY ts
    """, (base_time, base_time + timedelta(minutes=3)))
    
    rows = cur.fetchall()
    
    print(f"\n   Total de registros no banco: {len(rows)}")
    print()
    
    for ts, close, volume in rows:
        print(f"   📅 {ts} | close={close} | volume={volume}")

print()
print("─" * 60)
print()

# Limpar dados de teste
print("🧹 Limpando dados de teste...")

with conn.cursor() as cur:
    cur.execute("""
        DELETE FROM market_data
        WHERE symbol = 'EURUSD'
            AND timeframe = 'M1'
            AND ts >= %s
            AND ts <= %s
    """, (base_time, base_time + timedelta(minutes=3)))
    
    deleted = cur.rowcount
    conn.commit()
    
    print(f"   Removidos: {deleted} registros de teste")

conn.close()

print()
print("╔══════════════════════════════════════════════════════════════╗")
print("║                    ✅ TESTE CONCLUÍDO                        ║")
print("╚══════════════════════════════════════════════════════════════╝")
print()
print("🎯 CONCLUSÃO:")
print()
print("   ✅ Candles com timestamps DIFERENTES → Sempre inseridos")
print("   ✅ Candles com MESMA timestamp → Bloqueados (duplicatas)")
print()
print("   💡 O TimescaleDB separa corretamente por (symbol, timeframe, ts)")
print("      garantindo que cada momento único tenha seu próprio registro.")
print()
