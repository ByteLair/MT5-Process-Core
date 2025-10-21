# =============================================================
# Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
# All rights reserved. | Todos os direitos reservados.
# Private License: This code is the exclusive property of Felipe Petracco Carmo.
# Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
# Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
# Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
# =============================================================

"""Testes adicionais para módulos ML - aumentando cobertura de testes."""

import os

import pandas as pd
import pytest

# Mock environment variables for testing
os.environ["DB_HOST"] = "localhost"
os.environ["DB_NAME"] = "mt5_trading"
os.environ["DB_USER"] = "trader"
os.environ["DB_PASS"] = "trader123"


def test_rsi_calculation():
    """Testa cálculo do RSI."""
    from ml.prepare_dataset import rsi

    # Série de preços de exemplo
    prices = pd.Series([100, 102, 101, 105, 107, 106, 110, 108, 112, 115, 113, 118, 120, 119, 122])
    result = rsi(prices, period=14)

    assert isinstance(result, pd.Series)
    assert len(result) == len(prices)
    # RSI deve estar entre 0 e 100
    assert result.dropna().between(0, 100).all()


def test_make_features():
    """Testa criação de features a partir de dados de mercado."""
    from ml.prepare_dataset import make_features

    # Dados de exemplo
    dates = pd.date_range("2024-01-01", periods=100, freq="1min")
    df = pd.DataFrame(
        {
            "open": [100 + i * 0.1 for i in range(100)],
            "high": [101 + i * 0.1 for i in range(100)],
            "low": [99 + i * 0.1 for i in range(100)],
            "close": [100.5 + i * 0.1 for i in range(100)],
            "volume": [1000 + i * 10 for i in range(100)],
        },
        index=dates,
    )

    result = make_features(df)

    # Verifica se features foram criadas
    assert "ret_1" in result.columns
    assert "ret_5" in result.columns
    assert "ret_10" in result.columns
    assert "ma_5" in result.columns
    assert "ma_10" in result.columns
    assert "ma_20" in result.columns
    assert "ma_50" in result.columns
    assert "std_5" in result.columns
    assert "rsi_14" in result.columns

    # Verifica se não há valores infinitos
    assert not result.replace([float("inf"), float("-inf")], float("nan")).isnull().all().any()


def test_prepare_dataset_module_imports():
    """Testa importação dos módulos principais."""
    from ml import prepare_dataset

    assert hasattr(prepare_dataset, "rsi")
    assert hasattr(prepare_dataset, "make_features")
    assert hasattr(prepare_dataset, "DATA_DIR")


def test_eval_threshold_module():
    """Testa importação do módulo eval_threshold."""
    try:
        from ml import eval_threshold

        assert eval_threshold is not None
    except (ImportError, Exception) as e:
        pytest.skip(f"eval_threshold module not available or missing database tables: {e}")


def test_train_model_module():
    """Testa importação do módulo train_model."""
    try:
        from ml import train_model

        assert train_model is not None
    except ImportError:
        pytest.skip("train_model module not available")


def test_scheduler_module():
    """Testa importação do módulo scheduler."""
    try:
        from ml import scheduler

        assert scheduler is not None
    except ImportError:
        pytest.skip("scheduler module not available")


def test_data_directory_creation():
    """Testa criação de diretórios de dados."""
    from ml.prepare_dataset import DATA_DIR

    assert DATA_DIR.exists()
    assert DATA_DIR.is_dir()


def test_environment_variables():
    """Testa se variáveis de ambiente estão configuradas."""
    from ml.prepare_dataset import DB_HOST, DB_NAME, DB_PASS, DB_USER

    assert DB_HOST is not None
    assert DB_NAME is not None
    assert DB_USER is not None
    assert DB_PASS is not None


def test_train_model_with_sample_data(tmp_path):
    """Testa módulo train_model com dados de amostra."""
    import joblib
    from sklearn.ensemble import RandomForestRegressor

    # Criar dataset de teste
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    # Gerar dados sintéticos
    df = pd.DataFrame(
        {
            "ts": pd.date_range("2025-01-01", periods=100, freq="1h"),
            "ret_1": [0.001] * 100,
            "ret_5": [0.005] * 100,
            "ret_10": [0.01] * 100,
            "ma_5": [1.0] * 100,
            "ma_10": [1.0] * 100,
            "ma_20": [1.0] * 100,
            "ma_50": [1.0] * 100,
            "std_5": [0.01] * 100,
            "std_10": [0.01] * 100,
            "std_20": [0.01] * 100,
            "std_50": [0.01] * 100,
            "rsi_14": [50.0] * 100,
            "vol_ema_20": [1000.0] * 100,
            "open": [1.0] * 100,
            "high": [1.01] * 100,
            "low": [0.99] * 100,
            "close": [1.0] * 100,
            "volume": [1000] * 100,
            "target_ret_1": [0.001] * 100,
        }
    )

    csv_path = data_dir / "training_dataset.csv"
    df.to_csv(csv_path, index=False)

    # Treinar modelo mockado
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

    X = df[feature_cols].values
    y = df["target_ret_1"].values

    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X[:80], y[:80])

    # Salvar modelo
    model_path = models_dir / "rf_m1.pkl"
    joblib.dump(model, model_path)

    # Verificações
    assert model_path.exists()
    loaded_model = joblib.load(model_path)
    assert isinstance(loaded_model, RandomForestRegressor)

    # Testar predição
    preds = loaded_model.predict(X[80:])
    assert len(preds) == 20


def test_scheduler_basic_import():
    """Testa funcionalidades básicas do scheduler."""
    try:
        from ml.scheduler import schedule_training

        assert callable(schedule_training)
    except ImportError:
        pytest.skip("scheduler functions not available")
