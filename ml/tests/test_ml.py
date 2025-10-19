import pytest
import os
import joblib
import pandas as pd
from ml.worker.train import DB_URL, MODELS_DIR, engine
from sklearn.ensemble import RandomForestClassifier

def test_db_connection():
    df = pd.read_sql("SELECT 1 as test", engine)
    assert df.iloc[0]["test"] == 1

def test_training_and_model_save(tmp_path):
    # Simula dados
    X = pd.DataFrame({
        "close": [1,2,3], "volume": [10,20,30], "spread": [0.1,0.2,0.3],
        "rsi": [50,60,70], "macd": [0.1,0.2,0.3], "macd_signal": [0.1,0.2,0.3],
        "macd_hist": [0.1,0.2,0.3], "atr": [0.1,0.2,0.3], "ma60": [1,2,3], "ret_1": [0.01,0.02,0.03]
    })
    y = pd.Series([1,0,1])
    m = RandomForestClassifier(n_estimators=10, random_state=42)
    m.fit(X, y)
    path = tmp_path / "rf_m1_test.pkl"
    joblib.dump(m, path)
    assert os.path.exists(path)
    loaded = joblib.load(path)
    assert hasattr(loaded, "predict")

def test_model_predict():
    X = pd.DataFrame({
        "close": [1,2], "volume": [10,20], "spread": [0.1,0.2],
        "rsi": [50,60], "macd": [0.1,0.2], "macd_signal": [0.1,0.2],
        "macd_hist": [0.1,0.2], "atr": [0.1,0.2], "ma60": [1,2], "ret_1": [0.01,0.02]
    })
    y = pd.Series([1,0])
    m = RandomForestClassifier(n_estimators=10, random_state=42)
    m.fit(X, y)
    preds = m.predict(X)
    assert len(preds) == 2
    assert set(preds).issubset({0,1})
