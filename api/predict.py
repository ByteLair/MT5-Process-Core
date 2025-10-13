import os, json
from pathlib import Path
import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine

router = APIRouter(tags=["ml"])

DB_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader123@db:5432/mt5_trading")
MODELS_DIR = os.getenv("MODELS_DIR", "/models")
MODEL_PATH = os.path.join(MODELS_DIR, "rf_m1.pkl")
MANIFEST = Path(MODELS_DIR) / "manifest.json"

engine = create_engine(DB_URL)

_model_bundle = None
_best_threshold = 0.5  # fallback

def _load_manifest_threshold():
    global _best_threshold
    try:
        if MANIFEST.exists():
            data = json.loads(MANIFEST.read_text())
            t = data.get("metrics", {}).get("best_threshold", 0.5)
            _best_threshold = float(t)
    except Exception:
        _best_threshold = 0.5

def get_model():
    global _model_bundle
    if _model_bundle is None:
        try:
            _model_bundle = joblib.load(MODEL_PATH)
        except FileNotFoundError:
            raise HTTPException(500, detail="Modelo não encontrado. Treine primeiro.")
        except Exception as e:
            raise HTTPException(500, detail=f"Falha ao carregar modelo: {e}")
        _load_manifest_threshold()
    return _model_bundle["model"], _model_bundle["features"]

@router.get("/predict")
def predict(
    symbol: str = Query(..., description="Símbolo, ex: EURUSD"),
    n: int = Query(30, ge=1, le=500, description="Qtde de linhas recentes"),
    threshold: float | None = Query(None, ge=0.0, le=1.0, description="Opcional: sobrescreve o threshold")
):
    model, features = get_model()

    q = """
        SELECT * FROM public.features_m1
        WHERE symbol = %(symbol)s AND timeframe='M1'
        ORDER BY ts DESC
        LIMIT %(n)s
    """
    df = pd.read_sql(q, engine, params={"symbol": symbol, "n": n})
    if df.empty:
        raise HTTPException(404, f"Sem features para {symbol}")

    X = df[features].astype(float).fillna(0.0).values

    # prob de classe 1, compatível com RF e Dummy
    if hasattr(model, "predict_proba"):
        pf = model.predict_proba(X)
        if pf.shape[1] == 1:
            cls = int(getattr(model, "classes_", [0])[0])
            p0 = pf[:, 0]
            proba_1 = p0 if cls == 1 else (1.0 - p0)
        else:
            proba_1 = pf[:, 1]
    else:
        yhat = model.predict(X)
        proba_1 = yhat.astype(float)

    th = _best_threshold if threshold is None else float(threshold)
    label = (proba_1 >= th).astype(int)

    out = [{"ts": ts, "prob_up": float(p), "label": int(y)}
           for ts, p, y in zip(df["ts"].tolist(), proba_1.tolist(), label.tolist())]
    out.reverse()  # cronológico crescente
    return out
