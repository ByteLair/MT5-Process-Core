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
# Expect columns: ts,open,high,low,close,volume,spread (ts ISO8601)
required = {"ts","open","high","low","close","volume"}
missing = required - set(c.lower() for c in df.columns)
if missing:
    raise SystemExit(f"missing columns: {missing}")

# Normalize columns
df.columns = [c.lower() for c in df.columns]
df["symbol"] = symbol
df["timeframe"] = timeframe
if "spread" not in df.columns: df["spread"] = 0.0

# Batch insert
chunksize = 5000
with engine.begin() as conn:
    for i in range(0, len(df), chunksize):
        chunk = df.iloc[i:i+chunksize].copy()
        chunk.to_sql("market_data", conn, schema="public", index=False, if_exists="append", method="multi")
print(f"imported rows: {len(df)}")
