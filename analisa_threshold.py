import joblib
import numpy as np
import pandas as pd

# Carregar dados e modelo
csv_path = "ml/data/training_dataset.csv"
model_path = "ml/models/rf_m1.pkl"

df = pd.read_csv(csv_path)
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

model = joblib.load(model_path)
preds = model.predict(X)

positives = y > 0


# Testa vários thresholds para encontrar o que gera ~58% de trades positivas previstas
def busca_threshold(target_prop=0.58):
    best_thr = None
    best_diff = 1.0
    for thr in np.arange(0, 0.002, 0.00001):
        pred_positives = preds > thr
        prop = np.mean(pred_positives)
        diff = abs(prop - target_prop)
        if diff < best_diff:
            best_diff = diff
            best_thr = thr
    return best_thr


threshold = busca_threshold(0.58)
pred_positives = preds > threshold
precision = np.sum(pred_positives & positives) / max(np.sum(pred_positives), 1)
recall = np.sum(pred_positives & positives) / max(np.sum(positives), 1)

print(f"Threshold ótimo para 58%: {threshold:.5f}")
print("Precisão trades positivas:", precision)
print("Recall trades positivas:", recall)
print("Proporção de trades positivas previstas:", np.mean(pred_positives))
print("Proporção real de trades positivas:", np.mean(positives))
