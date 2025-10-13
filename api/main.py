# api/main.py
from __future__ import annotations

import importlib
import logging
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.logs.session import check_db_connection

log = logging.getLogger("uvicorn.error")


def _include_router_if_exists(app: FastAPI, module_path: str, *, prefix: str = "", tag: Optional[str] = None) -> None:
    """Importa um módulo que expõe `router` e inclui se existir."""
    try:
        module = importlib.import_module(module_path)
        router = getattr(module, "router", None)
        if router is None:
            log.warning("Módulo %s encontrado, mas não possui 'router'. Ignorando.", module_path)
            return
        tags = [tag] if tag else None
        app.include_router(router, prefix=prefix, tags=tags)
        log.info("Router %s montado em prefix='%s'.", module_path, prefix)
    except ModuleNotFoundError:
        # Router opcional
        pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    allow_origins = [o.strip() for o in settings.CORS_ALLOW_ORIGINS.split(",")] if settings.CORS_ALLOW_ORIGINS else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Saúde
    @app.get("/healthz", tags=["health"])
    def healthz() -> dict[str, Any]:
        return {
            "app": settings.APP_NAME,
            "env": settings.APP_ENV,
            "db_ok": check_db_connection(),
        }

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        ok = check_db_connection()
        return {"status": "ok" if ok else "degraded"}

    # Raiz
    @app.get("/", tags=["meta"])
    def root() -> dict[str, Any]:
        return {"message": f"{settings.APP_NAME} is up", "env": settings.APP_ENV}

    # Routers da aplicação (pacote `api`, arquivos no mesmo nível do main.py)
    base = "api"
    _include_router_if_exists(app, f"{base}.latest",   prefix="/latest",  tag="latest")
    _include_router_if_exists(app, f"{base}.backtest", prefix="/backtest", tag="backtest")
    _include_router_if_exists(app, f"{base}.metrics",  prefix="/metrics", tag="metrics")
    _include_router_if_exists(app, f"{base}.predict",  prefix="/predict", tag="predict")
    _include_router_if_exists(app, f"{base}.query",    prefix="/query",   tag="query")
    _include_router_if_exists(app, f"{base}.signals",  prefix="/signals", tag="signals")
    _include_router_if_exists(app, f"{base}.symbols",  prefix="/symbols", tag="symbols")

    return app


app = create_app()
