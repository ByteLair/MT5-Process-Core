# api/app/latest.py
import os
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine

router = APIRouter(tags=["dashboard"])

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://trader:trader123@db:5432/mt5_trading")
engine = create_engine(DB_URL)

@router.get("/latest")
def latest(
    symbol: str | None = Query(None, description="Filtra por símbolo, ex: EURUSD"),
    timeframe: str | None = Query(None, description="Filtra por timeframe, ex: M1")
):
    base = "SELECT symbol, timeframe, ts, open, high, low, close, volume, spread, bid, ask FROM public.market_data_latest"
    where = []
    params = {}
    if symbol:
        where.append("symbol = %(symbol)s")
        params["symbol"] = symbol
    if timeframe:
        where.append("timeframe = %(tf)s")
        params["tf"] = timeframe

    q = base + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY symbol, timeframe"
    df = pd.read_sql(q, engine, params=params)
    if df.empty:
        raise HTTPException(404, "Sem dados para os filtros informados.")
    return df.to_dict(orient="records")
