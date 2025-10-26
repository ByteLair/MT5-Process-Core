# =============================================================
# Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
# All rights reserved. | Todos os direitos reservados.
# Private License: This code is the exclusive property of Felipe Petracco Carmo.
# Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
# Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
# Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
# =============================================================

"""Testes para o módulo scheduler."""

from unittest.mock import Mock, patch

import joblib
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier


@pytest.fixture
def mock_model(tmp_path):
    """Cria um modelo mock para testes."""
    X = pd.DataFrame(
        {
            "close": [1.0, 1.1, 1.2],
            "volume": [100, 110, 120],
            "spread": [0.0001, 0.0002, 0.0001],
            "rsi": [50.0, 55.0, 60.0],
            "macd": [0.001, 0.002, 0.003],
            "macd_signal": [0.001, 0.0015, 0.002],
            "macd_hist": [0.0, 0.0005, 0.001],
            "atr": [0.01, 0.011, 0.012],
            "ma60": [1.0, 1.05, 1.1],
            "ret_1": [0.01, 0.02, 0.01],
        }
    )
    y = pd.Series([1, 0, 1])

    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X, y)

    model_path = tmp_path / "rf_m1.pkl"
    joblib.dump(model, model_path)

    return model_path


def test_scheduler_load_model(mock_model, monkeypatch):
    """Testa carregamento de modelo no scheduler."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///")
    monkeypatch.setenv("MODELS_DIR", str(mock_model.parent))

    from ml.scheduler import load_model

    model = load_model()
    assert model is not None
    assert hasattr(model, "predict_proba")


def test_scheduler_tick_function_with_empty_data(mock_model, monkeypatch):
    """Testa função tick do scheduler quando não há dados."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///")
    monkeypatch.setenv("MODELS_DIR", str(mock_model.parent))
    monkeypatch.setenv("SYMBOLS", "EURUSD")

    from ml.scheduler import tick

    # Mock do engine para retornar DataFrame vazio
    with patch("ml.scheduler.engine") as mock_engine:
        mock_conn = Mock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        with patch("pandas.read_sql", return_value=pd.DataFrame()):
            # Não deve lançar erro quando DataFrame está vazio
            tick()
            # Execute não deve ser chamado se não há dados
            assert not mock_conn.execute.called


def test_scheduler_tick_function_with_data(mock_model, monkeypatch):
    """Testa função tick do scheduler com dados."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///")
    monkeypatch.setenv("MODELS_DIR", str(mock_model.parent))
    monkeypatch.setenv("SYMBOLS", "EURUSD")

    from ml.scheduler import FEATURES, tick

    # Criar DataFrame mock com features necessárias
    mock_df = pd.DataFrame(
        {
            "ts": pd.date_range("2025-01-01", periods=30, freq="1min"),
            **{feat: [1.0] * 30 for feat in FEATURES},
        }
    )

    with patch("ml.scheduler.engine") as mock_engine:
        mock_conn = Mock()
        mock_engine.begin.return_value.__enter__.return_value = mock_conn

        with patch("pandas.read_sql", return_value=mock_df):
            tick()
            # Execute deve ser chamado para inserir sinal
            assert mock_conn.execute.called


def test_scheduler_features_constant():
    """Testa se a constante FEATURES está definida corretamente."""
    from ml.scheduler import FEATURES

    assert isinstance(FEATURES, list)
    assert len(FEATURES) > 0
    assert "close" in FEATURES
    assert "rsi" in FEATURES


def test_scheduler_symbols_from_env(monkeypatch):
    """Testa parsing de símbolos da variável de ambiente."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///")
    monkeypatch.setenv("SYMBOLS", "EURUSD,GBPUSD,USDJPY")

    # Reimportar para pegar nova env var
    import importlib

    import ml.scheduler

    importlib.reload(ml.scheduler)

    from ml.scheduler import SYMBOLS

    assert isinstance(SYMBOLS, list)
    assert len(SYMBOLS) == 3
    assert "EURUSD" in SYMBOLS


def test_scheduler_models_dir_default():
    """Testa diretório padrão de modelos."""
    from ml.scheduler import MODELS_DIR

    assert MODELS_DIR is not None
    assert isinstance(MODELS_DIR, str)
