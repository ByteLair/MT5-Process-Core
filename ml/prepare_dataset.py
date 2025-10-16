import os
import json
import math
import pathlib
import pandas as pd
import numpy as np
import psycopg2


# Variáveis padronizadas para conexão com o banco
DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "mt5_trading")
DB_USER = os.getenv("DB_USER", "trader")
DB_PASS = os.getenv("DB_PASS", "traderpass")

dsn = f"host={DB_HOST} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"

SYMBOL   = os.getenv("ML_SYMBOL", "EURUSD")
TIMEFRAME= os.getenv("ML_TIMEFRAME", "M1")
OUT_DIR  = pathlib.Path(__file__).resolve().parent
DATA_DIR = OUT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    roll_up = up.ewm(alpha=1/period, adjust=False).mean()
    roll_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = roll_up / (roll_down + 1e-12)
    return 100 - (100 / (1 + rs))

def fetch_market_data(limit: int = 20000) -> pd.DataFrame:
    with psycopg2.connect(dsn) as conn:
        sql = """
        SELECT ts, symbol, timeframe, open, high, low, close, volume
        FROM market_data
        WHERE symbol = %s AND timeframe = %s
        ORDER BY ts ASC
        LIMIT %s
        """
        df = pd.read_sql(sql, conn, params=(SYMBOL, TIMEFRAME, limit))
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.set_index("ts").sort_index()
    return df

def make_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # Retornos
    out["ret_1"] = out["close"].pct_change(1)
    out["ret_5"] = out["close"].pct_change(5)
    out["ret_10"] = out["close"].pct_change(10)

    # Médias móveis e desvios
    for w in (5, 10, 20, 50):
        out[f"ma_{w}"] = out["close"].rolling(w).mean()
        out[f"std_{w}"] = out["close"].rolling(w).std()

    # RSI
    out["rsi_14"] = rsi(out["close"], 14)

    # Volume transform
    out["vol_ema_20"] = out["volume"].ewm(span=20, adjust=False).mean()

    # Target: retorno futuro de 1 passo (shift -1)
    out["target_ret_1"] = out["close"].shift(-1) / out["close"] - 1.0

    # Drop linhas com NaN geradas por janelas/shift
    out = out.dropna().copy()
    return out

def main():
    print(f"[ML] Lendo dados de {SYMBOL} {TIMEFRAME}...")
    df = fetch_market_data(limit=200000)

    if df.empty:
        raise SystemExit("[ML] Sem dados no market_data para esse filtro.")

    print(f"[ML] Construindo features...")
    feat = make_features(df)

    # Seleciona colunas finais
    feature_cols = [
        "ret_1","ret_5","ret_10",
        "ma_5","ma_10","ma_20","ma_50",
        "std_5","std_10","std_20","std_50",
        "rsi_14","vol_ema_20",
        "open","high","low","close","volume",
    ]
    final = feat[feature_cols + ["target_ret_1"]].copy()
    final.reset_index(inplace=True)  # traz ts de volta como coluna

    out_csv = DATA_DIR / "training_dataset.csv"
    final.to_csv(out_csv, index=False)
    print(f"[ML] Dataset salvo em: {out_csv}")
    print(f"[ML] Linhas: {len(final)}, Colunas: {final.shape[1]}")

if __name__ == "__main__":
    main()
