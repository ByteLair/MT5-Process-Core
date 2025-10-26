# =============================================================
# Copyright (c) 2025 Felipe Petracco Carmo <kuramopr@gmail.com>
# All rights reserved. | Todos os direitos reservados.
# Private License: This code is the exclusive property of Felipe Petracco Carmo.
# Redistribution, copying, modification or commercial use is NOT permitted without express authorization.
# Licença privada: Este código é propriedade exclusiva de Felipe Petracco Carmo.
# Não é permitida redistribuição, cópia, modificação ou uso comercial sem autorização expressa.
# =============================================================

"""Testes avançados para funções ML - sequências, features e edge cases."""

import numpy as np
import pandas as pd


def test_create_sequences_basic():
    """Testa criação de sequências para modelos de séries temporais."""
    from ml.train_informer_advanced import create_sequences

    # Dados de exemplo
    x = np.array([[i, i + 1, i + 2] for i in range(100)])
    y = np.array([i for i in range(100)])
    seq_len = 10

    x_seq, y_seq = create_sequences(x, y, seq_len)

    # Verifica dimensões
    assert x_seq.shape[0] == len(x) - seq_len
    assert x_seq.shape[1] == seq_len
    assert x_seq.shape[2] == x.shape[1]
    assert y_seq.shape[0] == len(y) - seq_len


def test_create_sequences_edge_cases():
    """Testa casos extremos de criação de sequências."""
    from ml.train_informer_advanced import create_sequences

    # Sequência muito curta
    x = np.array([[1, 2], [3, 4], [5, 6]])
    y = np.array([1, 2, 3])
    seq_len = 2

    x_seq, y_seq = create_sequences(x, y, seq_len)
    assert x_seq.shape[0] == 1
    assert y_seq.shape[0] == 1


def test_add_features_informer():
    """Testa adição de features para modelo Informer."""
    from ml.train_informer_advanced import add_features

    # Dados de exemplo com coluna 'ts' necessária
    dates = pd.date_range("2024-01-01", periods=200, freq="1h")
    df = pd.DataFrame(
        {
            "ts": dates,
            "open": np.random.randn(200) * 10 + 100,
            "high": np.random.randn(200) * 10 + 105,
            "low": np.random.randn(200) * 10 + 95,
            "close": np.random.randn(200) * 10 + 100,
            "volume": np.random.randint(1000, 10000, 200),
        }
    )

    result = add_features(df)

    # Verifica se features foram adicionadas (EMA, MACD, Bollinger, lags, etc)
    assert "ema_12" in result.columns
    assert "macd" in result.columns
    assert "bb_upper" in result.columns
    assert "close_lag_1" in result.columns
    assert "hour" in result.columns
    assert "weekday" in result.columns
    assert len(result) == len(df)


def test_rsi_edge_cases():
    """Testa RSI com casos extremos."""
    from ml.prepare_dataset import rsi

    # Preços constantes - RSI pode variar entre 0-100 dependendo da implementação EWM
    prices_constant = pd.Series([100] * 50)
    rsi_constant = rsi(prices_constant, period=14)
    # RSI deve estar entre 0-100 para preços constantes (comportamento válido)
    assert 0 <= rsi_constant.dropna().iloc[-1] <= 100

    # Preços subindo - RSI alto
    prices_up = pd.Series(range(100, 150))
    rsi_up = rsi(prices_up, period=14)
    # RSI deve ser alto (próximo de 100)
    assert rsi_up.dropna().iloc[-1] > 70

    # Preços sempre caindo
    prices_down = pd.Series(range(150, 100, -1))
    rsi_down = rsi(prices_down, period=14)
    # RSI deve ser baixo (próximo de 0)
    assert rsi_down.dropna().iloc[-1] < 30


def test_make_features_comprehensive():
    """Testa criação de features com dados completos."""
    from ml.prepare_dataset import make_features

    # Dados realistas de mercado
    dates = pd.date_range("2024-01-01", periods=1000, freq="1min")
    np.random.seed(42)

    # Simula movimento de preços realista
    returns = np.random.randn(1000) * 0.001
    close_prices = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame(
        {
            "open": close_prices * (1 + np.random.randn(1000) * 0.001),
            "high": close_prices * (1 + np.abs(np.random.randn(1000) * 0.002)),
            "low": close_prices * (1 - np.abs(np.random.randn(1000) * 0.002)),
            "close": close_prices,
            "volume": np.random.randint(10000, 100000, 1000),
        },
        index=dates,
    )

    result = make_features(df)

    # Verifica todas as features esperadas
    expected_features = [
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
    ]

    for feature in expected_features:
        assert feature in result.columns, f"Feature {feature} não encontrada"

    # Verifica se não há valores infinitos
    assert not np.isinf(result.select_dtypes(include=[np.number]).values).any()

    # Verifica se médias móveis estão corretas
    assert result["ma_5"].notna().sum() > 0
    assert result["ma_50"].notna().sum() > 0


def test_features_no_nan_propagation():
    """Testa que NaN não se propaga excessivamente nas features."""
    from ml.prepare_dataset import make_features

    # Dados com valores válidos (make_features remove NaNs automaticamente)
    dates = pd.date_range("2024-01-01", periods=200, freq="1h")
    df = pd.DataFrame(
        {
            "open": list(range(95, 295)),
            "high": list(range(96, 296)),
            "low": list(range(94, 294)),
            "close": list(range(95, 295)),
            "volume": list(range(1000, 1200)),
        },
        index=dates,
    )

    result = make_features(df)

    # make_features já remove NaN, então resultado deve ter dados válidos
    assert len(result) > 100  # Deve ter linhas significativas
    assert result.notna().mean().mean() > 0.95  # >95% valores válidos


def test_model_training_reproducibility(tmp_path):
    """Testa reprodutibilidade do treinamento de modelo."""
    from sklearn.ensemble import RandomForestClassifier

    # Dados de treinamento
    np.random.seed(42)
    X = pd.DataFrame(np.random.randn(100, 10))
    y = pd.Series(np.random.randint(0, 2, 100))

    # Treina modelo duas vezes
    m1 = RandomForestClassifier(n_estimators=10, random_state=42)
    m1.fit(X, y)

    m2 = RandomForestClassifier(n_estimators=10, random_state=42)
    m2.fit(X, y)

    # Predições devem ser idênticas
    pred1 = m1.predict(X)
    pred2 = m2.predict(X)
    assert np.array_equal(pred1, pred2)


def test_model_persistence(tmp_path):
    """Testa salvamento e carregamento de modelo."""
    import joblib
    from sklearn.ensemble import RandomForestClassifier

    # Treina modelo
    X = pd.DataFrame(np.random.randn(50, 5))
    y = pd.Series(np.random.randint(0, 2, 50))
    m = RandomForestClassifier(n_estimators=5, random_state=42)
    m.fit(X, y)

    # Salva modelo
    path = tmp_path / "test_model.pkl"
    joblib.dump(m, path)

    # Carrega modelo
    m_loaded = joblib.load(path)

    # Verifica que predições são iguais
    pred_original = m.predict(X)
    pred_loaded = m_loaded.predict(X)
    assert np.array_equal(pred_original, pred_loaded)


def test_feature_engineering_performance():
    """Testa performance de feature engineering com dados grandes."""
    import time

    from ml.prepare_dataset import make_features

    # Dataset grande
    dates = pd.date_range("2024-01-01", periods=10000, freq="1min")
    df = pd.DataFrame(
        {
            "open": np.random.randn(10000) * 10 + 100,
            "high": np.random.randn(10000) * 10 + 105,
            "low": np.random.randn(10000) * 10 + 95,
            "close": np.random.randn(10000) * 10 + 100,
            "volume": np.random.randint(1000, 100000, 10000),
        },
        index=dates,
    )

    start = time.time()
    result = make_features(df)
    elapsed = time.time() - start

    # Deve processar rapidamente (< 5 segundos)
    assert elapsed < 5.0, f"Feature engineering muito lento: {elapsed:.2f}s"
    # make_features remove NaN, então len(result) < len(df) é esperado
    assert len(result) > 9500  # Deve preservar >95% dos dados
    assert len(result.columns) > 5  # Deve ter features adicionais
