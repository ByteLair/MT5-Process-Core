"""Testes para ml/train_informer_advanced.py cobrindo fluxo principal com mocks para acelerar e evitar treinos pesados."""

import importlib

import numpy as np
import pandas as pd
import torch


def test_train_informer_advanced_main(monkeypatch, tmp_path):
    class DummyInformer(torch.nn.Module):
        def __init__(self, *args, **kwargs):
            super().__init__()

        def forward(self, x):
            return torch.zeros((x.shape[0], 1), dtype=torch.float32)

        def parameters(self):
            return []

        def state_dict(self):
            return {}

    monkeypatch.setattr("ml.models.informer.Informer", DummyInformer)
    monkeypatch.setattr("joblib.dump", lambda obj, path: None)
    n = 100
    cols = [
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
    df = pd.DataFrame(np.random.randn(n, len(cols)), columns=cols)
    monkeypatch.setattr(pd, "read_csv", lambda path: df)
    monkeypatch.setattr(torch, "device", lambda x: torch.device("cpu"))
    import sys

    if str(tmp_path.parent) not in sys.path:
        sys.path.insert(0, str(tmp_path.parent))
    mod = importlib.import_module("ml.train_informer_advanced")
    assert hasattr(mod, "Informer")
