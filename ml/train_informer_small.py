#!/usr/bin/env python3
"""Train a small Transformer-based model (informer-like) on the prepared dataset.

This is a minimal, CPU-friendly training script that loads a .npz dataset
created by build_windows_dataset.py and trains a small model to predict
the next pred_len 'close' values from seq_len windows.

Usage: python ml/train_informer_small.py --data ml/dataset_eurusd.npz --epochs 5
"""
import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader


class SmallTransformer(nn.Module):
    def __init__(self, input_dim=5, d_model=64, nhead=4, num_layers=2, pred_len=60):
        super().__init__()
        self.input_fc = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, dim_feedforward=256, batch_first=True)
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        # pooling + decoding
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.out = nn.Linear(d_model, pred_len)

    def forward(self, x):
        # x: (B, seq_len, input_dim)
        h = self.input_fc(x)  # (B, seq_len, d_model)
        h = self.encoder(h)   # (B, seq_len, d_model)
        # transpose to (B, d_model, seq_len) for pooling
        h_t = h.transpose(1, 2)
        p = self.pool(h_t).squeeze(-1)  # (B, d_model)
        out = self.out(p)  # (B, pred_len)
        return out


def train(data_path, epochs=5, batch_size=64, lr=1e-3, device='cpu'):
    npz = np.load(data_path)
    X = npz['X']  # (N, seq_len, features)
    Y = npz['Y']  # (N, pred_len)
    print('Loaded', X.shape, Y.shape)

    X_t = torch.from_numpy(X).float()
    Y_t = torch.from_numpy(Y).float()

    dataset = TensorDataset(X_t, Y_t)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = SmallTransformer(input_dim=X.shape[2], d_model=64, nhead=4, num_layers=2, pred_len=Y.shape[1])
    model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.L1Loss()

    for ep in range(1, epochs+1):
        model.train()
        total_loss = 0.0
        nb = 0
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            pred = model(xb)
            loss = loss_fn(pred, yb)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item() * xb.size(0)
            nb += xb.size(0)
        avg = total_loss / nb
        print(f'Epoch {ep}/{epochs} — train MAE: {avg:.6f}')

    # save checkpoint
    torch.save({'model_state': model.state_dict(),'config': {'input_dim': X.shape[2], 'pred_len': Y.shape[1]}}, 'ml/informer_small_ckpt.pth')
    print('Saved checkpoint ml/informer_small_ckpt.pth')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', required=True)
    p.add_argument('--epochs', type=int, default=5)
    p.add_argument('--batch_size', type=int, default=64)
    p.add_argument('--lr', type=float, default=1e-3)
    args = p.parse_args()

    train(args.data, epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)


if __name__ == '__main__':
    main()
