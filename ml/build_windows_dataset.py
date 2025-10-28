#!/usr/bin/env python3
"""Build sliding-window dataset for time series training.

Output: npz file with X (num_examples, seq_len, n_features) and
Y (num_examples, pred_len) (predicting closing prices).

Usage: python ml/build_windows_dataset.py --parquet exports/eurusd_m1.parquet \
       --scalers exports/eurusd_m1_scalers.json --out ml/dataset_eurusd.npz
"""
import argparse
import json
import numpy as np
import pandas as pd
from pathlib import Path


def load_data(parquet_path):
    df = pd.read_parquet(parquet_path)
    # ensure ts sorted
    df = df.sort_values("ts").reset_index(drop=True)
    return df


def normalize(df, scalers):
    df2 = df.copy()
    for c, s in scalers.items():
        if s.get("mean") is None:
            continue
        mean = s["mean"]
        std = s["std"] if s["std"] and s["std"] > 0 else 1.0
        df2[c] = (df2[c] - mean) / std
    return df2


def build_windows(df, seq_len=480, pred_len=60, step=60, feature_cols=None):
    # df expected to have columns including feature_cols and 'close'
    Xs = []
    Ys = []
    n = len(df)
    last_start = n - seq_len - pred_len
    if last_start < 0:
        return np.empty((0, seq_len, len(feature_cols))), np.empty((0, pred_len))
    for start in range(0, last_start + 1, step):
        end = start + seq_len
        x = df.iloc[start:end][feature_cols].to_numpy(dtype=np.float32)
        y = df.iloc[end:end+pred_len]["close"].to_numpy(dtype=np.float32)
        if y.shape[0] != pred_len:
            break
        Xs.append(x)
        Ys.append(y)
    return np.stack(Xs), np.stack(Ys)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--parquet", required=True)
    p.add_argument("--scalers", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--seq_len", type=int, default=480)
    p.add_argument("--pred_len", type=int, default=60)
    p.add_argument("--step", type=int, default=60)
    args = p.parse_args()

    parquet = Path(args.parquet)
    scalers_path = Path(args.scalers)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    df = load_data(parquet)
    with open(scalers_path, "r") as f:
        meta = json.load(f)
    scalers = meta.get("scalers", {})

    # feature columns to use
    feature_cols = ["open", "high", "low", "close", "volume"]
    df_norm = normalize(df, scalers)

    X, Y = build_windows(df_norm, seq_len=args.seq_len, pred_len=args.pred_len, step=args.step, feature_cols=feature_cols)

    print(f"Built dataset: X={X.shape}, Y={Y.shape}")
    np.savez_compressed(out_path, X=X, Y=Y, ts_start=df['ts'].astype(str).values[:1])
    print(f"Saved dataset to {out_path}")


if __name__ == '__main__':
    main()
