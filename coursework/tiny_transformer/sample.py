"""Generate new venue names from the trained TinyGPT and measure how many are novel.

Inputs : outputs/model.pt (written by train.py)
Outputs: printed names; outputs/synthetic/generated_names.csv (name, temperature, is_novel, is_synthetic=1)
Run    : python -I coursework/tiny_transformer/sample.py --n 20 --temperature 0.8
         python -I coursework/tiny_transformer/sample.py --n 10 --temperature 0.3 --top-k 5 --no-save

[N11] Sampling one character at a time:
  start with [<s>] -> model gives logits for the next char -> divide by temperature ->
  (optionally keep only the top-k) -> softmax -> draw one char -> append -> repeat
  until <e> is drawn or the name reaches block_size characters.
Every generated name is SYNTHETIC: it is not a real venue and must never be shown as one.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.tiny_transformer.data import Tokenizer, clean_all, load_names, split_names  # noqa: E402
from coursework.tiny_transformer.model import TinyGPT  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs"


def load_model(path: Path = OUT / "model.pt") -> tuple[TinyGPT, list]:
    ckpt = torch.load(path, weights_only=True)
    cfg = ckpt["cfg"]
    model = TinyGPT(len(ckpt["itos"]), cfg["block_size"], cfg["n_embd"], cfg["n_head"],
                    cfg["n_layer"], cfg["dropout"])
    model.load_state_dict(ckpt["state_dict"])
    model.eval()  # dropout off while sampling
    return model, ckpt["itos"]


@torch.no_grad()
def generate_one(model: TinyGPT, start_id: int, end_id: int, temperature: float,
                 top_k: int | None, gen: torch.Generator) -> list[int]:
    """[N11] Autoregressive sampling of one name. Returns ids without <s>/<e>."""
    ids = [start_id]
    while len(ids) < model.block_size:                     # never longer than the model can see
        x = torch.tensor([ids])                            # (1, T)
        logits, _ = model(x)                               # (1, T, V)
        logits = logits[0, -1] / temperature               # (V,) only the LAST position predicts next
        logits[start_id] = float("-inf")                   # <s> only ever starts a name, never inside one
        if top_k is not None:
            cutoff = torch.topk(logits, top_k).values[-1]  # k-th largest score
            logits = logits.masked_fill(logits < cutoff, float("-inf"))
        probs = F.softmax(logits, dim=-1)                  # (V,) probabilities
        next_id = torch.multinomial(probs, 1, generator=gen).item()
        if next_id == end_id:
            break
        ids.append(next_id)
    return ids[1:]


def sample_names(model: TinyGPT, itos: list, n: int, temperature: float,
                 top_k: int | None = None, seed: int = 0) -> list[str]:
    gen = torch.Generator().manual_seed(seed)
    tok = Tokenizer([])            # rebuild the tokenizer from the saved vocab
    tok.itos, tok.stoi = itos, {t: i for i, t in enumerate(itos)}
    return [tok.decode(generate_one(model, tok.start_id, tok.end_id, temperature, top_k, gen))
            for _ in range(n)]


def novelty_rate(samples: list[str], train_names: set) -> float:
    """[N11] Share of samples that are NOT an exact copy of a training name."""
    return sum(s not in train_names for s in samples) / max(len(samples), 1)


def temperature_summary(model: TinyGPT, itos: list, train_set: set, n: int = 200) -> dict:
    """[N11] Novelty, copy rate and mean length at a low, medium and high temperature."""
    summary = {}
    for t in (0.3, 0.8, 1.2):
        names = sample_names(model, itos, n, t, seed=1)
        summary[str(t)] = {"novelty_rate": novelty_rate(names, train_set),
                           "distinct_share": len(set(names)) / n,
                           "mean_length": sum(map(len, names)) / n, "examples": names[:5]}
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top-k", type=int, default=None)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-save", action="store_true", help="print only, do not write the CSV")
    p.add_argument("--summary", action="store_true", help="also write outputs/sampling.json (T=0.3/0.8/1.2)")
    args = p.parse_args()
    model, itos = load_model()
    train, _ = split_names(clean_all(load_names()), seed=0)  # same split as train.py (seed 0)
    train_set = set(train)
    samples = sample_names(model, itos, args.n, args.temperature, args.top_k, args.seed)
    for s in samples:
        print(("  " if s not in train_set else "* ") + s)
    rate = novelty_rate(samples, train_set)
    print(f"novelty rate: {rate:.0%} not in the training names (* = copied); T={args.temperature}")
    if not args.no_save:
        path = OUT / "synthetic" / "generated_names.csv"  # SYNTHETIC: generated names, no real source
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["name", "temperature", "is_novel", "is_synthetic"])
            for s in samples:
                w.writerow([s, args.temperature, int(s not in train_set), 1])
        print(f"wrote {path.relative_to(Path(__file__).resolve().parents[2])}")
    if args.summary:
        summary = temperature_summary(model, itos, train_set)
        (OUT / "sampling.json").write_text(json.dumps(summary, indent=2))
        for t, row in summary.items():
            print(f"T={t}: novelty {row['novelty_rate']:.0%}, distinct {row['distinct_share']:.0%}, "
                  f"mean length {row['mean_length']:.1f}, e.g. {row['examples'][:3]}")


if __name__ == "__main__":
    main()
