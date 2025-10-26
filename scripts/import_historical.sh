#!/usr/bin/env bash
set -euo pipefail

# Import a CSV with columns Date,Time,Open,High,Low,Close,Volume (Date like 2021.10.18)
# Usage: ./scripts/import_historical.sh <local-csv-path> <SYMBOL> <TIMEFRAME>
# Example: ./scripts/import_historical.sh dados_historicos.csv EURUSD H1

CSV_PATH="$1"
SYMBOL="$2"
TIMEFRAME="$3"

if [ ! -f "$CSV_PATH" ]; then
  echo "CSV not found: $CSV_PATH" >&2
  exit 2
fi

PREP="/tmp/$(basename "$CSV_PATH" .csv)_prepared.csv"
BASENAME_PREP=$(basename "$PREP")

echo "Preparing $CSV_PATH -> $PREP (symbol=$SYMBOL timeframe=$TIMEFRAME)"

python3 - "$CSV_PATH" "$SYMBOL" "$TIMEFRAME" "$PREP" <<'PY'
import csv,sys
infile = sys.argv[1]
symbol = sys.argv[2]
tf = sys.argv[3]
out = sys.argv[4]
with open(infile, newline='') as f, open(out, 'w', newline='') as fo:
    r = csv.reader(f)
    # try to skip header if it looks like Date
    header = next(r)
    # if header doesn't contain non-numeric, assume it's data and rewind
    if len(header) >= 2 and header[0].strip().lower().startswith('date'):
        pass
    else:
        # header was data line, process it first
        r = (row for row in ([header] + list(r)))
    writer = csv.writer(fo)
    writer.writerow(['ts','symbol','timeframe','open','high','low','close','volume'])
    for row in r:
        if len(row) < 7:
            continue
        date, time, o,h,l,c,v = row[:7]
        # normalize date 2021.10.18 -> 2021-10-18
        date = date.replace('.', '-')
        if date.strip()=='' or time.strip()=='' or c.strip()=='' :
            continue
        ts = f"{date}T{time}:00Z"
        try:
            float(o); float(h); float(l); float(c); float(v)
        except Exception:
            continue
        writer.writerow([ts,symbol,tf,o,h,l,c,v])
PY

echo "Copying prepared CSV into database container..."
docker cp "$PREP" mt5_db:/tmp/ || { echo "docker cp failed"; exit 3; }

echo "Creating staging table and importing into DB..."
docker exec -i mt5_db psql -U trader -d mt5_trading -v ON_ERROR_STOP=1 <<SQL
CREATE TABLE IF NOT EXISTS public.staging_market_data (
  ts timestamptz,
  symbol text,
  timeframe text,
  open double precision,
  high double precision,
  low double precision,
  close double precision,
  volume double precision
);
\copy public.staging_market_data (ts,symbol,timeframe,open,high,low,close,volume) FROM '/tmp/${BASENAME_PREP}' WITH (FORMAT csv, HEADER true);
-- upsert into hypertable
INSERT INTO public.market_data (ts,symbol,timeframe,open,high,low,close,volume)
SELECT ts,symbol,timeframe,open,high,low,close,volume FROM public.staging_market_data
ON CONFLICT (symbol,timeframe,ts) DO NOTHING;
-- cleanup staging if desired (comment out to keep for auditing)
DELETE FROM public.staging_market_data WHERE TRUE;
SQL

echo "Import complete. Run queries to verify counts and last timestamps."
