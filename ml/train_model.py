import json
import pathlib

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

BASE = pathlib.Path(__file__).resolve().parent
DATA = BASE / "data" / "training_dataset.csv"
MODELS_DIR = BASE / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FEATURES_JSON = MODELS_DIR / "feature_list.json"
MODEL_PKL = MODELS_DIR / "random_forest.pkl"
REPORT_JSON = MODELS_DIR / "last_train_report.json"


def main() -> None:
    # Tune environment for CPU utilization
    try:
        from ml.utils.perf import fast_read_csv, sklearn_thread_limit, tune_environment

        n_threads = tune_environment()
    except Exception:
        n_threads = None
    print(f"[ML] Lendo dataset: {DATA}")
    try:
        from ml.utils.perf import fast_read_csv

        df = fast_read_csv(str(DATA), parse_dates=["ts"])
    except Exception:
        df = pd.read_csv(DATA, parse_dates=["ts"])

    feature_cols = [
        "ret_1",
        "ret_5",
        "ret_10",
        "ma_5",
        "ma_10",
        "ma_20",
        "ma_50",
        "std_5",
        "std_10",
        "std_20",
        "std_50",
        "rsi_14",
        "vol_ema_20",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
    target_col = "target_ret_1"

    X = df[feature_cols].values
    y = df[target_col].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=42,
    )

    print("[ML] Treinando RandomForest...")
    # Ensure BLAS threads are aligned during fit (avoid oversubscription: 1 thread per BLAS lib)
    try:
        from ml.utils.perf import sklearn_thread_limit

        with sklearn_thread_limit(1):
            model.fit(X_train, y_train)
    except Exception:
        model.fit(X_train, y_train)

    preds = model.predict(X_test)

    # Padroniza nome do modelo salvo para rf_m1.pkl
    MODEL_PKL = MODELS_DIR / "rf_m1.pkl"
    joblib.dump(model, MODEL_PKL)
    print(f"[ML] Modelo salvo em {MODEL_PKL}")
    r2 = r2_score(y_test, preds)
    mae = mean_absolute_error(y_test, preds)

    report = {
        "r2": float(r2),
        "mae": float(mae),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
    }
    print(f"[ML] R2={r2:.4f}  MAE={mae:.6f}")

    # Salva artefatos
    joblib.dump(model, MODEL_PKL)
    FEATURES_JSON.write_text(
        json.dumps(feature_cols, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ML] Modelo salvo em: {MODEL_PKL}")
    print(f"[ML] Features salvas em: {FEATURES_JSON}")
    print(f"[ML] Relatório salvo em: {REPORT_JSON}")


if __name__ == "__main__":
    main()
