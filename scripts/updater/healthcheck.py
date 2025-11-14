#!/usr/bin/env python3
"""
Healthcheck para container forex-updater.
Verifica se o banco está acessível e dados estão sendo atualizados.
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mt5_trading")
DB_USER = os.getenv("DB_USER", "trader")
DB_PASS = os.getenv("DB_PASS", "trader123")

DB_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def check_health():
    """Verifica saúde do serviço."""
    try:
        engine = create_engine(DB_URL, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # Verificar se banco responde
            conn.execute(text("SELECT 1"))
            
            # Verificar idade dos dados
            result = conn.execute(
                text("SELECT MAX(ts) FROM market_data WHERE symbol='EURUSD' AND timeframe='M1'")
            )
            last_ts = result.scalar()
            
            if last_ts:
                age = datetime.now() - last_ts.replace(tzinfo=None)
                
                # Alerta se dados têm mais de 24 horas
                if age > timedelta(hours=24):
                    print(f"⚠️  WARNING: Dados desatualizados ({age})")
                    sys.exit(1)
                else:
                    print(f"✅ Healthy - Última atualização: {age} atrás")
                    sys.exit(0)
            else:
                print("⚠️  WARNING: Nenhum dado encontrado")
                sys.exit(1)
                
    except Exception as e:
        print(f"❌ UNHEALTHY: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_health()
