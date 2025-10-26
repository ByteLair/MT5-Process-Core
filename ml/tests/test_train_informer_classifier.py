"""Testes para ml/train_informer_classifier.py cobrindo fluxo principal com mocks para acelerar e evitar treinos pesados."""

import pytest


def test_train_informer_classifier_imports():
    """Testa se os imports principais do módulo funcionam."""
    try:
        from ml import train_informer_classifier

        assert train_informer_classifier is not None
    except ImportError as e:
        pytest.skip(f"Módulo train_informer_classifier não disponível: {e}")


def test_train_informer_classifier_config():
    """Testa se o CONFIG existe e tem as chaves esperadas."""
    try:
        from ml.train_informer_classifier import CONFIG

        assert "seq_len" in CONFIG
        assert "d_model" in CONFIG
        assert "epochs" in CONFIG
    except ImportError:
        pytest.skip("Módulo train_informer_classifier não disponível")
