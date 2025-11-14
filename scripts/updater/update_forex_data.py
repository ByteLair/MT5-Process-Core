#!/usr/bin/env python3
"""
Atualização Automática de Dados Forex - Container Dedicado
===========================================================

Detecta último candle no banco e atualiza automaticamente com dados novos.
Otimizado para rodar a cada 6 horas via cron.

Features:
- Detecção automática de última timestamp
- Download incremental (apenas dados novos)
- Prevenção de duplicatas (ON CONFLICT)
- Logs detalhados
- Retry logic com backoff exponencial
- Notificações de erro
"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Configurar logging
log_file = "/var/log/forex-updater/update.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuração do banco
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mt5_trading")
DB_USER = os.getenv("DB_USER", "trader")
DB_PASS = os.getenv("DB_PASS", "trader123")

DB_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Configurações
SYMBOL = os.getenv("FOREX_SYMBOL", "EURUSD")
TIMEFRAME = os.getenv("FOREX_TIMEFRAME", "M1")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "60"))  # segundos


def get_last_candle_timestamp(symbol: str, timeframe: str, retries: int = MAX_RETRIES) -> datetime:
    """
    Busca a última timestamp de candle no banco.
    Implementa retry com backoff exponencial.
    """
    for attempt in range(retries):
        try:
            engine = create_engine(DB_URL, pool_pre_ping=True, pool_size=5)
            
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT MAX(ts) as last_ts 
                        FROM market_data 
                        WHERE symbol = :symbol AND timeframe = :timeframe
                    """),
                    {"symbol": symbol, "timeframe": timeframe}
                )
                row = result.fetchone()
                
                if row and row[0]:
                    last_ts = row[0]
                    logger.info(f"📅 Último candle no banco: {last_ts}")
                    logger.info(f"⏱️  Idade dos dados: {(datetime.now(last_ts.tzinfo) - last_ts)}")
                    return last_ts
                else:
                    logger.warning("⚠️  Nenhum dado encontrado no banco")
                    # Se não há dados, começar de 7 dias atrás (limite Yahoo Finance)
                    return datetime.now() - timedelta(days=7)
                    
        except Exception as e:
            wait_time = RETRY_DELAY * (2 ** attempt)
            logger.error(f"❌ Erro ao consultar banco (tentativa {attempt + 1}/{retries}): {e}")
            
            if attempt < retries - 1:
                logger.info(f"⏳ Aguardando {wait_time}s antes de tentar novamente...")
                time.sleep(wait_time)
            else:
                logger.error("❌ Todas as tentativas falharam!")
                raise
        finally:
            if 'engine' in locals():
                engine.dispose()


def download_new_candles(symbol: str, last_ts: datetime, max_days: int = 7) -> pd.DataFrame:
    """
    Baixa apenas candles novos após a última timestamp.
    Yahoo Finance limita M1 a 7 dias.
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("❌ yfinance não instalado!")
        sys.exit(1)
    
    # Calcular período a baixar
    now = datetime.now()
    days_missing = (now - last_ts.replace(tzinfo=None)).days
    
    logger.info(f"📊 Status dos dados:")
    logger.info(f"   Última atualização: {last_ts}")
    logger.info(f"   Dias desde última atualização: {days_missing}")
    
    if days_missing == 0:
        logger.info("✅ Dados já estão atualizados!")
        return pd.DataFrame()
    
    # Yahoo Finance: limite M1 = 7 dias
    if days_missing > max_days:
        logger.warning(f"⚠️  {days_missing} dias faltando, mas Yahoo Finance limita M1 a {max_days} dias")
        logger.info(f"💡 Baixando apenas últimos {max_days} dias")
        days_to_download = max_days
    else:
        days_to_download = days_missing
    
    # Download
    logger.info(f"📥 Baixando novos dados...")
    logger.info(f"   Símbolo: {symbol}=X")
    logger.info(f"   Período: últimos {days_to_download} dias")
    logger.info(f"   Intervalo: 1m")
    
    try:
        yahoo_symbol = f"{symbol}=X"
        ticker = yf.Ticker(yahoo_symbol)
        
        df = ticker.history(
            period=f"{days_to_download}d",
            interval="1m",
            auto_adjust=False,
            actions=False
        )
        
        if df.empty:
            logger.warning("⚠️  Yahoo Finance não retornou dados")
            return pd.DataFrame()
        
        # Filtrar apenas dados APÓS última timestamp
        df = df[df.index > last_ts]
        
        if df.empty:
            logger.info("ℹ️  Nenhum candle novo encontrado")
            return pd.DataFrame()
        
        logger.info(f"✅ {len(df):,} novos candles encontrados")
        logger.info(f"   Período: {df.index[0]} até {df.index[-1]}")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Erro ao baixar dados: {e}")
        return pd.DataFrame()


def insert_new_candles(df: pd.DataFrame, symbol: str, timeframe: str) -> int:
    """
    Insere novos candles no banco (ON CONFLICT para evitar duplicatas).
    """
    if df.empty:
        logger.info("Nada a inserir")
        return 0
    
    logger.info(f"💾 Inserindo {len(df):,} novos candles...")
    
    engine = create_engine(DB_URL, pool_pre_ping=True)
    inserted = 0
    errors = 0
    start_time = time.time()
    
    try:
        with engine.begin() as conn:
            for idx, row in df.iterrows():
                try:
                    result = conn.execute(
                        text("""
                            INSERT INTO market_data 
                            (ts, symbol, timeframe, open, high, low, close, volume, spread, bid, ask)
                            VALUES 
                            (:ts, :symbol, :timeframe, :open, :high, :low, :close, :volume, NULL, NULL, NULL)
                            ON CONFLICT (symbol, timeframe, ts) DO NOTHING
                        """),
                        {
                            "ts": idx.to_pydatetime(),
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "open": float(row['Open']),
                            "high": float(row['High']),
                            "low": float(row['Low']),
                            "close": float(row['Close']),
                            "volume": float(row['Volume'])
                        }
                    )
                    inserted += result.rowcount
                    
                except Exception as e:
                    errors += 1
                    if errors <= 3:
                        logger.error(f"Erro ao inserir candle: {e}")
            
            elapsed = time.time() - start_time
            rate = inserted / elapsed if elapsed > 0 else 0
            
            logger.info(f"✅ Inserção concluída!")
            logger.info(f"   Inseridos: {inserted:,} candles")
            logger.info(f"   Duplicatas ignoradas: {len(df) - inserted}")
            logger.info(f"   Erros: {errors}")
            logger.info(f"   Tempo: {elapsed:.1f}s")
            logger.info(f"   Taxa: {rate:.0f} candles/segundo")
            
            return inserted
            
    except Exception as e:
        logger.error(f"❌ Erro fatal na inserção: {e}")
        return 0
    finally:
        engine.dispose()


def update_statistics(symbol: str, timeframe: str):
    """Atualiza estatísticas no banco."""
    try:
        engine = create_engine(DB_URL, pool_pre_ping=True)
        
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        COUNT(*) as total,
                        MIN(ts) as first_candle,
                        MAX(ts) as last_candle,
                        COUNT(rsi) as with_indicators
                    FROM market_data 
                    WHERE symbol = :symbol AND timeframe = :timeframe
                """),
                {"symbol": symbol, "timeframe": timeframe}
            )
            row = result.fetchone()
            
            if row:
                logger.info(f"📊 Estatísticas atualizadas:")
                logger.info(f"   Total de candles: {row[0]:,}")
                logger.info(f"   Primeiro candle: {row[1]}")
                logger.info(f"   Último candle: {row[2]}")
                logger.info(f"   Com indicadores: {row[3]:,} ({row[3]/row[0]*100:.1f}%)")
                
    except Exception as e:
        logger.error(f"Erro ao atualizar estatísticas: {e}")
    finally:
        if 'engine' in locals():
            engine.dispose()


def main():
    """Função principal de atualização."""
    
    logger.info("=" * 70)
    logger.info("🔄 FOREX DATA UPDATER - ATUALIZAÇÃO AUTOMÁTICA")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Símbolo: {SYMBOL}")
    logger.info(f"Timeframe: {TIMEFRAME}")
    logger.info(f"Database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
    logger.info("")
    
    try:
        # 1. Buscar último candle
        logger.info("📊 Etapa 1/3: Verificando último candle no banco...")
        last_ts = get_last_candle_timestamp(SYMBOL, TIMEFRAME)
        logger.info("")
        
        # 2. Download novos candles
        logger.info("📊 Etapa 2/3: Baixando novos candles...")
        df = download_new_candles(SYMBOL, last_ts)
        logger.info("")
        
        if df.empty:
            logger.info("✅ Nenhuma atualização necessária. Dados já estão atualizados!")
            update_statistics(SYMBOL, TIMEFRAME)
            return
        
        # 3. Inserir no banco
        logger.info("📊 Etapa 3/3: Inserindo novos candles...")
        inserted = insert_new_candles(df, SYMBOL, TIMEFRAME)
        logger.info("")
        
        # 4. Estatísticas
        if inserted > 0:
            update_statistics(SYMBOL, TIMEFRAME)
        
        # Resumo
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info("=" * 70)
        logger.info("")
        logger.info(f"📊 Resumo:")
        logger.info(f"  • Novos candles inseridos: {inserted:,}")
        logger.info(f"  • Última timestamp: {df.index[-1] if not df.empty else 'N/A'}")
        logger.info("")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Atualização cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
