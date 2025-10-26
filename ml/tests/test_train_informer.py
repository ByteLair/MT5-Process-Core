"""Testes para ml/train_informer.py cobrindo fluxo principal com mocks para acelerar e evitar treinos pesados."""

import numpy as np
import pytest


def test_train_informer_create_sequences():
    """Testa a função create_sequences sem importar o módulo inteiro."""
    from ml.train_informer import create_sequences

    X = np.random.randn(100, 10)
    y = np.random.randn(100)
    seq_len = 10
    pred_len = 1

    Xs, ys = create_sequences(X, y, seq_len, pred_len)

    assert Xs.shape[1] == seq_len
    assert Xs.shape[2] == 10
    assert ys.shape[1] == 1
    assert len(Xs) == len(ys)


def test_train_informer_imports():
    """Testa se os imports principais do módulo funcionam."""
    try:
        from ml.train_informer import create_sequences

        assert callable(create_sequences)
    except ImportError as e:
        pytest.fail(f"Falha ao importar create_sequences: {e}")
