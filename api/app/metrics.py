import os
import sys

from fastapi import APIRouter
from sqlalchemy import text

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Robust import of the shared SQLAlchemy engine
try:
    from db import engine  # type: ignore
except Exception:  # pragma: no cover - fallback for different loaders
    try:
        from api.db import engine  # type: ignore
    except Exception:
        from ..db import engine  # type: ignore

router = APIRouter()


@router.get("/metrics")
def metrics():
    """Health-ish metrics endpoint used by tests.
    Returns keys 'current' and 'last_db' regardless of DB availability.
    """
    current = {"status": "ok"}
    last_db = None

    # Try to query basic DB timestamp; tolerate failures in test envs without DB
    try:
        with engine.connect() as c:
            row = c.execute(text("SELECT now()::timestamptz AS ts")).mappings().first()
            if row and row.get("ts") is not None:
                ts = row["ts"]
                last_db = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
    except Exception:
        last_db = None

    return {"current": current, "last_db": last_db}
