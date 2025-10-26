"""Testes para ml/train_worker.py com mocks de banco e filesystem."""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd


def test_train_worker_with_data(tmp_path, monkeypatch):
    # Copiar script para workspace temporário não é necessário; vamos interceptar IO
    # Mock psycopg2.connect -> retorna objeto com cursor/engine fictício
    fake_conn = Mock()
    # pandas.read_sql deve retornar dados suficientes
    df = pd.DataFrame(
        {
            "mean_close": np.random.rand(200),
            "volatility": np.random.rand(200) * 0.01,
            "pct_change": np.random.randn(200) * 0.001,
            "fwd_ret_5": np.random.randn(200),
        }
    )

    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    with (
        patch("psycopg2.connect", return_value=fake_conn),
        patch("pandas.read_sql", return_value=df),
        patch("os.makedirs"),
        patch("joblib.dump") as dump_mock,
        patch("sklearn.ensemble.RandomForestClassifier") as rf_cls,
    ):
        # Configurar RandomForest rápido
        from sklearn.ensemble import RandomForestClassifier as _RF

        class FastRF(_RF):
            def __init__(self, *args, **kwargs):
                super().__init__(n_estimators=10, max_depth=5, random_state=42)

        rf_cls.side_effect = FastRF
        # Executar o script importando-o e deixando rodar até o final
        import importlib
        import sys

        # Inserir o diretório raiz no sys.path para poder importar ml.train_worker
        if str(Path.cwd()) not in sys.path:
            sys.path.insert(0, str(Path.cwd()))
        mod = importlib.import_module("ml.train_worker")

        # Verificações de chamada de dump
        assert dump_mock.called, "Modelo não foi salvo"
        args, kwargs = dump_mock.call_args
        # Primeiro argumento é o modelo, segundo é o caminho
        saved_path = args[1]
        # Garantir que salva no diretório /models (do script). Não alteramos script, então verifique apenas string
        assert str(saved_path).endswith("latest_model.pkl")


def test_train_worker_empty_dataset(monkeypatch):
    # Se o DataFrame estiver vazio, o script deve imprimir mensagem e encerrar com SystemExit
    fake_conn = Mock()
    empty_df = pd.DataFrame()

    with (
        patch("psycopg2.connect", return_value=fake_conn),
        patch("pandas.read_sql", return_value=empty_df),
    ):
        import importlib
        import sys

        if str(Path.cwd()) not in sys.path:
            sys.path.insert(0, str(Path.cwd()))

        try:
            importlib.reload(importlib.import_module("ml.train_worker"))
            assert False, "Era esperado SystemExit quando dataset vazio"
        except SystemExit:
            pass
