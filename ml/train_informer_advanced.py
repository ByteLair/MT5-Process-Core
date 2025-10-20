import json
import os
import sys

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_score
from sklearn.utils import resample
from torch import nn

# Ensure project root is on sys.path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ml.models.informer import Informer

# =====================
# CONFIGURAÇÕES
# =====================
CONFIG = {
    "seq_len": 64,  # Janela maior
    "d_model": 128,  # Modelo mais expressivo
    "n_heads": 4,
    "e_layers": 3,
    "d_ff": 256,
    "dropout": 0.2,
    "batch_size": 64,
    "epochs": 15,
    "lr": 1e-3,
    "oversample": True,  # Balanceamento de classes
    "augment": True,  # Bootstrapping
}


# =====================
# FEATURE ENGINEERING
# =====================
def add_features(df):
    # MACD
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    # Bollinger Bands
    df["bb_ma20"] = df["close"].rolling(window=20).mean()
    df["bb_std20"] = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_ma20"] + 2 * df["bb_std20"]
    df["bb_lower"] = df["bb_ma20"] - 2 * df["bb_std20"]
    # Volatilidade
    df["volatility_10"] = df["close"].rolling(window=10).std()
    df["volatility_20"] = df["close"].rolling(window=20).std()
    # Lags
    for lag in [1, 2, 3, 5, 10]:
        df[f"close_lag_{lag}"] = df["close"].shift(lag)
        df[f"volume_lag_{lag}"] = df["volume"].shift(lag)
    # Contexto
    df["hour"] = pd.to_datetime(df["ts"]).dt.hour
    df["weekday"] = pd.to_datetime(df["ts"]).dt.weekday
    return df


# =====================
# CARREGAR E PREPARAR DADOS
# =====================
DATA_PATH = "ml/data/training_dataset.csv"
TARGET_COL = "target_ret_1"
df = pd.read_csv(DATA_PATH)
df = add_features(df)

# Remover linhas com NaN gerados pelas features
df = df.dropna().reset_index(drop=True)

# Seleciona apenas colunas numéricas exceto o alvo
drop_cols = ["ts"]
numeric_cols = [
    c for c in df.columns if np.issubdtype(df[c].dtype, np.number) and c not in drop_cols
]
features = [c for c in numeric_cols if c != TARGET_COL]
X = df[features].values
y_continuous = df[TARGET_COL].values

# CLASSIFICAÇÃO BINÁRIA: target = 1 se retorno > 0 (trade positivo), 0 caso contrário
y = (y_continuous > 0).astype(np.float32)
pos_ratio = y.mean()

# Normalização
X_mean = X.mean(axis=0)
X_std = X.std(axis=0) + 1e-8
X = (X - X_mean) / X_std

# =====================
# BALANCEAMENTO DE CLASSES (OVERSAMPLING)
# =====================
if CONFIG["oversample"]:
    X_pos = X[y == 1]
    y_pos = y[y == 1]
    X_neg = X[y == 0]
    y_neg = y[y == 0]
    # Oversample positivos para igualar negativos
    X_pos_upsampled, y_pos_upsampled = resample(
        X_pos, y_pos, replace=True, n_samples=len(y_neg), random_state=42
    )
    X_bal = np.vstack([X_neg, X_pos_upsampled])
    y_bal = np.hstack([y_neg, y_pos_upsampled])
    # Shuffle
    idx = np.random.permutation(len(y_bal))
    X, y = X_bal[idx], y_bal[idx]

# =====================
# DATA AUGMENTATION (BOOTSTRAPPING)
# =====================
if CONFIG["augment"]:
    # Bootstrapping simples: duplicar 20% dos dados de treino
    n_boot = int(0.2 * len(X))
    X_boot, y_boot = resample(X, y, replace=True, n_samples=n_boot, random_state=123)
    X = np.vstack([X, X_boot])
    y = np.hstack([y, y_boot])


# =====================
# PREPARAR SEQUÊNCIAS
# =====================
def create_sequences(X, y, seq_len):
    Xs, ys = [], []
    for i in range(len(X) - seq_len):
        Xs.append(X[i : i + seq_len])
        ys.append(y[i + seq_len])
    return np.array(Xs), np.array(ys)


X_seq, y_seq = create_sequences(X, y, CONFIG["seq_len"])

# Separar treino/validação/teste (60/20/20)
n = len(X_seq)
train_end = int(0.6 * n)
val_end = int(0.8 * n)
X_train, y_train = X_seq[:train_end], y_seq[:train_end]
X_val, y_val = X_seq[train_end:val_end], y_seq[train_end:val_end]
X_test, y_test = X_seq[val_end:], y_seq[val_end:]

# =====================
# TREINAMENTO
# =====================
device = torch.device("cpu")
X_train = torch.tensor(X_train, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.float32)
X_val = torch.tensor(X_val, dtype=torch.float32)
y_val = torch.tensor(y_val, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_test = torch.tensor(y_test, dtype=torch.float32)

model = Informer(
    enc_in=X_train.shape[2],
    c_out=1,
    seq_len=CONFIG["seq_len"],
    d_model=CONFIG["d_model"],
    n_heads=CONFIG["n_heads"],
    e_layers=CONFIG["e_layers"],
    d_ff=CONFIG["d_ff"],
    dropout=CONFIG["dropout"],
)
optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG["lr"], weight_decay=1e-5)
loss_fn = nn.BCEWithLogitsLoss()

best_val_loss = float("inf")
patience = 3
patience_counter = 0
for epoch in range(CONFIG["epochs"]):
    model.train()
    train_loss = 0
    for i in range(0, len(X_train), CONFIG["batch_size"]):
        xb = X_train[i : i + CONFIG["batch_size"]]
        yb = y_train[i : i + CONFIG["batch_size"]]
        optimizer.zero_grad()
        logits = model(xb).squeeze(-1)
        loss = loss_fn(logits, yb)
        loss.backward()
        optimizer.step()
        train_loss += loss.item()
    # Validação
    model.eval()
    with torch.no_grad():
        val_logits = model(X_val).squeeze(-1)
        val_loss = loss_fn(val_logits, y_val).item()
        val_probs = torch.sigmoid(val_logits).numpy()
        val_preds = (val_probs > 0.5).astype(int)
        val_precision = precision_score(y_val.numpy(), val_preds, zero_division=0)
        val_recall = recall_score(y_val.numpy(), val_preds, zero_division=0)
    print(
        f"Epoch {epoch+1}/{CONFIG['epochs']} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Prec: {val_precision:.3f} | Rec: {val_recall:.3f}"
    )
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        patience_counter = 0
        torch.save(model.state_dict(), "ml/models/informer_best_advanced.pt")
    else:
        patience_counter += 1
        if patience_counter >= patience:
            print(f"✓ Early stopping na época {epoch+1}")
            break

model.load_state_dict(torch.load("ml/models/informer_best_advanced.pt"))

# =====================
# AVALIAÇÃO
# =====================
model.eval()
with torch.no_grad():
    test_logits = model(X_test).squeeze(-1)
    test_probs = torch.sigmoid(test_logits).numpy()
test_preds_05 = (test_probs > 0.5).astype(int)
y_test_np = y_test.numpy()
precision_05 = precision_score(y_test_np, test_preds_05, zero_division=0)
recall_05 = recall_score(y_test_np, test_preds_05, zero_division=0)
auc = roc_auc_score(y_test_np, test_probs)
cm = confusion_matrix(y_test_np, test_preds_05)
print("\nThreshold 0.5:")
print(f"  Precision: {precision_05:.4f}")
print(f"  Recall: {recall_05:.4f}")
print(f"  AUC-ROC: {auc:.4f}")
print(f"  Positivos previstos: {test_preds_05.sum()} ({test_preds_05.mean()*100:.1f}%)")
print(f"  Confusion Matrix:\n{cm}")

# Otimização de threshold para atingir ~58% de positivos previstos
target_positive_rate = 0.58
best_threshold = 0.5
best_diff = abs(test_preds_05.mean() - target_positive_rate)
for thresh in np.arange(0.1, 0.9, 0.01):
    preds = (test_probs > thresh).astype(int)
    positive_rate = preds.mean()
    diff = abs(positive_rate - target_positive_rate)
    if diff < best_diff:
        best_diff = diff
        best_threshold = thresh
test_preds_optimized = (test_probs > best_threshold).astype(int)
precision_opt = precision_score(y_test_np, test_preds_optimized, zero_division=0)
recall_opt = recall_score(y_test_np, test_preds_optimized, zero_division=0)
cm_opt = confusion_matrix(y_test_np, test_preds_optimized)
print(f"\nThreshold otimizado: {best_threshold:.3f}")
print(f"  Precision: {precision_opt:.4f}")
print(f"  Recall: {recall_opt:.4f}")
print(
    f"  Positivos previstos: {test_preds_optimized.sum()} ({test_preds_optimized.mean()*100:.1f}%)"
)
print(f"  Confusion Matrix:\n{cm_opt}")

# =====================
# SALVAR MODELO E METADADOS
# =====================
torch.save(model.state_dict(), "ml/models/informer_classifier_advanced.pt")
norm_data = {
    "X_mean": X_mean.tolist(),
    "X_std": X_std.tolist(),
    "features": features,
}
with open("ml/models/informer_normalization_advanced.json", "w") as f:
    json.dump(norm_data, f, indent=2)
report = {
    "model": "Informer",
    "task": "binary_classification",
    "target": "trade_positivo (target_ret_1 > 0)",
    "config": CONFIG,
    "metrics": {
        "threshold_0.5": {
            "precision": float(precision_05),
            "recall": float(recall_05),
            "auc_roc": float(auc),
            "positive_predictions_pct": float(test_preds_05.mean() * 100),
        },
        "threshold_optimized": {
            "threshold": float(best_threshold),
            "precision": float(precision_opt),
            "recall": float(recall_opt),
            "positive_predictions_pct": float(test_preds_optimized.mean() * 100),
        },
    },
}
with open("ml/models/informer_report_advanced.json", "w") as f:
    json.dump(report, f, indent=2)
print("✓ Modelo, normalização e relatório salvos!")
