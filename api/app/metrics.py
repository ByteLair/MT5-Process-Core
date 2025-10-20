import os
import sys

from fastapi import APIRouter
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import engine

router = APIRouter()


@router.get("/metrics")
def metrics():
    sql = text(
        """
	SELECT symbol, timeframe,
	max(ts) AS last_ts,
	count(*) FILTER (WHERE ts >= now() - interval '10 minutes') AS rows_10m
	FROM public.market_data
	GROUP BY symbol, timeframe
	ORDER BY symbol, timeframe
	"""
    )
    with engine.connect() as c:
        rows = [dict(r._mapping) for r in c.execute(sql)]
    return {"ok": True, "data": rows}
