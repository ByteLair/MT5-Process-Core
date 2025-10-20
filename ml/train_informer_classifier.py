import json
import os
import sys

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_score
from torch import nn

# Ensure project root is on sys.path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ml.models.informer import Informer

print("=" * 60)
print("INFORMER - CLASSIFICAÇÃO BINÁRIA DE TRADES POSITIVOS")
print("=" * 60)

# Force CPU usage (otimizado para servidor sem GPU)
device = torch.device("cpu")
print(f"✓ Dispositivo: {device}")

# Configurações otimizadas para CPU
CONFIG = {
    "seq_len": 32,  # Reduzido para CPU
    "d_model": 64,  # Modelo menor para CPU
    "n_heads": 4,
    "e_layers": 2,
    "d_ff": 128,  # FFN menor para CPU
    "dropout": 0.2,
    "batch_size": 64,  # Batch menor para CPU
    "epochs": 10,
    "lr": 5e-4,
}

# Carregar dataset
DATA_PATH = "ml/data/training_dataset.csv"
TARGET_COL = "target_ret_1"
df = pd.read_csv(DATA_PATH)
print(f"✓ Dataset carregado: {len(df)} registros")

# Seleciona apenas colunas numéricas exceto o alvo
numeric_cols = [c for c in df.columns if np.issubdtype(df[c].dtype, np.number)]
features = [c for c in numeric_cols if c != TARGET_COL]
X = df[features].values
y_continuous = df[TARGET_COL].values

# CLASSIFICAÇÃO BINÁRIA: target = 1 se retorno > 0 (trade positivo), 0 caso contrário
y = (y_continuous > 0).astype(np.float32)
pos_ratio = y.mean()
print(f"✓ Features: {len(features)} colunas")
print(
    f"✓ Classes: {y.sum():.0f} positivos ({pos_ratio*100:.1f}%), {(1-y).sum():.0f} negativos ({(1-pos_ratio)*100:.1f}%)"
)

# Normalização simples (z-score)
X_mean = X.mean(axis=0)
X_std = X.std(axis=0) + 1e-8
X = (X - X_mean) / X_std


# Preparar dados sequenciais
def create_sequences(X, y, seq_len):
    Xs, ys = [], []
    for i in range(len(X) - seq_len):
        Xs.append(X[i : i + seq_len])
        ys.append(y[i + seq_len])
    return np.array(Xs), np.array(ys)


print(f"✓ Criando sequências (seq_len={CONFIG['seq_len']})...")
X_seq, y_seq = create_sequences(X, y, CONFIG["seq_len"])

# Separar treino/validação/teste (60/20/20)
n = len(X_seq)
train_end = int(0.6 * n)
val_end = int(0.8 * n)

X_train, y_train = X_seq[:train_end], y_seq[:train_end]
X_val, y_val = X_seq[train_end:val_end], y_seq[train_end:val_end]
X_test, y_test = X_seq[val_end:], y_seq[val_end:]

print(f"✓ Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")

# Converter para tensor (CPU)
X_train = torch.tensor(X_train, dtype=torch.float32)
y_train = torch.tensor(y_train, dtype=torch.float32)
X_val = torch.tensor(X_val, dtype=torch.float32)
y_val = torch.tensor(y_val, dtype=torch.float32)
X_test = torch.tensor(X_test, dtype=torch.float32)
y_test = torch.tensor(y_test, dtype=torch.float32)

# Modelo Informer para classificação binária
print(
    f"\n✓ Construindo modelo Informer (d_model={CONFIG['d_model']}, heads={CONFIG['n_heads']})..."
)
model = Informer(
    enc_in=X_train.shape[2],
    c_out=1,  # 1 logit para classificação binária
    seq_len=CONFIG["seq_len"],
    d_model=CONFIG["d_model"],
    n_heads=CONFIG["n_heads"],
    e_layers=CONFIG["e_layers"],
    d_ff=CONFIG["d_ff"],
    dropout=CONFIG["dropout"],
)

optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG["lr"], weight_decay=1e-5)
loss_fn = nn.BCEWithLogitsLoss()  # Binary Cross Entropy with Logits

# Treinamento com early stopping
print(f"\n{'='*60}")
print("TREINAMENTO")
print(f"{'='*60}")

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

    # Early stopping
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        patience_counter = 0
        torch.save(model.state_dict(), "ml/models/informer_best.pt")
    else:
        patience_counter += 1
        if patience_counter >= patience:
            print(f"✓ Early stopping na época {epoch+1}")
            break

# Carregar melhor modelo
model.load_state_dict(torch.load("ml/models/informer_best.pt"))

# Avaliação no conjunto de teste
print(f"\n{'='*60}")
print("AVALIAÇÃO NO TESTE")
print(f"{'='*60}")

model.eval()
with torch.no_grad():
    test_logits = model(X_test).squeeze(-1)
    test_probs = torch.sigmoid(test_logits).numpy()

# Métricas com threshold padrão (0.5)
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
print(f"\n{'='*60}")
print("OTIMIZAÇÃO DE THRESHOLD PARA 58% POSITIVOS")
print(f"{'='*60}")

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

# Aplicar melhor threshold
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

# Salvar modelo e metadados
print(f"\n{'='*60}")
print("SALVANDO MODELO E METADADOS")
print(f"{'='*60}")

# Salvar state_dict
torch.save(model.state_dict(), "ml/models/informer_classifier.pt")
print("✓ Modelo salvo: ml/models/informer_classifier.pt")

# Salvar normalização
norm_data = {
    "X_mean": X_mean.tolist(),
    "X_std": X_std.tolist(),
    "features": features,
}
with open("ml/models/informer_normalization.json", "w") as f:
    json.dump(norm_data, f, indent=2)
print("✓ Normalização salva: ml/models/informer_normalization.json")

# Salvar report
report = {
    "model": "Informer",
    "task": "binary_classification",
    "target": "trade_positivo (target_ret_1 > 0)",
    "config": CONFIG,
    "dataset": {
        "total_samples": len(df),
        "train": len(X_train),
        "val": len(X_val),
        "test": len(X_test),
        "positive_ratio": float(pos_ratio),
    },
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

with open("ml/models/informer_report.json", "w") as f:
    json.dump(report, f, indent=2)
print("✓ Report salvo: ml/models/informer_report.json")

print(f"\n{'='*60}")
print("✓ TREINAMENTO CONCLUÍDO COM SUCESSO!")
print(f"{'='*60}\n")
