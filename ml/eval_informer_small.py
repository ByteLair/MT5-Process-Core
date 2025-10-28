#!/usr/bin/env python3
"""Evaluate and (optionally) train the small transformer on different splits/epochs.

Usage examples:
  python ml/eval_informer_small.py --data ml/dataset_eurusd.npz --val_split 0.2 --epochs 10

This script will:
- load the dataset .npz created by the builder
- split into train/val by `val_split` (random, seed=42)
- train a SmallTransformer for `epochs` on the training split
- evaluate on validation split and save predictions + metrics
"""
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from pathlib import Path


class SmallTransformer(nn.Module):
    def __init__(self, input_dim=5, d_model=64, nhead=4, num_layers=2, pred_len=60):
        super().__init__()
        self.input_fc = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=256, batch_first=True)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.out = nn.Linear(d_model, pred_len)

    def forward(self, x):
        h = self.input_fc(x)
        h = self.encoder(h)
        h_t = h.transpose(1, 2)
        p = self.pool(h_t).squeeze(-1)
        out = self.out(p)
        return out


def train_and_eval(data_path, val_split=0.1, epochs=5, batch_size=64, lr=1e-3, device='cpu', out_prefix='ml/eval_preds'):
    npz = np.load(data_path)
    X = npz['X']
    Y = npz['Y']
    N = X.shape[0]
    print(f'Loaded dataset: X={X.shape}, Y={Y.shape}, N={N}')

    # train/val split
    rng = np.random.RandomState(42)
    idx = rng.permutation(N)
    n_val = max(1, int(round(N * val_split)))
    val_idx = idx[:n_val]
    train_idx = idx[n_val:]
    X_train = X[train_idx]
    Y_train = Y[train_idx]
    X_val = X[val_idx]
    Y_val = Y[val_idx]

    print(f'Train/Val sizes: {X_train.shape[0]}/{X_val.shape[0]} (val_split={val_split})')

    # tensors and loaders
    X_t = torch.from_numpy(X_train).float()
    Y_t = torch.from_numpy(Y_train).float()
    train_ds = TensorDataset(X_t, Y_t)
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)

    Xv_t = torch.from_numpy(X_val).float()
    Yv_t = torch.from_numpy(Y_val).float()
    val_ds = TensorDataset(Xv_t, Yv_t)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    model = SmallTransformer(input_dim=X.shape[2], d_model=64, nhead=4, num_layers=2, pred_len=Y.shape[1])
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.L1Loss()

    for ep in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        nb = 0
        for xb, yb in train_loader:
            xb = xb.to(device)
            yb = yb.to(device)
            pred = model(xb)
            loss = loss_fn(pred, yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item() * xb.size(0)
            nb += xb.size(0)
        avg = total_loss / nb if nb > 0 else 0.0
        print(f'Epoch {ep}/{epochs} — train MAE: {avg:.6f}')

    # eval
    model.eval()
    preds = []
    targets = []
    with torch.no_grad():
        for xb, yb in val_loader:
            xb = xb.to(device)
            out = model(xb).cpu().numpy()
            preds.append(out)
            targets.append(yb.numpy())
    if len(preds) == 0:
        preds_arr = np.zeros((0, Y.shape[1]))
        targets_arr = np.zeros((0, Y.shape[1]))
    else:
        preds_arr = np.concatenate(preds, axis=0)
        targets_arr = np.concatenate(targets, axis=0)

    # metrics: MAE and RMSE across all predicted timesteps and examples
    mae = float(np.mean(np.abs(preds_arr - targets_arr)))
    rmse = float(np.sqrt(np.mean((preds_arr - targets_arr) ** 2)))
    print(f'Validation — examples: {preds_arr.shape[0]}, MAE: {mae:.6f}, RMSE: {rmse:.6f}')

    # save predictions
    out_p = Path(f'{out_prefix}_{epochs}ep_{int(val_split*100)}pct.npz')
    np.savez_compressed(out_p, preds=preds_arr, targets=targets_arr, val_idx=val_idx)
    print(f'Saved predictions to {out_p}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', required=True)
    p.add_argument('--val_split', type=float, default=0.1)
    p.add_argument('--epochs', type=int, default=5)
    p.add_argument('--batch_size', type=int, default=64)
    p.add_argument('--lr', type=float, default=1e-3)
    p.add_argument('--device', default='cpu')
    p.add_argument('--out_prefix', default='ml/eval_preds')
    args = p.parse_args()

    train_and_eval(args.data, val_split=args.val_split, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, device=args.device, out_prefix=args.out_prefix)


if __name__ == '__main__':
    main()
