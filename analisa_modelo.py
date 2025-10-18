import joblib
import pandas as pd
import numpy as np

# Carregar dados e modelo
csv_path = 'ml/data/training_dataset.csv'
model_path = 'ml/models/rf_m1.pkl'

df = pd.read_csv(csv_path)
feature_cols = [
    "ret_1","ret_5","ret_10","ma_5","ma_10","ma_20","ma_50",
    "std_5","std_10","std_20","std_50","rsi_14","vol_ema_20",
    "open","high","low","close","volume"
]
X = df[feature_cols].values
y = df['target_ret_1'].values

model = joblib.load(model_path)
preds = model.predict(X)

positives = (y > 0)
pred_positives = (preds > 0)

precision = np.sum(pred_positives & positives) / max(np.sum(pred_positives), 1)
recall = np.sum(pred_positives & positives) / max(np.sum(positives), 1)

print("Precisão trades positivas:", precision)
print("Recall trades positivas:", recall)
print("Proporção de trades positivas previstas:", np.mean(pred_positives))
print("Proporção real de trades positivas:", np.mean(positives))
