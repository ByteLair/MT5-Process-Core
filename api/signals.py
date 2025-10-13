# api/app/signals.py
import os, json
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import create_engine, text

router = APIRouter(tags=["signals"])

DB_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader123@db:5432/mt5_trading")
MODELS_DIR = os.getenv("MODELS_DIR", "/models")
MANIFEST = Path(MODELS_DIR) / "manifest.json"

engine = create_engine(DB_URL)

def current_threshold(default=0.5):
    try:
        if MANIFEST.exists():
            data = json.loads(MANIFEST.read_text())
            return float(data.get("metrics", {}).get("best_threshold", default))
    except Exception:
        pass
    return default

def _predict_last_for_symbol(model, features, symbol: str, timeframe: str, n: int = 60):
    f = pd.read_sql("""
        SELECT * FROM public.features_m1
        WHERE symbol = %(s)s AND timeframe = %(tf)s
        ORDER BY ts DESC
        LIMIT %(n)s
    """, engine, params={"s": symbol, "tf": timeframe, "n": n})
    if f.empty:
        return None
    X = f[features].astype(float).fillna(0.0).values
    if hasattr(model, "predict_proba"):
        pfull = model.predict_proba(X)
        if pfull.shape[1] == 1:
            cls = int(getattr(model, "classes_", [0])[0])
            p0 = pfull[:, 0]
            proba_1 = p0 if cls == 1 else (1.0 - p0)
        else:
            proba_1 = pfull[:, 1]
    else:
        yhat = model.predict(X)
        proba_1 = yhat.astype(float)
    # registro mais recente é linha 0 (porque DESC)
    return {"ts": f.iloc[0]["ts"], "prob_up": float(proba_1[0])}

@router.get("/signals")
def signals(timeframe: str = Query("M1", description="Timeframe, ex: M1")):
    th = current_threshold()
    syms = pd.read_sql(
        "SELECT DISTINCT symbol FROM public.market_data WHERE timeframe = %(tf)s",
        engine, params={"tf": timeframe}
    )
    if syms.empty:
        raise HTTPException(404, "Sem símbolos para o timeframe informado.")

    from .predict import get_model
    model, features = get_model()

    out = []
    for sym in syms["symbol"].tolist():
        res = _predict_last_for_symbol(model, features, sym, timeframe)
        if not res:
            continue
        p0 = res["prob_up"]
        y0 = int(p0 >= th)
        out.append({"symbol": sym, "timeframe": timeframe, "ts": res["ts"], "prob_up": p0, "label": y0})
    if not out:
        raise HTTPException(404, "Sem sinais calculados.")
    out.sort(key=lambda x: x["symbol"])
    return out

@router.post("/signals/save")
def signals_save(timeframe: str = Query("M1")):
    """Calcula sinais atuais e persiste em public.model_signals (upsert)."""
    th = current_threshold()
    from .predict import get_model
    model, features = get_model()

    syms = pd.read_sql(
        "SELECT DISTINCT symbol FROM public.market_data WHERE timeframe = %(tf)s",
        engine, params={"tf": timeframe}
    )
    if syms.empty:
        raise HTTPException(404, "Sem símbolos para o timeframe informado.")

    rows = []
    for sym in syms["symbol"].tolist():
        res = _predict_last_for_symbol(model, features, sym, timeframe)
        if not res:
            continue
        ts0 = res["ts"]
        p0  = res["prob_up"]
        y0  = int(p0 >= th)
        rows.append({
            "ts": ts0, "symbol": sym, "timeframe": timeframe,
            "model_name": "rf_m1", "threshold": th,
            "prob_up": p0, "label": y0
        })
    if not rows:
        raise HTTPException(404, "Sem sinais para salvar.")

    # UPSERT
    with engine.begin() as conn:
        for r in rows:
            conn.execute(text("""
                INSERT INTO public.model_signals (ts, symbol, timeframe, model_name, threshold, prob_up, label)
                VALUES (:ts, :symbol, :tf, :model, :th, :p, :y)
                ON CONFLICT (symbol, timeframe, ts, model_name) DO UPDATE
                SET threshold = EXCLUDED.threshold,
                    prob_up   = EXCLUDED.prob_up,
                    label     = EXCLUDED.label
            """), {
                "ts": r["ts"], "symbol": r["symbol"], "tf": r["timeframe"],
                "model": r["model_name"], "th": r["threshold"],
                "p": r["prob_up"], "y": r["label"]
            })
    return {"saved": len(rows), "timeframe": timeframe}

@router.get("/signals/history")
def signals_history(
    symbol: str = Query(...),
    timeframe: str = Query("M1"),
    limit: int = Query(200, ge=1, le=5000)
):
    df = pd.read_sql("""
        SELECT ts, symbol, timeframe, model_name, threshold, prob_up, label, created_at
        FROM public.model_signals
        WHERE symbol = %(s)s AND timeframe = %(tf)s
        ORDER BY ts DESC
        LIMIT %(n)s
    """, engine, params={"s": symbol, "tf": timeframe, "n": limit})
    if df.empty:
        raise HTTPException(404, "Sem histórico para o filtro.")
    # devolver cronológico
    df = df.sort_values("ts").reset_index(drop=True)
    return df.to_dict(orient="records")

@router.get("/signals/latest")
def signals_latest(timeframe: str = Query("M1")):
    df = pd.read_sql("""
        SELECT DISTINCT ON (symbol) symbol, timeframe, ts, model_name, threshold, prob_up, label, created_at
        FROM public.model_signals
        WHERE timeframe = %(tf)s
        ORDER BY symbol, ts DESC
    """, engine, params={"tf": timeframe})
    if df.empty:
        raise HTTPException(404, "Sem sinais persistidos ainda. Use /signals/save primeiro.")
    return df.sort_values("symbol").to_dict(orient="records")
