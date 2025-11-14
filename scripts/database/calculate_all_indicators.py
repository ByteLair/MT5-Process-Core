#!/usr/bin/env python3
"""
Script para calcular indicadores técnicos em TODOS os dados históricos.
Processa os 24,882 candles EURUSD H1 importados.

Indicadores calculados:
- RSI (14 períodos)
- MACD (12, 26, 9)
- ATR (14 períodos)
- Bollinger Bands (20 períodos, 2 desvios)
"""

import logging
import sys
import time
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calcula RSI (Relative Strength Index)"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_macd(series: pd.Series, fast=12, slow=26, signal=9):
    """Calcula MACD (Moving Average Convergence Divergence)"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calcula ATR (Average True Range)"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return atr


def compute_bollinger(series: pd.Series, period: int = 20, num_std: float = 2.0):
    """Calcula Bollinger Bands"""
    sma = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower


def calculate_indicators_batch(engine, symbol: str, timeframe: str, batch_size: int = 5000):
    """
    Calcula indicadores para um símbolo/timeframe específico em lotes.
    
    Args:
        engine: SQLAlchemy engine
        symbol: Símbolo (ex: EURUSD)
        timeframe: Timeframe (ex: H1)
        batch_size: Tamanho do lote para atualização
    
    Returns:
        Número total de registros atualizados
    """
    logger.info(f"📊 Iniciando cálculo de indicadores para {symbol} {timeframe}...")
    
    start_time = time.time()
    
    with engine.begin() as conn:
        # Buscar TODOS os candles (sem limite de tempo)
        logger.info(f"📥 Carregando dados do banco...")
        df = pd.read_sql(
            text("""
                SELECT ts, symbol, timeframe, open, high, low, close, volume
                FROM market_data
                WHERE symbol = :sym
                  AND timeframe = :tf
                ORDER BY ts ASC
            """),
            conn,
            params={"sym": symbol, "tf": timeframe},
        )
        
        total_records = len(df)
        logger.info(f"✅ Carregados {total_records:,} registros")
        
        if df.empty:
            logger.warning("⚠️  Nenhum dado encontrado!")
            return 0
        
        if total_records < 30:
            logger.warning(f"⚠️  Apenas {total_records} registros - insuficiente para indicadores (mínimo 30)")
            return 0
        
        # Calcular todos os indicadores
        logger.info(f"🔢 Calculando indicadores...")
        
        # RSI
        logger.info("  • RSI (14 períodos)...")
        df["rsi"] = compute_rsi(df["close"], period=14)
        
        # MACD
        logger.info("  • MACD (12, 26, 9)...")
        macd, macd_sig, macd_h = compute_macd(df["close"])
        df["macd"] = macd
        df["macd_signal"] = macd_sig
        df["macd_hist"] = macd_h
        
        # ATR
        logger.info("  • ATR (14 períodos)...")
        df["atr"] = compute_atr(df["high"], df["low"], df["close"], period=14)
        
        # Bollinger Bands
        logger.info("  • Bollinger Bands (20, 2σ)...")
        bb_upper, bb_middle, bb_lower = compute_bollinger(df["close"], period=20)
        df["bb_upper"] = bb_upper
        df["bb_middle"] = bb_middle
        df["bb_lower"] = bb_lower
        
        # Remover linhas com NaN (primeiras linhas onde indicadores não podem ser calculados)
        df_valid = df.dropna(subset=["rsi", "macd", "atr", "bb_upper"])
        valid_records = len(df_valid)
        nan_records = total_records - valid_records
        
        logger.info(f"✅ Indicadores calculados: {valid_records:,} registros válidos ({nan_records} NaN descartados)")
        
        # Atualizar em lotes para melhor performance
        logger.info(f"💾 Atualizando banco de dados em lotes de {batch_size:,}...")
        
        updated = 0
        total_batches = (valid_records + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, valid_records)
            batch_df = df_valid.iloc[start_idx:end_idx]
            
            # Atualizar lote
            for _, row in batch_df.iterrows():
                result = conn.execute(
                    text("""
                        UPDATE market_data
                        SET rsi = :rsi,
                            macd = :macd,
                            macd_signal = :macd_signal,
                            macd_hist = :macd_hist,
                            atr = :atr,
                            bb_upper = :bb_upper,
                            bb_middle = :bb_middle,
                            bb_lower = :bb_lower
                        WHERE symbol = :symbol
                          AND timeframe = :timeframe
                          AND ts = :ts
                    """),
                    {
                        "symbol": row["symbol"],
                        "timeframe": row["timeframe"],
                        "ts": row["ts"],
                        "rsi": float(row["rsi"]),
                        "macd": float(row["macd"]),
                        "macd_signal": float(row["macd_signal"]),
                        "macd_hist": float(row["macd_hist"]),
                        "atr": float(row["atr"]),
                        "bb_upper": float(row["bb_upper"]),
                        "bb_middle": float(row["bb_middle"]),
                        "bb_lower": float(row["bb_lower"]),
                    },
                )
                updated += result.rowcount
            
            # Progress
            progress = (batch_num + 1) / total_batches * 100
            logger.info(f"  Progresso: {progress:.1f}% ({updated:,}/{valid_records:,} atualizados)")
        
        elapsed = time.time() - start_time
        records_per_sec = updated / elapsed if elapsed > 0 else 0
        
        logger.info(f"")
        logger.info(f"✅ Concluído!")
        logger.info(f"  • Total atualizado: {updated:,} registros")
        logger.info(f"  • Tempo decorrido: {elapsed:.2f}s")
        logger.info(f"  • Performance: {records_per_sec:.0f} registros/segundo")
        
        return updated


def verify_indicators(engine, symbol: str, timeframe: str):
    """Verifica se os indicadores foram calculados corretamente."""
    logger.info(f"")
    logger.info(f"🔍 Verificando indicadores calculados...")
    
    with engine.begin() as conn:
        # Contar registros com indicadores
        result = conn.execute(
            text("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(rsi) as with_rsi,
                    COUNT(macd) as with_macd,
                    COUNT(atr) as with_atr,
                    COUNT(bb_upper) as with_bb,
                    MIN(ts) as first_ts,
                    MAX(ts) as last_ts
                FROM market_data
                WHERE symbol = :sym
                  AND timeframe = :tf
            """),
            {"sym": symbol, "tf": timeframe}
        ).fetchone()
        
        logger.info(f"")
        logger.info(f"📊 Estatísticas:")
        logger.info(f"  • Total de registros: {result[0]:,}")
        logger.info(f"  • Com RSI: {result[1]:,} ({result[1]/result[0]*100:.1f}%)")
        logger.info(f"  • Com MACD: {result[2]:,} ({result[2]/result[0]*100:.1f}%)")
        logger.info(f"  • Com ATR: {result[3]:,} ({result[3]/result[0]*100:.1f}%)")
        logger.info(f"  • Com Bollinger: {result[4]:,} ({result[4]/result[0]*100:.1f}%)")
        logger.info(f"  • Período: {result[5]} até {result[6]}")
        
        # Mostrar amostra dos últimos 5 registros
        logger.info(f"")
        logger.info(f"📋 Amostra dos últimos 5 registros:")
        
        sample = pd.read_sql(
            text("""
                SELECT 
                    ts,
                    close,
                    ROUND(rsi::numeric, 2) as rsi,
                    ROUND(macd::numeric, 5) as macd,
                    ROUND(atr::numeric, 5) as atr,
                    ROUND(bb_upper::numeric, 5) as bb_upper,
                    ROUND(bb_lower::numeric, 5) as bb_lower
                FROM market_data
                WHERE symbol = :sym
                  AND timeframe = :tf
                  AND rsi IS NOT NULL
                ORDER BY ts DESC
                LIMIT 5
            """),
            conn,
            params={"sym": symbol, "tf": timeframe}
        )
        
        if not sample.empty:
            print(sample.to_string(index=False))


def main():
    """Função principal."""
    logger.info("=" * 70)
    logger.info("🚀 CÁLCULO DE INDICADORES TÉCNICOS - DADOS HISTÓRICOS")
    logger.info("=" * 70)
    logger.info(f"")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info(f"")
    
    # Conectar ao banco
    # Usar 'db' como hostname dentro do Docker, ou localhost se rodando no host
    import os
    db_host = os.getenv("DB_HOST", "db")
    DATABASE_URL = f"postgresql+psycopg://trader:trader123@{db_host}:5432/mt5_trading"
    logger.info(f"🔗 Conectando ao banco de dados...")
    logger.info(f"   URL: postgresql://trader:***@{db_host}:5432/mt5_trading")
    
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
        
        # Testar conexão
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"✅ Conectado com sucesso!")
        logger.info(f"")
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar: {e}")
        sys.exit(1)
    
    # Calcular indicadores - configurável via argumentos
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "EURUSD"
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "H1"
    
    try:
        # Calcular
        updated = calculate_indicators_batch(
            engine=engine,
            symbol=symbol,
            timeframe=timeframe,
            batch_size=1000
        )
        
        if updated > 0:
            # Verificar
            verify_indicators(engine, symbol, timeframe)
            
            logger.info(f"")
            logger.info(f"=" * 70)
            logger.info(f"✅ PROCESSO CONCLUÍDO COM SUCESSO!")
            logger.info(f"=" * 70)
            logger.info(f"")
            logger.info(f"📊 Resumo:")
            logger.info(f"  • Símbolo: {symbol}")
            logger.info(f"  • Timeframe: {timeframe}")
            logger.info(f"  • Registros atualizados: {updated:,}")
            logger.info(f"  • Indicadores: RSI, MACD, ATR, Bollinger Bands")
            logger.info(f"")
            logger.info(f"🎯 Próximos passos:")
            logger.info(f"  1. Executar testes com dados reais")
            logger.info(f"  2. Validar performance das queries")
            logger.info(f"  3. Otimizar índices do banco")
            logger.info(f"")
        else:
            logger.warning(f"⚠️  Nenhum registro foi atualizado!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Erro durante o processo: {e}", exc_info=True)
        sys.exit(1)
    
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
