"""Load, clean and split Manhattan venue names; build a character tokenizer.

Inputs : data/manhattan_bars.db, table venues, column name (real public SLA licence data, read-only).
Outputs: Python lists / tensors used by train.py, sample.py and baselines.py (nothing written to disk).
Run    : python -I coursework/tiny_transformer/data.py      (prints corpus stats)

Steps
  1. load_names()   -> SELECT DISTINCT name FROM venues               [N1]
  2. clean_name()   -> upper-case, strip LLC/INC/..., keep simple chars [N2]
  3. split_names()  -> 90/10 train/val split BY NAME, seeded           [N2]
  4. Tokenizer      -> one integer per character + <s> and <e>         [N4]
  5. make_examples()-> fixed-length (input, target) pairs for training [N4]
"""
import re
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # so "coursework" imports under python -I
from coursework.common import VENUE_DB, connect_read_only  # noqa: E402

START, END = "<s>", "<e>"  # special tokens: start of a name, end of a name (also used as padding)

# [N2] Legal noise to remove. "D/B/A ..." means "doing business as" and everything after it goes.
LEGAL_SUFFIX = re.compile(r"\b(LLC|L\.L\.C\.|INC|CORP|CO\.|LTD)\b\.?|#\s*\d+|D/B/A.*$")
NOT_ALLOWED = re.compile(r"[^A-Z0-9 &'\-.]")  # anything outside this small alphabet is dropped


def load_names(db_path: Path = VENUE_DB) -> list[str]:
    """[N1] Read every distinct venue name from the real venue DB (read-only)."""
    with connect_read_only(db_path) as conn:
        rows = conn.execute("SELECT DISTINCT name FROM venues WHERE name IS NOT NULL").fetchall()
    return [row[0] for row in rows]


def clean_name(raw: str) -> str:
    """[N2] Normalise one name: upper case, drop legal suffixes and odd characters."""
    name = raw.upper()
    name = name.split(";")[0]               # "LUMA HOTEL; APERIBAR" -> keep the first part
    name = LEGAL_SUFFIX.sub(" ", name)
    name = name.replace(",", " ")
    name = NOT_ALLOWED.sub("", name)
    name = re.sub(r"\s+", " ", name).strip(" .-&")  # collapse spaces, trim stray punctuation
    return name


def clean_all(raw_names: list[str], min_len: int = 3, max_len: int = 30) -> list[str]:
    """[N2] Clean every name, drop too short / too long ones, dedupe, sort (sorting = repeatable)."""
    cleaned = {clean_name(n) for n in raw_names}
    return sorted(n for n in cleaned if min_len <= len(n) <= max_len)


def split_names(names: list[str], val_frac: float = 0.1, seed: int = 0) -> tuple[list, list]:
    """[N2] Shuffle names with a fixed seed and hold out val_frac of them.

    We split by NAME, not by character: otherwise half of a name could be in train and the
    other half in val, and the val loss would look better than it really is.
    """
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(names))
    n_val = int(round(len(names) * val_frac))
    val = [names[i] for i in order[:n_val]]
    train = [names[i] for i in order[n_val:]]
    return train, val


class Tokenizer:
    """[N4] Character-level tokenizer: each distinct character gets an integer id."""

    def __init__(self, names: list[str]):
        chars = sorted(set("".join(names)))
        self.itos = [START, END] + chars              # id -> token; <s>=0, <e>=1
        self.stoi = {tok: i for i, tok in enumerate(self.itos)}  # token -> id
        self.start_id, self.end_id = 0, 1

    @property
    def vocab_size(self) -> int:
        return len(self.itos)

    def encode(self, text: str) -> list[int]:
        return [self.stoi[ch] for ch in text]

    def decode(self, ids: list[int]) -> str:
        # special tokens are not printed
        return "".join(self.itos[i] for i in ids if i not in (self.start_id, self.end_id))


def make_examples(names: list[str], tok: Tokenizer, block_size: int) -> tuple[torch.Tensor, ...]:
    """[N4] Turn names into (x, y) training pairs of length block_size.

    Sequence = <s> NAME <e> <e> <e> ... (padded with <e>).
    x = sequence[:-1], y = sequence[1:]  -> at every position the target is the NEXT character.
    Targets after the first <e> are set to -100, which cross_entropy ignores ([N10]):
    we want the model to learn to END a name, but not to waste effort predicting padding.
    """
    xs, ys = [], []
    for name in names:
        ids = [tok.start_id] + tok.encode(name) + [tok.end_id]
        ids = ids[: block_size + 1]                               # truncate (names are <= 30 chars)
        ids = ids + [tok.end_id] * (block_size + 1 - len(ids))    # pad with <e>
        x, y = ids[:-1], ids[1:]
        first_end = y.index(tok.end_id) if tok.end_id in y else len(y)
        y = y[: first_end + 1] + [-100] * (len(y) - first_end - 1)  # ignore padding targets
        xs.append(x)
        ys.append(y)
    return torch.tensor(xs), torch.tensor(ys)  # both (N, block_size)


if __name__ == "__main__":
    raw = load_names()
    names = clean_all(raw)
    train, val = split_names(names)
    tok = Tokenizer(train + val)
    print(f"raw distinct names: {len(raw)}  cleaned: {len(names)}  train: {len(train)}  val: {len(val)}")
    print(f"vocab size: {tok.vocab_size}  mean length: {np.mean([len(n) for n in names]):.1f}")
    print("examples:", names[:: max(1, len(names) // 10)][:10])
