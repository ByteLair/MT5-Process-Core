# api/main.py
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from prometheus_client import REGISTRY, make_asgi_app
from pydantic import BaseModel

from .ingest import router as ingest_router
from .metrics import router as metrics_router
from .signals import router as signals_router

# Adicionar diretório pai ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configuração de logging estruturado
LOG_DIR = os.environ.get("LOG_DIR", "./logs/api/")
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "api.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    # =============================================================
    # Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
    # All rights reserved. | Todos os direitos reservados.
    # Private License: This code is the exclusive property of Felipe Petracco Carmo.
    # Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
    # Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
    # Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
    # =============================================================
)

app = FastAPI(title="MT5 Trade Bridge")

# Configurar tracing com Jaeger
try:
    from tracing import setup_tracing

    setup_tracing(app, service_name="mt5-trading-api", service_version="1.0.0")
except ImportError:
    print("⚠️  OpenTelemetry não instalado - tracing desabilitado")
except Exception as e:
    print(f"⚠️  Erro ao configurar tracing: {e}")

# Connection pool monitoring
try:
    from pool_monitoring import (
        collect_pgbouncer_metrics,
        setup_sqlalchemy_pool_metrics,
        update_sqlalchemy_pool_metrics,
    )

    from db import engine

    setup_sqlalchemy_pool_metrics(engine, pool_name="default")

    async def _pool_metrics_loop():
        while True:
            try:
                update_sqlalchemy_pool_metrics(engine, pool_name="default")
                # Collect PgBouncer stats using env vars
                import os

                collect_pgbouncer_metrics(
                    pgbouncer_host=os.getenv("PGBOUNCER_HOST", "pgbouncer"),
                    pgbouncer_port=int(os.getenv("PGBOUNCER_PORT", "5432")),
                    pgbouncer_user=os.getenv("POSTGRES_USER", "trader"),
                    pgbouncer_password=os.getenv("POSTGRES_PASSWORD", ""),
                )
            except Exception as e:
                print(f"⚠️  Falha ao atualizar métricas do pool: {e}")
            await asyncio.sleep(15)

    @app.on_event("startup")
    async def _start_pool_metrics_loop():
        asyncio.create_task(_pool_metrics_loop())

except Exception as e:
    print(f"⚠️  Monitoramento do pool não configurado: {e}")


class Signal(BaseModel):
    signal_id: str
    ts: str
    symbol: str
    timeframe: str
    side: str  # "buy" | "sell" | "flat"
    lots: float
    sl: float
    tp: float
    price: float | None = None
    model_version: str


class Feedback(BaseModel):
    signal_id: str
    order_id: int | None = None
    status: str  # "FILLED" | "REJECTED" | "CANCELLED"
    price: float | None = None
    slippage: float | None = None
    message: str | None = None
    ts: str


def decide(symbol: str, timeframe: str) -> Signal:
    _id = str(uuid.uuid4())
    logging.info(f"Decide chamado: symbol={symbol}, timeframe={timeframe}, id={_id}")
    return Signal(
        signal_id=_id,
        ts=datetime.now(timezone.utc).isoformat(),
        symbol=symbol,
        timeframe=timeframe,
        side="flat",
        lots=0.01,
        sl=0.0,
        tp=0.0,
        price=None,
        model_version="lgbm-0.1",
    )


@app.get("/signals/latest")
def latest(symbol: str, period: str):
    logging.info(f"/signals/latest chamado: symbol={symbol}, period={period}")
    return decide(symbol, period).model_dump()


@app.post("/orders/feedback")
def orders_feedback(body: Feedback):
    logging.info(f"/orders/feedback chamado: {body.model_dump()}")
    return {"ok": True}


@app.get("/health")
def health():
    logging.info("/health chamado")
    return {"status": "ok"}


app.include_router(signals_router)
app.include_router(ingest_router)
app.include_router(metrics_router)

# Expor /prometheus para Prometheus scrapes
metrics_app = make_asgi_app(registry=REGISTRY)
app.mount("/prometheus", metrics_app)
