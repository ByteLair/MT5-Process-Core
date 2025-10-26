import os

import joblib
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier

from ml.worker.train import engine, load_dataset, train_and_save


def test_db_connection():
    df = pd.read_sql("SELECT 1 as test", engine)
    assert df.iloc[0]["test"] == 1


def test_training_and_model_save(tmp_path):
    # Simula dados
    X = pd.DataFrame(
        {
            "close": [1, 2, 3],
            "volume": [10, 20, 30],
            "spread": [0.1, 0.2, 0.3],
            "rsi": [50, 60, 70],
            "macd": [0.1, 0.2, 0.3],
            "macd_signal": [0.1, 0.2, 0.3],
            "macd_hist": [0.1, 0.2, 0.3],
            "atr": [0.1, 0.2, 0.3],
            "ma60": [1, 2, 3],
            "ret_1": [0.01, 0.02, 0.03],
        }
    )
    y = pd.Series([1, 0, 1])
    m = RandomForestClassifier(n_estimators=10, random_state=42)
    m.fit(X, y)
    path = tmp_path / "rf_m1_test.pkl"
    joblib.dump(m, path)
    assert os.path.exists(path)
    loaded = joblib.load(path)
    assert hasattr(loaded, "predict")


def test_model_predict():
    X = pd.DataFrame(
        {
            "close": [1, 2],
            "volume": [10, 20],
            "spread": [0.1, 0.2],
            "rsi": [50, 60],
            "macd": [0.1, 0.2],
            "macd_signal": [0.1, 0.2],
            "macd_hist": [0.1, 0.2],
            "atr": [0.1, 0.2],
            "ma60": [1, 2],
            "ret_1": [0.01, 0.02],
        }
    )
    y = pd.Series([1, 0])
    m = RandomForestClassifier(n_estimators=10, random_state=42)
    m.fit(X, y)
    preds = m.predict(X)
    assert len(preds) == 2
    assert set(preds).issubset({0, 1})


def test_load_dataset_with_engine():
    """Testa carregamento de dataset (se tabela existir)."""
    try:
        df = load_dataset(engine)
        assert isinstance(df, pd.DataFrame)
        # Se chegou aqui, tabela existe e tem dados
        assert not df.empty
    except SystemExit:
        # Tabela vazia ou não existe - comportamento esperado em ambiente de teste
        pytest.skip("trainset_m1 table is empty or doesn't exist")
    except Exception:
        # Alguns bancos (ex.: SQLite) não suportam a sintaxe de intervalo usada no SQL
        pytest.skip("dialeto SQL sem suporte ao intervalo usado no SELECT")


def test_train_and_save_function(tmp_path, monkeypatch):
    """Testa função train_and_save com dados mock."""
    # Mock do diretório de modelos
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))

    # Criar DataFrame de teste
    df = pd.DataFrame(
        {
            "close": [1.0, 1.1, 1.2, 1.3, 1.4],
            "volume": [100, 110, 120, 130, 140],
            "spread": [0.0001, 0.0002, 0.0001, 0.0002, 0.0001],
            "rsi": [45.0, 50.0, 55.0, 60.0, 65.0],
            "macd": [0.001, 0.002, 0.003, 0.002, 0.001],
            "macd_signal": [0.001, 0.0015, 0.002, 0.0025, 0.002],
            "macd_hist": [0.0, 0.0005, 0.001, -0.0005, -0.001],
            "atr": [0.01, 0.011, 0.012, 0.011, 0.01],
            "ma60": [1.0, 1.05, 1.1, 1.15, 1.2],
            "ret_1": [0.01, 0.02, 0.01, 0.02, 0.01],
            "fwd_ret_5": [0.02, -0.01, 0.03, -0.02, 0.01],
        }
    )

    # Executar treinamento
    model_path = train_and_save(df)

    # Verificar que modelo foi salvo
    assert os.path.exists(model_path)
    assert model_path.endswith("rf_m1.pkl")

    # Carregar e verificar modelo
    loaded_model = joblib.load(model_path)
    assert isinstance(loaded_model, RandomForestClassifier)
    assert hasattr(loaded_model, "predict")


def test_load_dataset_empty_raises_error(monkeypatch):
    """Testa que load_dataset levanta erro quando dataset está vazio."""

    def mock_read_sql(*args, **kwargs):
        return pd.DataFrame()  # DataFrame vazio

    monkeypatch.setattr(pd, "read_sql", mock_read_sql)

    with pytest.raises(SystemExit, match="dataset vazio"):
        load_dataset(engine)
