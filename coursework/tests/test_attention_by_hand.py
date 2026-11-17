"""[N6] The numpy hand-worked example must equal model.Head with the same weights."""
import numpy as np
import torch

from coursework.tiny_transformer.attention_by_hand import W_K, W_Q, W_V, X, attention_by_hand
from coursework.tiny_transformer.model import Head


def test_hand_example_matches_head():
    head = Head(n_embd=2, head_size=2, block_size=3, dropout=0.0)
    with torch.no_grad():  # nn.Linear computes x @ W.T, so we load the transposes
        head.query.weight.copy_(torch.tensor(W_Q.T))
        head.key.weight.copy_(torch.tensor(W_K.T))
        head.value.weight.copy_(torch.tensor(W_V.T))
        out = head(torch.tensor(X, dtype=torch.float64).float().unsqueeze(0))[0].numpy()
    assert np.abs(out - attention_by_hand()["out"]).max() < 1e-6


def test_hand_weights_rows_sum_to_one_and_mask_future():
    w = attention_by_hand()["weights"]
    assert np.allclose(w.sum(axis=1), 1.0)
    assert w[0, 1] == 0 and w[0, 2] == 0 and w[1, 2] == 0
