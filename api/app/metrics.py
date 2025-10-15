from fastapi import APIRouter
from sqlalchemy import create_engine, text
import os

router = APIRouter()
engine = create_engine(os.environ.get("DATABASE_URL"), pool_pre_ping=True, future=True)

@router.get("/metrics")
def metrics():
	sql = text("""
	SELECT symbol, timeframe,
	max(ts) AS last_ts,
	count(*) FILTER (WHERE ts >= now() - interval '10 minutes') AS rows_10m
	FROM public.market_data
	GROUP BY symbol, timeframe
	ORDER BY symbol, timeframe
	""")
	with engine.connect() as c:
		rows = [dict(r) for r in c.execute(sql)]
	return {"ok": True, "data": rows}