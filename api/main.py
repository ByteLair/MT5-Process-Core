from fastapi import FastAPI
from sqlalchemy import create_engine, text
from api.config import get_db_url

app = FastAPI(title="MT5 Trading API", version="1.0.0")
engine = create_engine(get_db_url(), pool_pre_ping=True, future=True)

@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}

try:
    from api.predict import router as predict_router
    app.include_router(predict_router)
except Exception:
    pass
