#!/usr/bin/env python3
"""
Script de Teste Completo do Banco de Dados MT5-Process-Core
"""
import psycopg
from datetime import datetime, timedelta
import time

def test_direct_connection():
    """Testa conexão direta com PostgreSQL"""
    print("=" * 60)
    print("🔍 TESTE 1: Conexão Direta com PostgreSQL")
    print("=" * 60)
    
    try:
        conn = psycopg.connect(
            "host=db port=5432 dbname=mt5_trading user=trader password=trader123",
            connect_timeout=5
        )
        print("✅ Conexão estabelecida com sucesso!")
        
        with conn.cursor() as cur:
            # Versão do PostgreSQL
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            print(f"✅ PostgreSQL Version: {version[:80]}...")
            
            # Extensões instaladas
            cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'timescaledb'")
            ext = cur.fetchone()
            if ext:
                print(f"✅ TimescaleDB Version: {ext[1]}")
            
            # Contar registros
            cur.execute("SELECT COUNT(*) FROM signals")
            signals_count = cur.fetchone()[0]
            print(f"✅ Total de signals: {signals_count}")
            
            cur.execute("SELECT COUNT(*) FROM market_data_raw")
            raw_count = cur.fetchone()[0]
            print(f"✅ Total de market_data_raw: {raw_count}")
            
        conn.close()
        print("✅ Teste 1: PASSOU\n")
        return True
    except Exception as e:
        print(f"❌ Erro no Teste 1: {e}\n")
        return False


def test_pgbouncer_connection():
    """Testa conexão via PgBouncer"""
    print("=" * 60)
    print("🔍 TESTE 2: Conexão via PgBouncer")
    print("=" * 60)
    
    try:
        conn = psycopg.connect(
            "host=pgbouncer port=5432 dbname=mt5_trading user=trader password=trader123",
            connect_timeout=5
        )
        print("✅ Conexão via PgBouncer estabelecida!")
        
        with conn.cursor() as cur:
            # Query simples
            cur.execute("SELECT symbol, timeframe, prob_up, label FROM signals ORDER BY ts DESC LIMIT 3")
            rows = cur.fetchall()
            print(f"✅ Últimos 3 signals recuperados:")
            for row in rows:
                print(f"   - {row[0]} {row[1]}: prob={row[2]:.2f}, label={row[3]}")
            
            # Agregação
            cur.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as total,
                    AVG(prob_up) as avg_prob
                FROM signals
                GROUP BY symbol
                ORDER BY total DESC
            """)
            agg = cur.fetchall()
            print(f"✅ Agregação por símbolo:")
            for row in agg:
                print(f"   - {row[0]}: {row[1]} signals, avg_prob={row[2]:.3f}")
        
        conn.close()
        print("✅ Teste 2: PASSOU\n")
        return True
    except Exception as e:
        print(f"❌ Erro no Teste 2: {e}\n")
        return False


def test_write_performance():
    """Testa performance de escrita"""
    print("=" * 60)
    print("🔍 TESTE 3: Performance de Escrita")
    print("=" * 60)
    
    try:
        conn = psycopg.connect(
            "host=pgbouncer port=5432 dbname=mt5_trading user=trader password=trader123"
        )
        
        # Inserir 100 registros
        start_time = time.time()
        with conn.cursor() as cur:
            for i in range(100):
                ts = datetime.now() - timedelta(minutes=i)
                cur.execute("""
                    INSERT INTO signals (ts, symbol, timeframe, prob_up, label)
                    VALUES (%s, %s, %s, %s, %s)
                """, (ts, 'TEST', 'M1', 0.5 + (i % 50) / 100, i % 2))
            conn.commit()
        
        elapsed = time.time() - start_time
        print(f"✅ Inseridos 100 registros em {elapsed:.3f}s")
        print(f"✅ Taxa: {100/elapsed:.1f} inserts/segundo")
        
        # Verificar
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM signals WHERE symbol = 'TEST'")
            count = cur.fetchone()[0]
            print(f"✅ Total de registros TEST: {count}")
        
        conn.close()
        print("✅ Teste 3: PASSOU\n")
        return True
    except Exception as e:
        print(f"❌ Erro no Teste 3: {e}\n")
        return False


def test_read_performance():
    """Testa performance de leitura"""
    print("=" * 60)
    print("🔍 TESTE 4: Performance de Leitura")
    print("=" * 60)
    
    try:
        conn = psycopg.connect(
            "host=pgbouncer port=5432 dbname=mt5_trading user=trader password=trader123"
        )
        
        # Query complexa 100 vezes
        start_time = time.time()
        for _ in range(100):
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        symbol,
                        timeframe,
                        AVG(prob_up) as avg_prob,
                        COUNT(*) as total
                    FROM signals
                    WHERE ts > NOW() - INTERVAL '1 hour'
                    GROUP BY symbol, timeframe
                """)
                rows = cur.fetchall()
        
        elapsed = time.time() - start_time
        print(f"✅ 100 queries complexas em {elapsed:.3f}s")
        print(f"✅ Taxa: {100/elapsed:.1f} queries/segundo")
        print(f"✅ Latência média: {elapsed*10:.1f}ms por query")
        
        conn.close()
        print("✅ Teste 4: PASSOU\n")
        return True
    except Exception as e:
        print(f"❌ Erro no Teste 4: {e}\n")
        return False


def test_timescaledb_features():
    """Testa features do TimescaleDB"""
    print("=" * 60)
    print("🔍 TESTE 5: Features do TimescaleDB")
    print("=" * 60)
    
    try:
        conn = psycopg.connect(
            "host=db port=5432 dbname=mt5_trading user=trader password=trader123"
        )
        
        with conn.cursor() as cur:
            # Verificar hypertables
            cur.execute("""
                SELECT hypertable_name, num_chunks, compression_enabled
                FROM timescaledb_information.hypertables
            """)
            hypertables = cur.fetchall()
            print(f"✅ Hypertables encontradas: {len(hypertables)}")
            for ht in hypertables:
                compression = "✓" if ht[2] else "✗"
                print(f"   - {ht[0]}: {ht[1]} chunks, compression={compression}")
            
            # Tamanho das tabelas
            cur.execute("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size('public.'||tablename)) as size
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size('public.'||tablename) DESC
            """)
            sizes = cur.fetchall()
            print(f"\n✅ Tamanho das tabelas:")
            for size in sizes:
                print(f"   - {size[0]}: {size[1]}")
        
        conn.close()
        print("✅ Teste 5: PASSOU\n")
        return True
    except Exception as e:
        print(f"❌ Erro no Teste 5: {e}\n")
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "=" * 60)
    print("🚀 INICIANDO TESTES DO BANCO DE DADOS")
    print("=" * 60 + "\n")
    
    results = []
    
    # Executar testes
    results.append(("Conexão Direta PostgreSQL", test_direct_connection()))
    results.append(("Conexão via PgBouncer", test_pgbouncer_connection()))
    results.append(("Performance de Escrita", test_write_performance()))
    results.append(("Performance de Leitura", test_read_performance()))
    results.append(("Features TimescaleDB", test_timescaledb_features()))
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status} - {name}")
    
    print("\n" + "-" * 60)
    print(f"Total: {passed}/{total} testes passaram ({passed*100//total}%)")
    print("=" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
