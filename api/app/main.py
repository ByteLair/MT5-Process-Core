# api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone
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

# stub de decisão: troque por seu predictor + risk
def decide(symbol: str, timeframe: str) -> Signal:
    _id = str(uuid.uuid4())
    # Exemplo: decisão “flat” por padrão
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
    sig = decide(symbol, period)
    return sig.dict()

@app.post("/orders/feedback")
def orders_feedback(body: Feedback):
    # TODO: persistir em trade_logs/fills
    return {"ok": True}

@app.get("/health")
def health():
    return {"status": "ok"}
