# api/app/core/config.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    # funciona com python-dotenv se estiver instalado (opcional)
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # fallback

# Carrega .env automaticamente, se existir
def _load_dotenv_if_present() -> None:
    if load_dotenv is None:
        return
    # tenta nas localizações mais comuns do seu projeto
    candidates = [
        Path(__file__).resolve().parents[3] / ".env",        # raiz do repo (../..../.env)
        Path(__file__).resolve().parents[2] / ".env",        # api/.env
        Path(__file__).resolve().parents[3] / "compose" / ".env",
        Path.cwd() / ".env",
    ]
    for p in candidates:
        if p.exists():
            load_dotenv(p)
            break

_load_dotenv_if_present()


class Settings:
    """Config central da aplicação.
    Lê primeiro do ambiente (Docker/OS) e, se existir, do .env carregado acima.
    """

    # App
    APP_NAME: str = os.getenv("APP_NAME", "MT5 API")
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    API_PREFIX: str = os.getenv("API_PREFIX", "")

    # CORS
    CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", "*")

    # DB (URL completa tem prioridade)
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # Campos para montar a URL se não for fornecida
    DB_USER: str = os.getenv("POSTGRES_USER", "postgres")
    DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    DB_HOST: str = os.getenv("POSTGRES_HOST", "mt5_db")
    DB_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME: str = os.getenv("POSTGRES_DB", "mt5")

    def get_db_url(self) -> str:
        if self.DATABASE_URL and self.DATABASE_URL.strip():
            return self.DATABASE_URL
        # monta URL padrão do Postgres
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()
