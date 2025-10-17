# api/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timezone
from .signals import router as signals_router
from .ingest import router as ingest_router
from .metrics import router as metrics_router
from prometheus_client import make_asgi_app, REGISTRY
import uuid

app = FastAPI(title="MT5 Trade Bridge")

class Signal(BaseModel):
    signal_id: str
    ts: str
    symbol: str
    timeframe: str
    side: str            # "buy" | "sell" | "flat"
    lots: float
    sl: float
    tp: float
    price: float | None = None
    model_version: str

class Feedback(BaseModel):
    signal_id: str
    order_id: int | None = None
    status: str          # "FILLED" | "REJECTED" | "CANCELLED"
    price: float | None = None
    slippage: float | None = None
    message: str | None = None
    ts: str

def decide(symbol: str, timeframe: str) -> Signal:
    _id = str(uuid.uuid4())
    return Signal(
        signal_id=_id,
        ts=datetime.now(timezone.utc).isoformat(),
        symbol=symbol,
        timeframe=timeframe,
        side="flat",
        lots=0.01,
        sl=0.0, tp=0.0, price=None,
        model_version="lgbm-0.1"
    )

@app.get("/signals/latest")
def latest(symbol: str, period: str):
    return decide(symbol, period).model_dump()

@app.post("/orders/feedback")
def orders_feedback(body: Feedback):
    return {"ok": True}

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(signals_router)
app.include_router(ingest_router)
app.include_router(metrics_router)

# Expor /prometheus para Prometheus scrapes
metrics_app = make_asgi_app(registry=REGISTRY)
app.mount("/prometheus", metrics_app)
