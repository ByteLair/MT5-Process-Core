from fastapi import APIRouter, Query
import joblib, numpy as np, os

router = APIRouter()
MODEL_PATH = os.getenv("MODEL_PATH","/models/rf_m1.pkl")
model = joblib.load(MODEL_PATH)

@router.get("/predict")
def predict(
    mean_close: float = Query(...),
    volatility: float = Query(...),
    pct_change: float = Query(...)
):
    X = np.array([[mean_close, volatility, pct_change]])
    prob = float(model.predict_proba(X)[0,1])
    return {"label": int(prob > 0.5), "confidence": prob}
