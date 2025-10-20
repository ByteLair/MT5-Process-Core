import json
import os
import sys
from itertools import product

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sklearn.utils import resample
from torch import nn

# Ensure project root is on sys.path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ml.models.informer import Informer


def add_features(df):
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["bb_ma20"] = df["close"].rolling(window=20).mean()
    df["bb_std20"] = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_ma20"] + 2 * df["bb_std20"]
    df["bb_lower"] = df["bb_ma20"] - 2 * df["bb_std20"]
    df["volatility_10"] = df["close"].rolling(window=10).std()
    df["volatility_20"] = df["close"].rolling(window=20).std()
    for lag in [1, 2, 3, 5, 10]:
        df[f"close_lag_{lag}"] = df["close"].shift(lag)
        df[f"volume_lag_{lag}"] = df["volume"].shift(lag)
    df["hour"] = pd.to_datetime(df["ts"]).dt.hour
    df["weekday"] = pd.to_datetime(df["ts"]).dt.weekday
    return df


DATA_PATH = "ml/data/training_dataset.csv"
TARGET_COL = "target_ret_1"
df = pd.read_csv(DATA_PATH)
df = add_features(df)
df = df.dropna().reset_index(drop=True)
drop_cols = ["ts"]
numeric_cols = [
    c for c in df.columns if np.issubdtype(df[c].dtype, np.number) and c not in drop_cols
]
features = [c for c in numeric_cols if c != TARGET_COL]
X = df[features].values
y_continuous = df[TARGET_COL].values
y = (y_continuous > 0).astype(np.float32)

# Oversample positivos
X_pos = X[y == 1]
y_pos = y[y == 1]
X_neg = X[y == 0]
y_neg = y[y == 0]
X_pos_upsampled, y_pos_upsampled = resample(
    X_pos, y_pos, replace=True, n_samples=len(y_neg), random_state=42
)
X_bal = np.vstack([X_neg, X_pos_upsampled])
y_bal = np.hstack([y_neg, y_pos_upsampled])
idx = np.random.permutation(len(y_bal))
X, y = X_bal[idx], y_bal[idx]

# Normalização
X_mean = X.mean(axis=0)
X_std = X.std(axis=0) + 1e-8
X = (X - X_mean) / X_std


def create_sequences(X, y, seq_len):
    Xs, ys = [], []
    for i in range(len(X) - seq_len):
        Xs.append(X[i : i + seq_len])
        ys.append(y[i + seq_len])
    return np.array(Xs), np.array(ys)


# Grid de hiperparâmetros
param_grid = {
    "seq_len": [32, 64, 128],
    "d_model": [64, 128, 256],
    "e_layers": [2, 3, 4],
    "dropout": [0.1, 0.2, 0.3],
    "lr": [1e-3, 5e-4],
}

results = []

for seq_len, d_model, e_layers, dropout, lr in product(
    param_grid["seq_len"],
    param_grid["d_model"],
    param_grid["e_layers"],
    param_grid["dropout"],
    param_grid["lr"],
):
    print(
        f"\n=== Treinando: seq_len={seq_len}, d_model={d_model}, e_layers={e_layers}, dropout={dropout}, lr={lr} ==="
    )
    X_seq, y_seq = create_sequences(X, y, seq_len)
    n = len(X_seq)
    train_end = int(0.6 * n)
    val_end = int(0.8 * n)
    X_train, y_train = X_seq[:train_end], y_seq[:train_end]
    X_val, y_val = X_seq[train_end:val_end], y_seq[train_end:val_end]
    X_test, y_test = X_seq[val_end:], y_seq[val_end:]
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
        seq_len=seq_len,
        d_model=d_model,
        n_heads=4,
        e_layers=e_layers,
        d_ff=d_model * 2,
        dropout=dropout,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    loss_fn = nn.BCEWithLogitsLoss()
    best_val_loss = float("inf")
    patience = 2
    patience_counter = 0
    for epoch in range(6):  # epochs reduzidos para grid
        model.train()
        train_loss = 0
        for i in range(0, len(X_train), 64):
            xb = X_train[i : i + 64]
            yb = y_train[i : i + 64]
            optimizer.zero_grad()
            logits = model(xb).squeeze(-1)
            loss = loss_fn(logits, yb)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        model.eval()
        with torch.no_grad():
            val_logits = model(X_val).squeeze(-1)
            val_loss = loss_fn(val_logits, y_val).item()
            val_probs = torch.sigmoid(val_logits).numpy()
            val_preds = (val_probs > 0.5).astype(int)
            val_precision = precision_score(y_val.numpy(), val_preds, zero_division=0)
            val_recall = recall_score(y_val.numpy(), val_preds, zero_division=0)
        print(
            f"Epoch {epoch+1}/6 | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Prec: {val_precision:.3f} | Rec: {val_recall:.3f}"
        )
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), "ml/models/informer_grid_best.pt")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"✓ Early stopping na época {epoch+1}")
                break
    model.load_state_dict(torch.load("ml/models/informer_grid_best.pt"))
    model.eval()
    with torch.no_grad():
        test_logits = model(X_test).squeeze(-1)
        test_probs = torch.sigmoid(test_logits).numpy()
    test_preds_05 = (test_probs > 0.5).astype(int)
    y_test_np = y_test.numpy()
    precision_05 = precision_score(y_test_np, test_preds_05, zero_division=0)
    recall_05 = recall_score(y_test_np, test_preds_05, zero_division=0)
    auc = roc_auc_score(y_test_np, test_probs)
    results.append(
        {
            "seq_len": seq_len,
            "d_model": d_model,
            "e_layers": e_layers,
            "dropout": dropout,
            "lr": lr,
            "precision": precision_05,
            "recall": recall_05,
            "auc_roc": auc,
        }
    )
    print(f"Test Precision: {precision_05:.4f} | Recall: {recall_05:.4f} | AUC: {auc:.4f}")

with open("ml/models/informer_gridsearch_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("✓ Grid search concluído e resultados salvos!")
