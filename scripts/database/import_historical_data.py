#!/usr/bin/env python3
"""
Importação Otimizada de Dados Históricos
========================================

Importa dados do CSV (dados_historicos.csv) para a tabela market_data
com otimizações de performance para 24k+ registros.

Features:
- Batch insert (1000 registros por vez)
- Validação de dados
- Progress bar
- Estatísticas de importação
- Rollback automático em caso de erro

Uso:
    python scripts/database/import_historical_data.py
    python scripts/database/import_historical_data.py --dry-run
    python scripts/database/import_historical_data.py --symbol EURUSD --timeframe H1
"""

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import psycopg
from psycopg import Connection


# Configurações
CSV_PATH = Path("/app/dados_historicos.csv")
DB_CONFIG = {
    "host": "pgbouncer",  # Nome do serviço no Docker
    "port": 5432,
    "dbname": "mt5_trading",
    "user": "trader",
    "password": "trader123"
}
BATCH_SIZE = 1000
DEFAULT_SYMBOL = "EURUSD"
DEFAULT_TIMEFRAME = "H1"


def parse_csv_row(row: dict, symbol: str, timeframe: str) -> Tuple:
    """Converte linha do CSV para tupla SQL."""
    # Combinar Date e Time em timestamp
    date_str = row["Date"]
    time_str = row["Time"]
    timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y.%m.%d %H:%M")
    
    return (
        timestamp,
        symbol,
        timeframe,
        float(row["Open"]),
        float(row["High"]),
        float(row["Low"]),
        float(row["Close"]),
        float(row["Volume"]),
        None,  # spread
        None,  # bid
        None,  # ask
        None,  # rsi
        None,  # macd
        None,  # macd_signal
        None,  # macd_hist
        None,  # atr
        None,  # bb_upper
        None,  # bb_middle
        None,  # bb_lower
    )


def validate_csv(csv_path: Path) -> dict:
    """Valida e analisa o CSV antes da importação."""
    print(f"📊 Validando CSV: {csv_path}")
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV não encontrado: {csv_path}")
    
    stats = {
        "total_rows": 0,
        "first_date": None,
        "last_date": None,
        "min_volume": float("inf"),
        "max_volume": 0,
        "errors": []
    }
    
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            try:
                date_str = f"{row['Date']} {row['Time']}"
                ts = datetime.strptime(date_str, "%Y.%m.%d %H:%M")
                volume = float(row["Volume"])
                
                if stats["first_date"] is None:
                    stats["first_date"] = ts
                stats["last_date"] = ts
                stats["min_volume"] = min(stats["min_volume"], volume)
                stats["max_volume"] = max(stats["max_volume"], volume)
                stats["total_rows"] = idx
                
            except Exception as e:
                stats["errors"].append(f"Linha {idx}: {e}")
                if len(stats["errors"]) > 10:
                    break
    
    return stats


def import_data(
    conn: Connection,
    csv_path: Path,
    symbol: str,
    timeframe: str,
    dry_run: bool = False
) -> dict:
    """Importa dados do CSV para o banco."""
    
    print(f"\n🚀 Iniciando importação...")
    print(f"   CSV: {csv_path.name}")
    print(f"   Symbol: {symbol}")
    print(f"   Timeframe: {timeframe}")
    print(f"   Modo: {'DRY RUN' if dry_run else 'PRODUÇÃO'}")
    
    stats = {
        "total": 0,
        "inserted": 0,
        "duplicates": 0,
        "errors": 0,
        "start_time": datetime.now()
    }
    
    batch = []
    
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        
        for idx, row in enumerate(reader, start=1):
            try:
                data = parse_csv_row(row, symbol, timeframe)
                batch.append(data)
                stats["total"] += 1
                
                # Inserir em lotes
                if len(batch) >= BATCH_SIZE:
                    if not dry_run:
                        inserted, dups = insert_batch(conn, batch)
                        stats["inserted"] += inserted
                        stats["duplicates"] += dups
                    
                    # Progress
                    print(f"   Processados: {stats['total']:,} registros...", end="\r")
                    batch = []
                
            except Exception as e:
                stats["errors"] += 1
                print(f"\n⚠️  Erro na linha {idx}: {e}")
                if stats["errors"] > 100:
                    print("❌ Muitos erros! Abortando importação.")
                    raise
        
        # Inserir registros restantes
        if batch and not dry_run:
            inserted, dups = insert_batch(conn, batch)
            stats["inserted"] += inserted
            stats["duplicates"] += dups
    
    stats["end_time"] = datetime.now()
    stats["duration"] = (stats["end_time"] - stats["start_time"]).total_seconds()
    
    return stats


def insert_batch(conn: Connection, batch: List[Tuple]) -> Tuple[int, int]:
    """Insere lote de registros usando ON CONFLICT."""
    
    query = """
        INSERT INTO market_data (
            ts, symbol, timeframe,
            open, high, low, close, volume,
            spread, bid, ask,
            rsi, macd, macd_signal, macd_hist, atr,
            bb_upper, bb_middle, bb_lower
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (symbol, timeframe, ts) DO NOTHING
    """
    
    with conn.cursor() as cur:
        # Executar batch insert
        cur.executemany(query, batch)
        inserted = cur.rowcount
        duplicates = len(batch) - inserted
    
    return inserted, duplicates


def print_stats(validation_stats: dict, import_stats: dict = None):
    """Imprime estatísticas da importação."""
    
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS DA IMPORTAÇÃO")
    print("="*70)
    
    # Validação
    print("\n🔍 Validação do CSV:")
    print(f"   Total de registros: {validation_stats['total_rows']:,}")
    print(f"   Período: {validation_stats['first_date']} até {validation_stats['last_date']}")
    
    if validation_stats['first_date'] and validation_stats['last_date']:
        days = (validation_stats['last_date'] - validation_stats['first_date']).days
        print(f"   Duração: {days} dias (~{days/365:.1f} anos)")
    
    print(f"   Volume mín: {validation_stats['min_volume']:,.0f}")
    print(f"   Volume máx: {validation_stats['max_volume']:,.0f}")
    
    if validation_stats['errors']:
        print(f"\n   ⚠️  Erros de validação: {len(validation_stats['errors'])}")
        for err in validation_stats['errors'][:5]:
            print(f"      - {err}")
    
    # Importação
    if import_stats:
        print("\n💾 Importação:")
        print(f"   Registros processados: {import_stats['total']:,}")
        print(f"   Inseridos: {import_stats['inserted']:,}")
        print(f"   Duplicados (ignorados): {import_stats['duplicates']:,}")
        print(f"   Erros: {import_stats['errors']:,}")
        print(f"   Duração: {import_stats['duration']:.2f}s")
        
        if import_stats['duration'] > 0:
            rate = import_stats['total'] / import_stats['duration']
            print(f"   Taxa: {rate:,.0f} registros/segundo")
        
        success_rate = (import_stats['inserted'] / import_stats['total'] * 100) if import_stats['total'] > 0 else 0
        print(f"   Taxa de sucesso: {success_rate:.1f}%")
    
    print("="*70)


def verify_import(conn: Connection, symbol: str, timeframe: str):
    """Verifica dados importados."""
    
    print("\n🔍 Verificando importação...")
    
    with conn.cursor() as cur:
        # Total de registros
        cur.execute(
            "SELECT COUNT(*) FROM market_data WHERE symbol = %s AND timeframe = %s",
            (symbol, timeframe)
        )
        total = cur.fetchone()[0]
        print(f"   ✅ Total de registros: {total:,}")
        
        # Período
        cur.execute(
            """
            SELECT MIN(ts) as first_date, MAX(ts) as last_date
            FROM market_data
            WHERE symbol = %s AND timeframe = %s
            """,
            (symbol, timeframe)
        )
        first, last = cur.fetchone()
        print(f"   ✅ Período: {first} até {last}")
        
        # Gaps (intervalos faltantes)
        cur.execute(
            """
            WITH time_series AS (
                SELECT
                    ts,
                    LAG(ts) OVER (ORDER BY ts) as prev_ts,
                    ts - LAG(ts) OVER (ORDER BY ts) as gap
                FROM market_data
                WHERE symbol = %s AND timeframe = %s
            )
            SELECT COUNT(*) as gaps
            FROM time_series
            WHERE gap > INTERVAL '2 hours'
            """,
            (symbol, timeframe)
        )
        gaps = cur.fetchone()[0]
        if gaps > 0:
            print(f"   ⚠️  Gaps detectados: {gaps} (intervalos > 2h)")
        else:
            print(f"   ✅ Sem gaps detectados")
        
        # Sample de dados
        cur.execute(
            """
            SELECT ts, open, high, low, close, volume
            FROM market_data
            WHERE symbol = %s AND timeframe = %s
            ORDER BY ts DESC
            LIMIT 3
            """,
            (symbol, timeframe)
        )
        print(f"\n   📊 Sample dos últimos 3 registros:")
        for row in cur.fetchall():
            print(f"      {row[0]} | O:{row[1]:.5f} H:{row[2]:.5f} L:{row[3]:.5f} C:{row[4]:.5f} V:{row[5]:.0f}")


def main():
    """Função principal."""
    
    # Parse argumentos simples
    dry_run = "--dry-run" in sys.argv
    symbol = DEFAULT_SYMBOL
    timeframe = DEFAULT_TIMEFRAME
    
    for i, arg in enumerate(sys.argv):
        if arg == "--symbol" and i + 1 < len(sys.argv):
            symbol = sys.argv[i + 1]
        if arg == "--timeframe" and i + 1 < len(sys.argv):
            timeframe = sys.argv[i + 1]
    
    print("="*70)
    print("🗄️  IMPORTAÇÃO DE DADOS HISTÓRICOS")
    print("="*70)
    
    try:
        # Validar CSV
        validation_stats = validate_csv(CSV_PATH)
        
        if validation_stats['errors']:
            print(f"\n⚠️  {len(validation_stats['errors'])} erros de validação encontrados!")
            print("Continuar mesmo assim? (s/N): ", end="")
            if input().lower() != "s":
                print("❌ Importação cancelada.")
                return 1
        
        # Conectar ao banco
        print(f"\n🔌 Conectando ao banco via PgBouncer...")
        conn_str = (
            f"host={DB_CONFIG['host']} "
            f"port={DB_CONFIG['port']} "
            f"dbname={DB_CONFIG['dbname']} "
            f"user={DB_CONFIG['user']} "
            f"password={DB_CONFIG['password']}"
        )
        
        with psycopg.connect(conn_str, autocommit=False) as conn:
            print("   ✅ Conectado!")
            
            # Importar dados
            import_stats = import_data(conn, CSV_PATH, symbol, timeframe, dry_run)
            
            if not dry_run:
                # Commit
                conn.commit()
                print("\n✅ Transação commitada!")
                
                # Verificar importação
                verify_import(conn, symbol, timeframe)
            else:
                conn.rollback()
                print("\n⚠️  DRY RUN - Transação revertida (nenhum dado salvo)")
            
            # Estatísticas finais
            print_stats(validation_stats, import_stats)
        
        print("\n🎉 Importação concluída com sucesso!")
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Importação cancelada pelo usuário.")
        return 130
    
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
