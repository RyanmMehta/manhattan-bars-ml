"""Unigram and bigram character models: the bars the transformer must beat.

Inputs : train / val name lists from data.py
Outputs: val loss in nats per character (returned; train.py stores them in metrics.json)
Run    : python -I coursework/tiny_transformer/baselines.py

[N3] "Loss in nats per character" = average of -ln P(true next char). Lower is better.
A model that guesses uniformly over V tokens scores ln(V) (about 3.76 for V=43).
Both baselines are scored on exactly the same targets as the transformer:
every character of the name plus the final <e>, i.e. len(name)+1 predictions per name.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.tiny_transformer.data import Tokenizer, clean_all, load_names, split_names  # noqa: E402


def sequences(names: list[str], tok: Tokenizer) -> list[list[int]]:
    """<s> name <e> as ids, for every name."""
    return [[tok.start_id] + tok.encode(n) + [tok.end_id] for n in names]


def unigram_loss(train: list[str], val: list[str], tok: Tokenizer) -> float:
    """[N3] P(next char) = how often that char appears in train (ignores all context). Add-1 smoothing."""
    counts = np.ones(tok.vocab_size)  # add-1 smoothing: every token gets a count of 1 to start
    for seq in sequences(train, tok):
        for target in seq[1:]:
            counts[target] += 1
    probs = counts / counts.sum()
    losses = [-math.log(probs[t]) for seq in sequences(val, tok) for t in seq[1:]]
    return float(np.mean(losses))


def bigram_loss(train: list[str], val: list[str], tok: Tokenizer) -> float:
    """[N3] P(next | previous char) from a count table (V x V), add-1 smoothed."""
    counts = np.ones((tok.vocab_size, tok.vocab_size))  # counts[prev, next]
    for seq in sequences(train, tok):
        for prev, nxt in zip(seq[:-1], seq[1:]):
            counts[prev, nxt] += 1
    probs = counts / counts.sum(axis=1, keepdims=True)  # each row sums to 1
    losses = [-math.log(probs[p, n]) for seq in sequences(val, tok) for p, n in zip(seq[:-1], seq[1:])]
    return float(np.mean(losses))


if __name__ == "__main__":
    names = clean_all(load_names())
    train, val = split_names(names, seed=0)
    tok = Tokenizer(train + val)
    print(f"uniform : {math.log(tok.vocab_size):.4f} nats/char")
    print(f"unigram : {unigram_loss(train, val, tok):.4f} nats/char")
    print(f"bigram  : {bigram_loss(train, val, tok):.4f} nats/char")
