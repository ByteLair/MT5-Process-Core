"""
Worker para cálculo de indicadores técnicos server-side.
Garante consistência entre treino e produção, evitando discrepâncias
quando EA e pipeline de ML calculam indicadores de formas diferentes.
"""

import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # =============================================================
    # Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
    # All rights reserved. | Todos os direitos reservados.
    # Private License: This code is the exclusive property of Felipe Petracco Carmo.
    # Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
    # Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
    # Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
    # =============================================================
)
logger = logging.getLogger(__name__)

# Robust import of the shared SQLAlchemy engine
try:
    from ..db import engine as ENGINE  # type: ignore
except Exception:
    try:
        from db import engine as ENGINE  # type: ignore
    except Exception:
        # Last resort: build engine from env
        from sqlalchemy import create_engine

        DATABASE_URL = os.getenv(
            "DATABASE_URL", "postgresql+psycopg://trader:trader123@db:5432/mt5_trading"
        )
        ENGINE = create_engine(DATABASE_URL, pool_pre_ping=True)
        logger.info(f"Created ENGINE from DATABASE_URL: {DATABASE_URL}")


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:  # type: ignore
    """RSI (Relative Strength Index)"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)  # type: ignore
    loss = -delta.where(delta < 0, 0.0)  # type: ignore
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_macd(series: pd.Series, fast=12, slow=26, signal=9):
    """MACD (Moving Average Convergence Divergence)"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """ATR (Average True Range)"""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    return atr


def compute_bollinger(series: pd.Series, period: int = 20, num_std: float = 2.0):
    """Bollinger Bands"""
    sma = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std()
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    return upper, sma, lower


def calculate_indicators(symbol: str, lookback_minutes: int = 200) -> int:
    """
    Calcula indicadores para um símbolo específico.
    Retorna número de linhas atualizadas.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)

    with ENGINE.begin() as conn:
        # Buscar candles M1 recentes sem indicadores ou desatualizados
        df = pd.read_sql(
            text(
                """
                SELECT ts, symbol, open, high, low, close, volume
                FROM public.market_data
                WHERE symbol = :sym
                  AND timeframe = 'M1'
                  AND ts >= :cutoff
                ORDER BY ts ASC
            """
            ),
            conn,
            params={"sym": symbol, "cutoff": cutoff},
        )

        if df.empty or len(df) < 30:  # Mínimo para indicadores
            return 0

        # Calcular indicadores
        df["rsi"] = compute_rsi(df["close"], period=14)
        macd, macd_sig, macd_h = compute_macd(df["close"])
        df["macd"] = macd
        df["macd_signal"] = macd_sig
        df["macd_hist"] = macd_h
        df["atr"] = compute_atr(df["high"], df["low"], df["close"], period=14)
        bb_upper, bb_middle, bb_lower = compute_bollinger(df["close"], period=20)
        df["bb_upper"] = bb_upper
        df["bb_middle"] = bb_middle
        df["bb_lower"] = bb_lower

        # Atualizar apenas linhas com indicadores calculados (não-NaN)
        df_valid = df.dropna(subset=["rsi", "macd", "atr", "bb_upper"])

        updated = 0
        for _, row in df_valid.iterrows():
            result = conn.execute(
                text(
                    """
                    UPDATE public.market_data
                    SET rsi = :rsi,
                        macd = :macd,
                        macd_signal = :macd_signal,
                        macd_hist = :macd_hist,
                        atr = :atr,
                        bb_upper = :bb_upper,
                        bb_middle = :bb_middle,
                        bb_lower = :bb_lower
                    WHERE symbol = :symbol
                      AND timeframe = 'M1'
                      AND ts = :ts
                """
                ),
                {
                    "symbol": row["symbol"],
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

        return updated


_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    _shutdown_requested = True


def run_loop(interval_sec: int = 60, symbols: list[str] | None = None):
    """Loop principal do worker de indicadores."""
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    if symbols is None:
        symbols_str = os.getenv("SYMBOLS", "EURUSD,GBPUSD,USDJPY")
        symbols = [s.strip() for s in symbols_str.split(",")]

    logger.info(f"Indicators Worker started for symbols: {symbols}, interval={interval_sec}s")

    while not _shutdown_requested:
        try:
            for symbol in symbols:
                if _shutdown_requested:
                    break
                updated = calculate_indicators(symbol, lookback_minutes=200)
                if updated > 0:
                    logger.info(f"{symbol}: updated {updated} rows with indicators")
                else:
                    logger.debug(f"{symbol}: no rows updated")
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}", exc_info=True)

        # Sleep in smaller increments to respond faster to shutdown
        for _ in range(interval_sec):
            if _shutdown_requested:
                break
            time.sleep(1)

    logger.info("Indicators Worker stopped gracefully")
    sys.exit(0)


if __name__ == "__main__":
    interval = int(os.getenv("INDICATORS_INTERVAL", "60"))
    run_loop(interval_sec=interval)
