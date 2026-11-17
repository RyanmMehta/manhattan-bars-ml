"""A tiny decoder-only transformer (GPT-style) for characters, written from scratch in PyTorch.

Inputs : token ids (B, T) from data.py
Outputs: logits (B, T, vocab_size) and, if targets are given, the cross-entropy loss
Run    : python -I coursework/tiny_transformer/model.py      (prints the parameter count)

Shape letters used everywhere below (explained once here):
  B = batch size (names per batch), T = time = sequence length, C = channels = n_embd,
  H = head size = n_embd / n_head, V = vocab size.

Pieces, in the order data flows through them:
  token embedding [N4] + position embedding [N5]
  -> n_layer x Block: x + MultiHeadAttention(LayerNorm(x))  [N6][N7][N8][N9]
                      x + FeedForward(LayerNorm(x))         [N8][N9]
  -> final LayerNorm -> Linear to V logits -> cross-entropy loss [N10]
"""
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class Head(nn.Module):
    """[N6] One head of causal self-attention."""

    def __init__(self, n_embd: int, head_size: int, block_size: int, dropout: float):
        super().__init__()
        self.key = nn.Linear(n_embd, head_size, bias=False)
        self.query = nn.Linear(n_embd, head_size, bias=False)
        self.value = nn.Linear(n_embd, head_size, bias=False)
        # [N7] lower-triangular matrix of ones: position t may look at positions 0..t only.
        # register_buffer = saved with the model but not a trainable weight.
        self.register_buffer("mask", torch.tril(torch.ones(block_size, block_size)))
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        k = self.key(x)                                       # (B, T, H) what each token "offers"
        q = self.query(x)                                     # (B, T, H) what each token "looks for"
        v = self.value(x)                                     # (B, T, H) what each token passes on
        scores = q @ k.transpose(-2, -1)                      # (B, T, T) similarity of every pair
        scores = scores / (k.shape[-1] ** 0.5)                # (B, T, T) scale by sqrt(H) so softmax isn't too peaky
        scores = scores.masked_fill(self.mask[:T, :T] == 0, float("-inf"))  # (B, T, T) [N7] hide the future
        weights = F.softmax(scores, dim=-1)                   # (B, T, T) each row sums to 1
        weights = self.dropout(weights)                       # (B, T, T)
        return weights @ v                                    # (B, T, H) weighted average of values


class MultiHeadAttention(nn.Module):
    """[N8] Several heads in parallel; their outputs are concatenated and mixed by a linear layer."""

    def __init__(self, n_embd: int, n_head: int, block_size: int, dropout: float):
        super().__init__()
        head_size = n_embd // n_head
        self.heads = nn.ModuleList([Head(n_embd, head_size, block_size, dropout) for _ in range(n_head)])
        self.proj = nn.Linear(n_embd, n_embd)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = torch.cat([head(x) for head in self.heads], dim=-1)  # (B, T, C) = n_head * H
        return self.dropout(self.proj(out))                         # (B, T, C)


class FeedForward(nn.Module):
    """[N8] A per-position MLP: widen to 4*C, GELU non-linearity, back to C."""

    def __init__(self, n_embd: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_embd, 4 * n_embd),
            nn.GELU(),
            nn.Linear(4 * n_embd, n_embd),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)  # (B, T, C) -> (B, T, C)


class Block(nn.Module):
    """[N9] One transformer block: attention then MLP, each with pre-LayerNorm and a residual add."""

    def __init__(self, n_embd: int, n_head: int, block_size: int, dropout: float):
        super().__init__()
        self.ln1 = nn.LayerNorm(n_embd)
        self.attn = MultiHeadAttention(n_embd, n_head, block_size, dropout)
        self.ln2 = nn.LayerNorm(n_embd)
        self.ffwd = FeedForward(n_embd, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))   # (B, T, C) tokens talk to each other (residual keeps the old x)
        x = x + self.ffwd(self.ln2(x))   # (B, T, C) each token "thinks" on its own
        return x


class TinyGPT(nn.Module):
    """The full model: embeddings -> blocks -> logits."""

    def __init__(self, vocab_size: int, block_size: int = 32, n_embd: int = 64,
                 n_head: int = 4, n_layer: int = 2, dropout: float = 0.1):
        super().__init__()
        self.block_size = block_size
        self.token_emb = nn.Embedding(vocab_size, n_embd)      # [N4] one learned vector per token
        self.pos_emb = nn.Embedding(block_size, n_embd)        # [N5] one learned vector per position
        self.blocks = nn.Sequential(*[Block(n_embd, n_head, block_size, dropout) for _ in range(n_layer)])
        self.ln_f = nn.LayerNorm(n_embd)
        self.lm_head = nn.Linear(n_embd, vocab_size)

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        B, T = idx.shape
        tok = self.token_emb(idx)                               # (B, T, C)
        pos = self.pos_emb(torch.arange(T, device=idx.device))  # (T, C), broadcast over B
        x = tok + pos                                           # (B, T, C) [N5] "what" + "where"
        x = self.blocks(x)                                      # (B, T, C)
        x = self.ln_f(x)                                        # (B, T, C)
        logits = self.lm_head(x)                                # (B, T, V) a score for every next token
        if targets is None:
            return logits, None
        # [N10] cross-entropy = mean of -ln softmax(logits)[true next token]; -100 targets are skipped.
        loss = F.cross_entropy(logits.reshape(B * T, -1), targets.reshape(B * T), ignore_index=-100)
        return logits, loss


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


if __name__ == "__main__":
    model = TinyGPT(vocab_size=43)
    print(f"TinyGPT default config: {count_params(model):,} parameters")
