# api/app/metrics.py
import os, json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from sqlalchemy import create_engine, text

router = APIRouter(tags=["ml"])

DB_URL     = os.getenv("DATABASE_URL", "postgresql://trader:trader123@db:5432/mt5_trading")
MODELS_DIR = os.getenv("MODELS_DIR", "/models")
MANIFEST   = Path(MODELS_DIR) / "manifest.json"

engine = create_engine(DB_URL)

@router.get("/metrics")
def metrics():
    """
    Retorna:
      - métricas atuais (manifest.json salvo pelo treino)
      - última linha de model_metrics (se existir)
    """
    current = None
    if MANIFEST.exists():
        try:
            current = json.loads(MANIFEST.read_text())
        except Exception as e:
            raise HTTPException(500, f"Falha lendo manifest.json: {e}")
    else:
        current = {"warning": "manifest.json não encontrado — rode o treino antes."}

    # tenta buscar a última métrica gravada no banco
    last_db = None
    try:
        with engine.begin() as conn:
            row = conn.execute(text("""
                SELECT created_at, model_name, metrics
                FROM public.model_metrics
                ORDER BY id DESC
                LIMIT 1
            """)).mappings().first()
            if row:
                last_db = {
                    "created_at": row["created_at"],
                    "model_name": row["model_name"],
                    "metrics": row["metrics"],
                }
    except Exception as e:
        # não quebra a rota; só devolve aviso
        last_db = {"warning": f"Falha ao ler model_metrics: {e}"}

    return {
        "current": current,
        "last_db": last_db
    }
