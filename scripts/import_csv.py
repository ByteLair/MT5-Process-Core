#!/usr/bin/env python3
import os, sys, pandas as pd
from sqlalchemy import create_engine

if len(sys.argv) < 2:
    print("usage: import_csv.py <csv_file> [symbol=EURUSD] [timeframe=M1]")
    sys.exit(1)

csv_path = sys.argv[1]
symbol = sys.argv[2] if len(sys.argv) > 2 else os.getenv("SYMBOL","EURUSD")
timeframe = sys.argv[3] if len(sys.argv) > 3 else os.getenv("TIMEFRAME","M1")

db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://trader:trader123@localhost:5432/mt5_trading")
engine = create_engine(db_url, future=True)

df = pd.read_csv(csv_path)
# Normalize columns
df.columns = [c.lower() for c in df.columns]
# If ts is missing, create from date+time
if "ts" not in df.columns and "date" in df.columns and "time" in df.columns:
    df["ts"] = pd.to_datetime(df["date"] + " " + df["time"], format="%Y.%m.%d %H:%M", utc=True)
# Garantir que ts é datetime
if not pd.api.types.is_datetime64_any_dtype(df["ts"]):
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
required = {"ts","open","high","low","close","volume"}
missing = required - set(df.columns)
if missing:
    raise SystemExit(f"missing columns: {missing}")
df["symbol"] = symbol
df["timeframe"] = timeframe

if "spread" not in df.columns: df["spread"] = 0.0
# Remover colunas extras que não existem na tabela
for col in ["date", "time"]:
    if col in df.columns:
        df.drop(columns=[col], inplace=True)

# Batch insert (reduzido para evitar erro de parâmetros)
chunksize = 500
cols = ["ts", "open", "high", "low", "close", "volume", "spread", "symbol", "timeframe"]
with engine.begin() as conn:
    for i in range(0, len(df), chunksize):
        chunk = df.iloc[i:i+chunksize].copy()
        chunk = chunk[cols]
        chunk.to_sql("market_data", conn, schema="public", index=False, if_exists="append")
print(f"imported rows: {len(df)}")
