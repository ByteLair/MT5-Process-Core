# api/app/query.py
import os

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine, text

router = APIRouter(tags=["dashboard"])

DB_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader123@db:5432/mt5_trading")
engine = create_engine(DB_URL)

# somente SELECT e apenas destas tabelas/views:
WHITELIST = {
    "market_data_latest",
    "features_m1",
    "labels_m1",
    "trainset_m1",
    "market_data_raw",
}


@router.get("/query")
def query(
    table: str = Query(..., description="Nome da tabela/view (whitelist)"),
    limit: int = Query(100, ge=1, le=5000),
    order_by: str | None = Query(None, description="Ex: ts DESC"),
):
    if table not in WHITELIST:
        raise HTTPException(400, f"Tabela/View não permitida. Permitidas: {sorted(WHITELIST)}")
    if order_by and ";" in order_by:
        raise HTTPException(400, "order_by inválido.")
    q = f"SELECT * FROM public.{table}"
    if order_by:
        q += f" ORDER BY {order_by}"
    q += " LIMIT :limit"
    with engine.begin() as conn:
        df = pd.read_sql(text(q), conn, params={"limit": limit})
    return df.to_dict(orient="records")
