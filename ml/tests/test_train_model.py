"""Testes para ml/train_model.py cobrindo o fluxo principal sem treinos pesados."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


# Classe FastRF no nível de módulo para ser serializável (pickle)
class FastRF(RandomForestRegressor):
    """RandomForest rápido para testes - menos árvores e profundidade limitada."""

    def __init__(
        self,
        n_estimators=10,
        max_depth=5,
        min_samples_leaf=2,
        n_jobs=1,
        random_state=42,
        **kwargs,
    ):
        super().__init__(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            n_jobs=n_jobs,
            random_state=random_state,
        )


def build_synthetic_dataset(tmp_path: Path) -> Path:
    # Colunas exigidas por train_model.py
    cols = [
        "ts",
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
        "target_ret_1",
    ]
    n = 120
    data = {
        "ts": pd.date_range("2025-01-01", periods=n, freq="min"),
        "ret_1": np.random.randn(n) * 0.001,
        "ret_5": np.random.randn(n) * 0.002,
        "ret_10": np.random.randn(n) * 0.003,
        "ma_5": np.random.rand(n),
        "ma_10": np.random.rand(n),
        "ma_20": np.random.rand(n),
        "ma_50": np.random.rand(n),
        "std_5": np.random.rand(n) * 0.01,
        "std_10": np.random.rand(n) * 0.01,
        "std_20": np.random.rand(n) * 0.01,
        "std_50": np.random.rand(n) * 0.01,
        "rsi_14": np.random.rand(n) * 100,
        "vol_ema_20": np.random.rand(n),
        "open": np.random.rand(n) * 2 + 100,
        "high": np.random.rand(n) * 2 + 101,
        "low": np.random.rand(n) * 2 + 99,
        "close": np.random.rand(n) * 2 + 100,
        "volume": (np.random.rand(n) * 1000).astype(int),
        "target_ret_1": np.random.randn(n) * 0.002,
    }
    df = pd.DataFrame(data, columns=cols)
    data_dir = tmp_path / "ml" / "data"
    models_dir = tmp_path / "ml" / "models"
    data_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    csv_path = data_dir / "training_dataset.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


def test_train_model_main_flow(tmp_path, monkeypatch):
    """Testa o fluxo completo de train_model.main() com dataset sintético."""
    # Construir dataset
    csv_path = build_synthetic_dataset(tmp_path)

    # Importar módulo train_model
    import ml.train_model as mod

    # Monkeypatch paths para usar diretórios temporários
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(mod, "DATA", csv_path)
    monkeypatch.setattr(mod, "MODELS_DIR", models_dir)
    monkeypatch.setattr(mod, "FEATURES_JSON", models_dir / "feature_list.json")
    monkeypatch.setattr(mod, "MODEL_PKL", models_dir / "rf_m1.pkl")
    monkeypatch.setattr(mod, "REPORT_JSON", models_dir / "last_train_report.json")

    # Tornar o treinamento mais rápido substituindo o RandomForestRegressor pela versão rápida
    monkeypatch.setattr(mod, "RandomForestRegressor", FastRF, raising=False)

    # Executar main()
    mod.main()

    # Artefatos esperados
    model_pkl = models_dir / "rf_m1.pkl"
    features_json = models_dir / "feature_list.json"
    report_json = models_dir / "last_train_report.json"

    assert model_pkl.exists(), "Modelo não foi salvo"
    assert features_json.exists(), "Lista de features não foi salva"
    assert report_json.exists(), "Relatório não foi salvo"

    # Verificar que o modelo carrega e faz previsão
    model = joblib.load(model_pkl)
    sample = pd.read_csv(csv_path).head(5)
    feature_cols = json.loads(features_json.read_text(encoding="utf-8"))
    preds = model.predict(sample[feature_cols].values)
    assert preds.shape[0] == 5
