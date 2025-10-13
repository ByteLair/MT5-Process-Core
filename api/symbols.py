# api/app/symbols.py
import os
import pandas as pd
from fastapi import APIRouter
from sqlalchemy import create_engine

router = APIRouter(tags=["dashboard"])

DB_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader123@db:5432/mt5_trading")
engine = create_engine(DB_URL)

@router.get("/symbols")
def symbols():
    q = """
      SELECT symbol, timeframe, COUNT(*) AS n
      FROM public.market_data
      GROUP BY symbol, timeframe
      ORDER BY symbol, timeframe
    """
    df = pd.read_sql(q, engine)
    sym = sorted(df["symbol"].unique().tolist()) if not df.empty else []
    tfs = sorted(df["timeframe"].unique().tolist()) if not df.empty else []
    return {"symbols": sym, "timeframes": tfs, "counts": df.to_dict(orient="records")}
