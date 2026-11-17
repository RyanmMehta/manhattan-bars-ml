"""[N6] One causal attention head worked by hand in numpy: 3 tokens, d = 2.

Run: python -I coursework/tiny_transformer/attention_by_hand.py
The same numbers appear in NOTES.md [N6], and tests/test_attention_by_hand.py checks that
model.Head gives exactly the same output when it is given these weights.
"""
import numpy as np

# Three token vectors (rows), each of size d = 2. Think "token 0, token 1, token 2".
X = np.array([[1.0, 0.0],
              [0.0, 1.0],
              [1.0, 1.0]])
# Weight matrices (d x d). Chosen to be simple so the arithmetic can be done on paper.
W_Q = np.array([[1.0, 0.0], [0.0, 1.0]])    # identity: q = x
W_K = np.array([[1.0, 0.0], [0.0, 2.0]])    # doubles the 2nd coordinate
W_V = np.array([[0.0, 1.0], [1.0, 0.0]])    # swaps the two coordinates


def softmax_rows(m: np.ndarray) -> np.ndarray:
    m = m - m.max(axis=1, keepdims=True)    # subtract the row max: same result, no overflow
    e = np.exp(m)
    return e / e.sum(axis=1, keepdims=True)


def attention_by_hand(x: np.ndarray = X) -> dict:
    """Return every intermediate so NOTES.md can show them step by step."""
    q, k, v = x @ W_Q, x @ W_K, x @ W_V              # (3, 2) each
    scores = q @ k.T / np.sqrt(k.shape[1])            # (3, 3) scaled dot products
    mask = np.tril(np.ones((3, 3)))                   # [N7] 1 = allowed, 0 = future
    masked = np.where(mask == 1, scores, -np.inf)     # future positions get -inf -> weight 0
    weights = softmax_rows(masked)                    # (3, 3) rows sum to 1
    out = weights @ v                                 # (3, 2)
    return {"q": q, "k": k, "v": v, "scores": scores, "masked": masked, "weights": weights, "out": out}


if __name__ == "__main__":
    np.set_printoptions(precision=4, suppress=True)
    for name, value in attention_by_hand().items():
        print(f"{name} =\n{value}\n")
