"""Treinamento simples do Informer com dataset CSV e tuning opcional de CPU."""
import os
import sys
import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import mean_squared_error, precision_score, recall_score
from torch import nn

# Ensure project root is on sys.path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ml.models.informer import Informer

# Optional performance tuning
_fast_read_csv = None
_cpu_count = None
try:
    from ml.utils.perf import cpu_count as _cpu
    from ml.utils.perf import fast_read_csv as _fast
    from ml.utils.perf import tune_environment, tune_torch_threads

    tune_environment()
    tune_torch_threads()
    _fast_read_csv = _fast
    _cpu_count = _cpu
except Exception:
    # perf utils not available; proceed with defaults
    _fast_read_csv = None
    _cpu_count = None

# Carregar dataset
DATA_PATH = "ml/data/training_dataset.csv"
TARGET_COL = "target_ret_1"
if callable(_fast_read_csv):
    try:
        df = _fast_read_csv(DATA_PATH)
    except Exception:
        df = pd.read_csv(DATA_PATH)
else:
    df = pd.read_csv(DATA_PATH)

# Seleciona apenas colunas numéricas exceto o alvo (robusto a pandas dtypes)
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
features = [c for c in numeric_cols if c != TARGET_COL]
X = df[features].values
y = df[TARGET_COL].values

# Normalização simples (z-score)
X_mean = X.mean(axis=0)
X_std = X.std(axis=0) + 1e-8
X = (X - X_mean) / X_std

# Parâmetros Informer
seq_len = 64  # janela maior ajuda seq models
pred_len = 1  # prever 1 passo à frente
if callable(_cpu_count):
    try:
        _cores = _cpu_count()
        batch_size = max(128, _cores * 64)
    except Exception:
        batch_size = 128
else:
    batch_size = 128
try:
    # Allow manual override from environment
    _env_bs = int(os.getenv("BATCH_SIZE", "0"))
    if _env_bs > 0:
        batch_size = _env_bs
except Exception:
    pass


# Preparar dados sequenciais
def create_sequences(X: np.ndarray, y: np.ndarray, seq_len: int, pred_len: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Cria sequências para modelos de séries temporais.
    Args:
        X: array de features
        y: array de targets
        seq_len: tamanho da janela
        pred_len: passos à frente para previsão
    Returns:
        tuple: (Xs, ys) arrays de entrada e saída
    """
    Xs, ys = [], []
    for i in range(len(X) - seq_len - pred_len):
        Xs.append(X[i : i + seq_len])
        ys.append(y[i + seq_len + pred_len - 1])
    return np.array(Xs), np.array(ys)[:, None]


X_seq, y_seq = create_sequences(X, y, seq_len, pred_len)

# Separar treino/teste
split = int(0.8 * len(X_seq))
X_train, X_test = X_seq[:split], X_seq[split:]
y_train, y_test = y_seq[:split], y_seq[split:]

# Converter para tensor
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
X_train = torch.tensor(X_train, dtype=torch.float32).to(device)
y_train = torch.tensor(y_train, dtype=torch.float32).to(device)
X_test = torch.tensor(X_test, dtype=torch.float32).to(device)
y_test = torch.tensor(y_test, dtype=torch.float32).to(device)

"""
Local Informer-like model: maps (B, L, F) -> (B, 1)
"""
model = Informer(
    enc_in=X_train.shape[2],
    c_out=1,
    seq_len=seq_len,
    d_model=128,
    n_heads=4,
    e_layers=2,
    d_ff=256,
    dropout=0.1,
).to(device)

optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.MSELoss()

# Treinamento
epochs = 5
for epoch in range(epochs):
    model.train()
    epoch_loss = 0
    for i in range(0, len(X_train), batch_size):
        xb = X_train[i : i + batch_size]
        yb = y_train[i : i + batch_size]
        optimizer.zero_grad()
        # Forward: (B, L, F) -> (B, 1)
        out = model(xb)
        # yb shape: (B, 1), ensure same shape
        yb_ = yb.squeeze(-1)
        loss = loss_fn(out.squeeze(-1), yb_)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    print(f"Epoch {epoch+1}/{epochs} Loss: {epoch_loss:.4f}")

# Avaliação
model.eval()
with torch.no_grad():
    preds = model(X_test).cpu().numpy().squeeze()
    y_true = y_test.cpu().numpy().squeeze()
    mse = mean_squared_error(y_true, preds)
    print(f"Test MSE: {mse:.4f}")
    # Se for classificação binária, calcule precisão/recall
    if set(np.unique(y_true)) <= {0, 1}:
        precision = precision_score(y_true, preds.round())
        recall = recall_score(y_true, preds.round())
        print(f"Precision: {precision:.4f} Recall: {recall:.4f}")

# Salvar modelo
joblib.dump(model.state_dict(), "ml/models/informer_model.pt")
