import jsonimport json

import osimport os

import sysimport sys



import numpy as npimport numpy as np

import pandas as pdimport pandas as pd

import torchimport torch

from sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_scorefrom sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_score

from torch import nnimport json

import os

# Ensure project root is on sys.pathimport sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

_PROJECT_ROOT = os.path.dirname(_THIS_DIR)import numpy as np

if _PROJECT_ROOT not in sys.path:import pandas as pd

    sys.path.insert(0, _PROJECT_ROOT)import torch

from sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_score

from ml.models.informer import Informerfrom torch import nn



_fast_read_csv = None# Ensure project root is on sys.path

try:_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    from ml.utils.perf import fast_read_csv as _fast_PROJECT_ROOT = os.path.dirname(_THIS_DIR)

    from ml.utils.perf import tune_environment, tune_torch_threadsif _PROJECT_ROOT not in sys.path:

    sys.path.insert(0, _PROJECT_ROOT)

    tune_environment()

    tune_torch_threads()from ml.models.informer import Informer

    _fast_read_csv = _fast

except Exception:_fast_read_csv = None

    _fast_read_csv = Nonetry:

    from ml.utils.perf import fast_read_csv as _fast

# Configurações otimizadas para CPU    from ml.utils.perf import tune_environment, tune_torch_threads

CONFIG = {

    "seq_len": 32,    tune_environment()

    "d_model": 64,    tune_torch_threads()

    "n_heads": 4,    _fast_read_csv = _fast

    "e_layers": 2,except Exception:

    "d_ff": 128,    _fast_read_csv = None

    "dropout": 0.2,

    "batch_size": 64,print("=" * 60)

    "epochs": 10,print("INFORMER - CLASSIFICAÇÃO BINÁRIA DE TRADES POSITIVOS")

    "lr": 5e-4,print("=" * 60)

}

# Force CPU usage (otimizado para servidor sem GPU)

DATA_PATH = "ml/data/training_dataset.csv"device = torch.device("cpu")

TARGET_COL = "target_ret_1"print(f"✓ Dispositivo: {device}")



# Configurações otimizadas para CPU

def _prepare_from_csv(path: str):CONFIG = {

    """Helper to load dataset and return (df, X, y, X_mean, X_std, features, pos_ratio)"""    "seq_len": 32,  # Reduzido para CPU

    if callable(_fast_read_csv):    "d_model": 64,  # Modelo menor para CPU

        try:    "n_heads": 4,

            df = _fast_read_csv(path)    "e_layers": 2,

        except Exception:    "d_ff": 128,  # FFN menor para CPU

            df = pd.read_csv(path)    "dropout": 0.2,

    else:    "batch_size": 64,  # Batch menor para CPU

        df = pd.read_csv(path)    "epochs": 10,

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()    "lr": 5e-4,

    features = [c for c in numeric_cols if c != TARGET_COL]}

    X = df[features].to_numpy()

    y_continuous = df[TARGET_COL].to_numpy(dtype=np.float32)

    y = (y_continuous > 0).astype(np.float32)# Dataset constants (loading moved to main)

    pos_ratio = y.mean()DATA_PATH = "ml/data/training_dataset.csv"

    X_mean = X.mean(axis=0)TARGET_COL = "target_ret_1"

    X_std = X.std(axis=0) + 1e-8

    X = (X - X_mean) / X_std

    return df, X, y, X_mean, X_std, features, pos_ratiodef _prepare_from_csv(path: str):

    """Helper to load dataset and return (df, X, y, X_mean, X_std, features, pos_ratio)

    This keeps module import-safe for tests that construct their own DataFrames."""

def create_sequences(x: np.ndarray, y: np.ndarray, seq_len: int) -> tuple[np.ndarray, np.ndarray]:    if callable(_fast_read_csv):

    """Cria sequências para modelos de séries temporais."""        try:

    xs, ys = [], []            df = _fast_read_csv(path)

    for i in range(len(x) - seq_len):        except Exception:

        xs.append(x[i : i + seq_len])            df = pd.read_csv(path)

        ys.append(y[i + seq_len])    else:

    return np.array(xs), np.array(ys)        df = pd.read_csv(path)

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    features = [c for c in numeric_cols if c != TARGET_COL]

def main():    X = df[features].to_numpy()

    print("=" * 60)    y_continuous = df[TARGET_COL].to_numpy(dtype=np.float32)

    print("INFORMER - CLASSIFICAÇÃO BINÁRIA DE TRADES POSITIVOS")    y = (y_continuous > 0).astype(np.float32)

    print("=" * 60)    pos_ratio = y.mean()

    device = torch.device("cpu")    # Normalização simples (z-score)

    print(f"✓ Dispositivo: {device}")    X_mean = X.mean(axis=0)

        X_std = X.std(axis=0) + 1e-8

    df, X, y, X_mean, X_std, features, pos_ratio = _prepare_from_csv(DATA_PATH)    X = (X - X_mean) / X_std

    print(f"✓ Dataset carregado: {len(df)} registros")    return df, X, y, X_mean, X_std, features, pos_ratio

    print(f"✓ Features: {len(features)} colunas")

    print(f"✓ Classes: {y.sum():.0f} positivos ({pos_ratio*100:.1f}%), {(1-y).sum():.0f} negativos ({(1-pos_ratio)*100:.1f}%)")

# Preparar dados sequenciais

    X_seq, y_seq = create_sequences(X, y, CONFIG["seq_len"])def create_sequences(x: np.ndarray, y: np.ndarray, seq_len: int) -> tuple[np.ndarray, np.ndarray]:

    n = len(X_seq)    """

    train_end = int(0.6 * n)    Cria sequências para modelos de séries temporais.

    val_end = int(0.8 * n)    Args:

    X_train, y_train = X_seq[:train_end], y_seq[:train_end]        x: array de features

    X_val, y_val = X_seq[train_end:val_end], y_seq[train_end:val_end]        y: array de targets

    X_test, y_test = X_seq[val_end:], y_seq[val_end:]        seq_len: tamanho da janela

    print(f"✓ Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")    Returns:

        tuple: (xs, ys) arrays de entrada e saída

    X_train = torch.tensor(X_train, dtype=torch.float32)    """

    y_train = torch.tensor(y_train, dtype=torch.float32)    xs, ys = [], []

    X_val = torch.tensor(X_val, dtype=torch.float32)    for i in range(len(x) - seq_len):

    y_val = torch.tensor(y_val, dtype=torch.float32)        xs.append(x[i : i + seq_len])

    X_test = torch.tensor(X_test, dtype=torch.float32)        ys.append(y[i + seq_len])

    y_test = torch.tensor(y_test, dtype=torch.float32)    return np.array(xs), np.array(ys)



    print(f"\n✓ Construindo modelo Informer (d_model={CONFIG['d_model']}, heads={CONFIG['n_heads']})...")

    model = Informer(def main():

        enc_in=X_train.shape[2],    print("✓ Criando sequências e iniciando fluxo de treinamento a partir do CSV...")

        c_out=1,    # Prepare data from CSV

        seq_len=CONFIG["seq_len"],    df, X, y, X_mean, X_std, features, pos_ratio = _prepare_from_csv(DATA_PATH)

        d_model=CONFIG["d_model"],    print(f"✓ Dataset carregado: {len(df)} registros")

        n_heads=CONFIG["n_heads"],    print(f"✓ Features: {len(features)} colunas")

        e_layers=CONFIG["e_layers"],    print(

        d_ff=CONFIG["d_ff"],        f"✓ Classes: {y.sum():.0f} positivos ({pos_ratio*100:.1f}%), {(1-y).sum():.0f} negativos ({(1-pos_ratio)*100:.1f}%)"

        dropout=CONFIG["dropout"],    )

    )

    X_seq, y_seq = create_sequences(X, y, CONFIG["seq_len"])

    optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG["lr"], weight_decay=1e-5)

    loss_fn = nn.BCEWithLogitsLoss()    # Separar treino/validação/teste (60/20/20)

    n = len(X_seq)

    print(f"\n{'='*60}")    train_end = int(0.6 * n)

    print("TREINAMENTO")    val_end = int(0.8 * n)

    print(f"{'='*60}")    X_train, y_train = X_seq[:train_end], y_seq[:train_end]

    X_val, y_val = X_seq[train_end:val_end], y_seq[train_end:val_end]

    best_val_loss = float("inf")    X_test, y_test = X_seq[val_end:], y_seq[val_end:]

    patience = 3

    patience_counter = 0    print(f"✓ Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")



    for epoch in range(CONFIG["epochs"]):    # Converter para tensor (CPU)

        model.train()    X_train = torch.tensor(X_train, dtype=torch.float32)

        train_loss = 0    y_train = torch.tensor(y_train, dtype=torch.float32)

        for i in range(0, len(X_train), CONFIG["batch_size"]):    X_val = torch.tensor(X_val, dtype=torch.float32)

            xb = X_train[i : i + CONFIG["batch_size"]]    y_val = torch.tensor(y_val, dtype=torch.float32)

            yb = y_train[i : i + CONFIG["batch_size"]]    X_test = torch.tensor(X_test, dtype=torch.float32)

            optimizer.zero_grad()    y_test = torch.tensor(y_test, dtype=torch.float32)

            logits = model(xb).squeeze(-1)

            loss = loss_fn(logits, yb)    # Modelo Informer para classificação binária

            loss.backward()    print(

            optimizer.step()        f"\n✓ Construindo modelo Informer (d_model={CONFIG['d_model']}, heads={CONFIG['n_heads']})..."

            train_loss += loss.item()    )

    model = Informer(

        model.eval()        enc_in=X_train.shape[2],

        with torch.no_grad():        c_out=1,  # 1 logit para classificação binária

            val_logits = model(X_val).squeeze(-1)        seq_len=CONFIG["seq_len"],

            val_loss = loss_fn(val_logits, y_val).item()        d_model=CONFIG["d_model"],

            val_probs = torch.sigmoid(val_logits).numpy()        n_heads=CONFIG["n_heads"],

            val_preds = (val_probs > 0.5).astype(int)        e_layers=CONFIG["e_layers"],

            val_precision = precision_score(y_val.numpy(), val_preds, zero_division=0)        d_ff=CONFIG["d_ff"],

            val_recall = recall_score(y_val.numpy(), val_preds, zero_division=0)        dropout=CONFIG["dropout"],

    )

        print(f"Epoch {epoch+1}/{CONFIG['epochs']} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Prec: {val_precision:.3f} | Rec: {val_recall:.3f}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG["lr"], weight_decay=1e-5)

        if val_loss < best_val_loss:    loss_fn = nn.BCEWithLogitsLoss()  # Binary Cross Entropy with Logits

            best_val_loss = val_loss

            patience_counter = 0    # Treinamento com early stopping

            torch.save(model.state_dict(), "ml/models/informer_best.pt")    print(f"\n{'='*60}")

        else:    print("TREINAMENTO")

            patience_counter += 1    print(f"{'='*60}")

            if patience_counter >= patience:

                print(f"✓ Early stopping na época {epoch+1}")    best_val_loss = float("inf")

                break    patience = 3

    patience_counter = 0

    model.load_state_dict(torch.load("ml/models/informer_best.pt"))

    for epoch in range(CONFIG["epochs"]):

    print(f"\n{'='*60}")        model.train()

    print("AVALIAÇÃO NO TESTE")        train_loss = 0

    print(f"{'='*60}")

        for i in range(0, len(X_train), CONFIG["batch_size"]):

    model.eval()            xb = X_train[i : i + CONFIG["batch_size"]]

    with torch.no_grad():            yb = y_train[i : i + CONFIG["batch_size"]]

        test_logits = model(X_test).squeeze(-1)

        test_probs = torch.sigmoid(test_logits).numpy()            optimizer.zero_grad()

            logits = model(xb).squeeze(-1)

    test_preds_05 = (test_probs > 0.5).astype(int)            loss = loss_fn(logits, yb)

    y_test_np = y_test.numpy()            loss.backward()

    precision_05 = precision_score(y_test_np, test_preds_05, zero_division=0)            optimizer.step()

    recall_05 = recall_score(y_test_np, test_preds_05, zero_division=0)            train_loss += loss.item()

    auc = roc_auc_score(y_test_np, test_probs)

    cm = confusion_matrix(y_test_np, test_preds_05)        # Validação

        model.eval()

    print("\nThreshold 0.5:")        with torch.no_grad():

    print(f"  Precision: {precision_05:.4f}")            val_logits = model(X_val).squeeze(-1)

    print(f"  Recall: {recall_05:.4f}")            val_loss = loss_fn(val_logits, y_val).item()

    print(f"  AUC-ROC: {auc:.4f}")            val_probs = torch.sigmoid(val_logits).numpy()

    print(f"  Positivos previstos: {test_preds_05.sum()} ({test_preds_05.mean()*100:.1f}%)")            val_preds = (val_probs > 0.5).astype(int)

    print(f"  Confusion Matrix:\n{cm}")            val_precision = precision_score(y_val.numpy(), val_preds, zero_division=0)

            val_recall = recall_score(y_val.numpy(), val_preds, zero_division=0)

    print(f"\n{'='*60}")

    print("OTIMIZAÇÃO DE THRESHOLD PARA 58% POSITIVOS")        print(

    print(f"{'='*60}")            f"Epoch {epoch+1}/{CONFIG['epochs']} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | Prec: {val_precision:.3f} | Rec: {val_recall:.3f}"

        )

    target_positive_rate = 0.58

    best_threshold = 0.5        # Early stopping

    best_diff = abs(test_preds_05.mean() - target_positive_rate)        if val_loss < best_val_loss:

            best_val_loss = val_loss

    for thresh in np.arange(0.1, 0.9, 0.01):            patience_counter = 0

        preds = (test_probs > thresh).astype(int)            torch.save(model.state_dict(), "ml/models/informer_best.pt")

        positive_rate = preds.mean()        else:

        diff = abs(positive_rate - target_positive_rate)            patience_counter += 1

        if diff < best_diff:            if patience_counter >= patience:

            best_diff = diff                print(f"✓ Early stopping na época {epoch+1}")

            best_threshold = thresh                break



    test_preds_optimized = (test_probs > best_threshold).astype(int)    # Carregar melhor modelo

    precision_opt = precision_score(y_test_np, test_preds_optimized, zero_division=0)    model.load_state_dict(torch.load("ml/models/informer_best.pt"))

    recall_opt = recall_score(y_test_np, test_preds_optimized, zero_division=0)

    cm_opt = confusion_matrix(y_test_np, test_preds_optimized)    # Avaliação no conjunto de teste

    print(f"\n{'='*60}")

    print(f"\nThreshold otimizado: {best_threshold:.3f}")    print("AVALIAÇÃO NO TESTE")

    print(f"  Precision: {precision_opt:.4f}")    print(f"{'='*60}")

    print(f"  Recall: {recall_opt:.4f}")

    print(f"  Positivos previstos: {test_preds_optimized.sum()} ({test_preds_optimized.mean()*100:.1f}%)")    model.eval()

    print(f"  Confusion Matrix:\n{cm_opt}")    with torch.no_grad():

        test_logits = model(X_test).squeeze(-1)

    print(f"\n{'='*60}")        test_probs = torch.sigmoid(test_logits).numpy()

    print("SALVANDO MODELO E METADADOS")

    print(f"{'='*60}")    # Métricas com threshold padrão (0.5)

    test_preds_05 = (test_probs > 0.5).astype(int)

    torch.save(model.state_dict(), "ml/models/informer_classifier.pt")    y_test_np = y_test.numpy()

    print("✓ Modelo salvo: ml/models/informer_classifier.pt")

    precision_05 = precision_score(y_test_np, test_preds_05, zero_division=0)

    norm_data = {    recall_05 = recall_score(y_test_np, test_preds_05, zero_division=0)

        "X_mean": X_mean.tolist(),    auc = roc_auc_score(y_test_np, test_probs)

        "X_std": X_std.tolist(),    cm = confusion_matrix(y_test_np, test_preds_05)

        "features": features,

    }    print("\nThreshold 0.5:")

    with open("ml/models/informer_normalization.json", "w") as f:    print(f"  Precision: {precision_05:.4f}")

        json.dump(norm_data, f, indent=2)    print(f"  Recall: {recall_05:.4f}")

    print("✓ Normalização salva: ml/models/informer_normalization.json")    print(f"  AUC-ROC: {auc:.4f}")

    print(f"  Positivos previstos: {test_preds_05.sum()} ({test_preds_05.mean()*100:.1f}%)")

    report = {    print(f"  Confusion Matrix:\n{cm}")

        "model": "Informer",

        "task": "binary_classification",    # Otimização de threshold para atingir ~58% de positivos previstos

        "target": "trade_positivo (target_ret_1 > 0)",    print(f"\n{'='*60}")

        "config": CONFIG,    print("OTIMIZAÇÃO DE THRESHOLD PARA 58% POSITIVOS")

        "dataset": {    print(f"{'='*60}")

            "total_samples": len(df),

            "train": len(X_train),    target_positive_rate = 0.58

            "val": len(X_val),    best_threshold = 0.5

            "test": len(X_test),    best_diff = abs(test_preds_05.mean() - target_positive_rate)

            "positive_ratio": float(pos_ratio),

        },    for thresh in np.arange(0.1, 0.9, 0.01):

        "metrics": {        preds = (test_probs > thresh).astype(int)

            "threshold_0.5": {        positive_rate = preds.mean()

                "precision": float(precision_05),        diff = abs(positive_rate - target_positive_rate)

                "recall": float(recall_05),

                "auc_roc": float(auc),        if diff < best_diff:

                "positive_predictions_pct": float(test_preds_05.mean() * 100),            best_diff = diff

            },            best_threshold = thresh

            "threshold_optimized": {

                "threshold": float(best_threshold),    # Aplicar melhor threshold

                "precision": float(precision_opt),    test_preds_optimized = (test_probs > best_threshold).astype(int)

                "recall": float(recall_opt),    precision_opt = precision_score(y_test_np, test_preds_optimized, zero_division=0)

                "positive_predictions_pct": float(test_preds_optimized.mean() * 100),    recall_opt = recall_score(y_test_np, test_preds_optimized, zero_division=0)

            },    cm_opt = confusion_matrix(y_test_np, test_preds_optimized)

        },

    }    print(f"\nThreshold otimizado: {best_threshold:.3f}")

    print(f"  Precision: {precision_opt:.4f}")

    with open("ml/models/informer_report.json", "w") as f:    print(f"  Recall: {recall_opt:.4f}")

        json.dump(report, f, indent=2)    print(

    print("✓ Report salvo: ml/models/informer_report.json")        f"  Positivos previstos: {test_preds_optimized.sum()} ({test_preds_optimized.mean()*100:.1f}%)"

    print(f"\n{'='*60}")    )

    print("✓ TREINAMENTO CONCLUÍDO COM SUCESSO!")    print(f"  Confusion Matrix:\n{cm_opt}")

    print(f"{'='*60}\n")

    # Salvar modelo e metadados

    print(f"\n{'='*60}")

if __name__ == "__main__":    print("SALVANDO MODELO E METADADOS")

    main()    print(f"{'='*60}")


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


if __name__ == "__main__":
    main()
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


if __name__ == "__main__":
    main()
