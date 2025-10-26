import torch
from torch import nn


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2) * (-torch.log(torch.tensor(10000.0)) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, L, D)
        L = x.size(1)
        return x + self.pe[:, :L]


class Informer(nn.Module):
    """
    Minimal Informer-like model using TransformerEncoder backbone.
    This is not the full Informer with ProbSparse attention, but a pragmatic
    drop-in for sequence-to-one forecasting/classification.
    """

    def __init__(
        self,
        enc_in: int,
        c_out: int,
        seq_len: int,
        d_model: int = 128,
        n_heads: int = 4,
        e_layers: int = 2,
        d_ff: int = 256,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.seq_len = seq_len
        self.input_proj = nn.Linear(enc_in, d_model)
        self.pos_encoding = PositionalEncoding(d_model, max_len=seq_len + 512)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_ff,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=e_layers)

        # Pooling over the sequence dimension (mean pooling)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.head = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_ff, c_out),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: (B, L, F)
        returns: (B, c_out)
        """
        h = self.input_proj(x)
        h = self.pos_encoding(h)
        h = self.encoder(h)  # (B, L, D)
        # mean pool over L
        h = h.transpose(1, 2)  # (B, D, L)
        h = self.pool(h).squeeze(-1)  # (B, D)
        out = self.head(h)  # (B, c_out)
        return out
