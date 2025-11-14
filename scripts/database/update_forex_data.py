#!/usr/bin/env python3
"""
Atualização Automática de Dados Forex - Yahoo Finance
======================================================

Detecta automaticamente dados faltantes e baixa via Yahoo Finance.
Limitado aos últimos 7 dias para M1 (restrição da API).

Para histórico completo (5+ anos), use MetaTrader 5.

Uso:
    python scripts/database/update_forex_data.py
    
Cron (atualização diária às 00:05):
    5 0 * * * /usr/bin/docker exec mt5_api python /app/scripts/database/update_forex_data.py
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configurações
DB_URL = "postgresql://trader:trader123@db:5432/mt5_trading"
SYMBOL = "EURUSD"
TIMEFRAME = "M1"


def get_last_timestamp(symbol: str, timeframe: str) -> datetime:
    """
    Retorna a última timestamp disponível no banco.
    
    Returns:
        datetime: Última data com dados, ou datetime(2020,1,1) se vazio
    """
    engine = create_engine(DB_URL, pool_pre_ping=True)
    
    try:
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
                logger.info(f"📅 Última data no banco: {row[0]}")
                return row[0]
            else:
                logger.warning("⚠️  Nenhum dado encontrado no banco")
                return datetime(2020, 1, 1)
                
    except Exception as e:
        logger.error(f"❌ Erro ao consultar banco: {e}")
        raise
    finally:
        engine.dispose()


def download_recent_data(symbol: str, last_ts: datetime, max_days: int = 7) -> pd.DataFrame:
    """
    Download dados recentes via Yahoo Finance.
    
    Args:
        symbol: Par forex (ex: EURUSD)
        last_ts: Última timestamp no banco
        max_days: Máximo de dias para baixar (Yahoo Finance limita M1 a 7 dias)
    
    Returns:
        DataFrame com dados novos (apenas após last_ts)
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("❌ yfinance não instalado!")
        logger.info("💡 Instale com: pip install yfinance")
        sys.exit(1)
    
    # Calcular dias faltando
    now = datetime.now()
    days_missing = (now - last_ts).days
    
    logger.info(f"⏱️  Dias desde última atualização: {days_missing}")
    
    if days_missing == 0:
        logger.info("✅ Dados já estão atualizados!")
        return pd.DataFrame()
    
    # Yahoo Finance: limite de 7 dias para M1
    if days_missing > max_days:
        logger.warning(f"⚠️  {days_missing} dias faltando, mas Yahoo Finance limita M1 a {max_days} dias")
        logger.info(f"💡 Baixando apenas últimos {max_days} dias")
        logger.info("💡 Para histórico completo, use MetaTrader 5")
        days_missing = max_days
    
    # Download
    logger.info(f"📥 Baixando dados via Yahoo Finance...")
    logger.info(f"   Símbolo: {symbol}=X")
    logger.info(f"   Período: últimos {days_missing} dias")
    
    try:
        yahoo_symbol = f"{symbol}=X"
        ticker = yf.Ticker(yahoo_symbol)
        
        # Download com período específico
        df = ticker.history(period=f"{days_missing}d", interval="1m", auto_adjust=False)
        
        if df.empty:
            logger.warning("⚠️  Yahoo Finance não retornou dados")
            return pd.DataFrame()
        
        # Filtrar apenas dados APÓS última timestamp no banco
        df = df[df.index > last_ts]
        
        if df.empty:
            logger.info("ℹ️  Nenhum dado novo encontrado")
            return pd.DataFrame()
        
        logger.info(f"✅ {len(df):,} novos candles encontrados")
        logger.info(f"   Período: {df.index[0]} até {df.index[-1]}")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Erro ao baixar dados: {e}")
        return pd.DataFrame()


def insert_new_data(df: pd.DataFrame, symbol: str, timeframe: str) -> int:
    """
    Insere novos dados no banco (evita duplicatas com ON CONFLICT).
    
    Returns:
        int: Número de registros inseridos
    """
    if df.empty:
        logger.info("Nada a inserir")
        return 0
    
    logger.info(f"💾 Inserindo {len(df):,} novos registros...")
    
    engine = create_engine(DB_URL, pool_pre_ping=True)
    inserted = 0
    errors = 0
    
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
                    if errors <= 3:  # Mostrar apenas primeiros 3 erros
                        logger.error(f"Erro ao inserir: {e}")
            
            logger.info(f"✅ {inserted:,} registros inseridos com sucesso")
            if errors > 0:
                logger.warning(f"⚠️  {errors} erros durante inserção")
            
            return inserted
            
    except Exception as e:
        logger.error(f"❌ Erro fatal na inserção: {e}")
        return 0
    finally:
        engine.dispose()


def calculate_indicators_for_new_data(symbol: str, timeframe: str, since: datetime):
    """
    Calcula indicadores apenas para dados novos (otimizado).
    
    TODO: Implementar cálculo incremental de indicadores
    """
    logger.info("🔢 Cálculo de indicadores...")
    logger.info("⏳ (Implementar cálculo incremental no futuro)")
    
    # Por enquanto, sugerir cálculo manual completo
    logger.info("💡 Execute manualmente:")
    logger.info(f"   docker exec mt5_api python /tmp/calculate_all_indicators.py {symbol} {timeframe}")


def main():
    """Função principal de atualização."""
    
    logger.info("=" * 70)
    logger.info("🔄 ATUALIZAÇÃO AUTOMÁTICA DE DADOS FOREX")
    logger.info("=" * 70)
    logger.info("")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Símbolo: {SYMBOL}")
    logger.info(f"Timeframe: {TIMEFRAME}")
    logger.info("")
    
    try:
        # 1. Verificar última data no banco
        logger.info("📊 Etapa 1/3: Verificando dados existentes...")
        last_ts = get_last_timestamp(SYMBOL, TIMEFRAME)
        
        days_missing = (datetime.now() - last_ts).days
        logger.info(f"⏱️  Dias faltando: {days_missing}")
        logger.info("")
        
        if days_missing == 0:
            logger.info("✅ Dados já estão atualizados!")
            return
        
        # 2. Download dados novos
        logger.info("📊 Etapa 2/3: Download de dados novos...")
        df = download_recent_data(SYMBOL, last_ts)
        logger.info("")
        
        if df.empty:
            logger.info("ℹ️  Nenhum dado novo disponível")
            return
        
        # 3. Inserir no banco
        logger.info("📊 Etapa 3/3: Inserindo no banco de dados...")
        inserted = insert_new_data(df, SYMBOL, TIMEFRAME)
        logger.info("")
        
        # 4. Indicadores (opcional)
        if inserted > 0:
            calculate_indicators_for_new_data(SYMBOL, TIMEFRAME, last_ts)
        
        # Resumo
        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info("=" * 70)
        logger.info("")
        logger.info(f"📊 Resumo:")
        logger.info(f"  • Novos candles: {inserted:,}")
        logger.info(f"  • Última data: {df.index[-1] if not df.empty else 'N/A'}")
        logger.info("")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Atualização cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
