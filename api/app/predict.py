import os
import sys
import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine, text
from .features_sql import LATEST_WINDOW_SQL

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import engine

router = APIRouter()

DB_URL = os.environ.get("DATABASE_URL")
MODEL_PATH = os.environ.get("MODEL_PATH", "/models/rf_m1.pkl")


_model_cache = None


def load_model():
	global _model_cache
	if _model_cache is None:
		_model_cache = joblib.load(MODEL_PATH)
	return _model_cache


@router.get("/predict")
def predict(symbol: str = Query(..., min_length=3, max_length=10), lookback: int = 120):
	mdl = load_model()
	features = mdl["features"]

	with engine.connect() as conn:
		df = pd.read_sql(text(LATEST_WINDOW_SQL), conn, params={"symbol": symbol, "lookback": lookback})

	if df.empty:
		raise HTTPException(status_code=404, detail="no data for symbol")

	X = df[[
		"close","volume","spread","rsi",
		"macd","macd_signal","macd_hist","atr",
		"ma60","ret_1"
	]].fillna(0)

	# garante ordem das colunas conforme treino
	X = X[features]

	proba = mdl["model"].predict_proba(X.iloc[[-1]])[0,1]
	label = int(proba >= float(os.environ.get("THRESHOLD", 0.55)))

	return {
		"symbol": symbol,
		"ts": df["ts"].iloc[-1].isoformat(),
		"proba_up": round(float(proba), 4),
		"label": label,
		"features_tail": X.iloc[-1].to_dict()
	}


# Endpoint adicional: aceita um JSON com features e retorna predição usando um modelo 'raw'
@router.post("/predict")
def predict_raw(data: dict):
	"""Recebe um JSON com as features, carrega o modelo em /models/latest_model.pkl e retorna a predição.

	Exemplo de corpo esperado: {"feature1": 1.2, "feature2": 0.3, ...}
	"""
	# carrega modelo local (não altera o loader existente)
	try:
		model = joblib.load("/models/latest_model.pkl")
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"failed to load model: {e}")

	try:
		X = pd.DataFrame([data])
	except Exception as e:
		raise HTTPException(status_code=400, detail=f"invalid input data: {e}")

	try:
		y_pred = model.predict(X)[0]
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"model predict error: {e}")

	return {"prediction": float(y_pred)}