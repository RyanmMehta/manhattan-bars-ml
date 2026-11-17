"""Train TinyGPT on Manhattan venue names (CPU only) and save metrics + a loss curve.

Inputs : data/manhattan_bars.db (read-only, via data.py)
Outputs: outputs/metrics.json, outputs/loss_curve.png, outputs/model.pt (not committed)
Run    : python -I coursework/tiny_transformer/train.py              (default run, ~1-3 min)
         python -I coursework/tiny_transformer/train.py --ablation   (also 3 small variants)

Steps
  1. load + clean + split names, build tokenizer, make (x, y) examples   [N1][N2][N4]
  2. compute unigram / bigram baselines on the same val names           [N3]
  3. build TinyGPT, AdamW optimizer, cosine learning-rate schedule      [N10]
  4. loop: random batch -> loss -> backward -> step; every eval_every steps measure
     train and val loss; keep the best weights; stop early if val stops improving [N10]
  5. save metrics.json + loss_curve.png                                 [N12]
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # draw to files, no window
import matplotlib.pyplot as plt  # noqa: E402
import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.common import set_seed  # noqa: E402
from coursework.tiny_transformer import baselines  # noqa: E402
from coursework.tiny_transformer.data import (Tokenizer, clean_all, load_names,  # noqa: E402
                                              make_examples, split_names)
from coursework.tiny_transformer.model import TinyGPT, count_params  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs"
torch.set_num_threads(4)  # CPU only; a fixed thread count also keeps timings comparable


@torch.no_grad()
def evaluate(model: TinyGPT, x: torch.Tensor, y: torch.Tensor) -> float:
    """Mean loss (nats/char) over ALL given examples, with dropout switched off."""
    model.eval()
    _, loss = model(x, y)
    model.train()
    return loss.item()


def lr_at(step: int, max_steps: int, lr_max: float, lr_min: float) -> float:
    """[N10] Cosine schedule: start at lr_max, glide smoothly down to lr_min at max_steps."""
    progress = min(step / max_steps, 1.0)
    return lr_min + 0.5 * (lr_max - lr_min) * (1 + math.cos(math.pi * progress))


def train_model(cfg: dict, data: dict, verbose: bool = True) -> dict:
    """Train one model with config cfg. Returns its history and best val loss."""
    set_seed(cfg["seed"])
    tok = data["tok"]
    x_tr, y_tr = make_examples(data["train"], tok, cfg["block_size"])  # (N_train, T)
    x_va, y_va = make_examples(data["val"], tok, cfg["block_size"])    # (N_val, T)
    x_tr_eval, y_tr_eval = x_tr[:1000], y_tr[:1000]  # fixed train subset to report train loss
    model = TinyGPT(tok.vocab_size, cfg["block_size"], cfg["n_embd"], cfg["n_head"],
                    cfg["n_layer"], cfg["dropout"])
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr_max"], weight_decay=0.01)
    gen = torch.Generator().manual_seed(cfg["seed"])  # own generator -> same batches every run
    history, best_val, best_state, bad_evals, step = [], float("inf"), None, 0, 0
    for step in range(1, cfg["max_steps"] + 1):
        for group in opt.param_groups:
            group["lr"] = lr_at(step, cfg["max_steps"], cfg["lr_max"], cfg["lr_min"])
        idx = torch.randint(0, len(x_tr), (cfg["batch_size"],), generator=gen)  # random names
        _, loss = model(x_tr[idx], y_tr[idx])
        opt.zero_grad()
        loss.backward()          # autograd fills .grad of every weight
        opt.step()               # AdamW update
        if step % cfg["eval_every"] == 0 or step == cfg["max_steps"]:
            tr, va = evaluate(model, x_tr_eval, y_tr_eval), evaluate(model, x_va, y_va)
            history.append({"step": step, "train_loss": tr, "val_loss": va})
            if verbose:
                print(f"step {step:5d}  train {tr:.4f}  val {va:.4f}")
            if va < best_val - 1e-4:   # [N10] early stopping bookkeeping
                best_val, bad_evals = va, 0
                best_state = {k: v.clone() for k, v in model.state_dict().items()}
            else:
                bad_evals += 1
                if bad_evals >= cfg["patience"]:
                    if verbose:
                        print(f"early stop: no val improvement in {cfg['patience']} evals")
                    break
    model.load_state_dict(best_state)  # keep the best weights, not the last ones
    return {"model": model, "history": history, "best_val_loss": best_val,
            "steps_run": step, "params": count_params(model)}


def plot_curve(history: list, base: dict, path: Path) -> None:
    steps = [h["step"] for h in history]
    plt.figure(figsize=(6.5, 4))
    plt.plot(steps, [h["train_loss"] for h in history], label="train loss")
    plt.plot(steps, [h["val_loss"] for h in history], label="val loss")
    plt.axhline(base["bigram"], color="grey", ls="--", label=f"bigram baseline ({base['bigram']:.3f})")
    plt.axhline(base["unigram"], color="grey", ls=":", label=f"unigram baseline ({base['unigram']:.3f})")
    plt.xlabel("training step")
    plt.ylabel("loss (nats per character)")
    plt.title("TinyGPT on Manhattan venue names")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-layer", type=int, default=2)
    p.add_argument("--n-head", type=int, default=4)
    p.add_argument("--n-embd", type=int, default=64)
    p.add_argument("--block-size", type=int, default=32)
    p.add_argument("--dropout", type=float, default=0.1)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--max-steps", type=int, default=3000)
    p.add_argument("--eval-every", type=int, default=100)
    p.add_argument("--patience", type=int, default=5)
    p.add_argument("--ablation", action="store_true", help="also run the 3 ablation variants")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = {"seed": args.seed, "n_layer": args.n_layer, "n_head": args.n_head, "n_embd": args.n_embd,
           "block_size": args.block_size, "dropout": args.dropout, "batch_size": args.batch_size,
           "max_steps": args.max_steps, "eval_every": args.eval_every, "patience": args.patience,
           "lr_max": 3e-3, "lr_min": 3e-4}
    names = clean_all(load_names())
    train, val = split_names(names, seed=args.seed)
    tok = Tokenizer(train + val)
    data = {"train": train, "val": val, "tok": tok}
    base = {"uniform": math.log(tok.vocab_size), "unigram": baselines.unigram_loss(train, val, tok),
            "bigram": baselines.bigram_loss(train, val, tok)}
    print(f"names: {len(train)} train / {len(val)} val, vocab {tok.vocab_size}; baselines {base}")
    start = time.time()
    result = train_model(cfg, data)
    runtime = time.time() - start
    OUT.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": result["model"].state_dict(), "cfg": cfg, "itos": tok.itos}, OUT / "model.pt")
    plot_curve(result["history"], base, OUT / "loss_curve.png")
    best = result["best_val_loss"]
    metrics = {"config": cfg, "n_train_names": len(train), "n_val_names": len(val),
               "vocab_size": tok.vocab_size, "params": result["params"], "steps_run": result["steps_run"],
               "runtime_seconds": round(runtime, 1), "best_val_loss": best,
               "val_perplexity_per_char": math.exp(best), "baselines": base,
               "improvement_vs_bigram_pct": 100 * (base["bigram"] - best) / base["bigram"],
               "beats_bigram": best < base["bigram"], "history": result["history"]}
    if args.ablation:
        metrics["ablation"] = run_ablation(cfg, data)
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"best val {best:.4f} nats/char (perplexity {math.exp(best):.2f}); bigram {base['bigram']:.4f}; "
          f"{metrics['improvement_vs_bigram_pct']:.1f}% better; {runtime:.0f}s")


def run_ablation(cfg: dict, data: dict) -> list:
    """[N12] Change one setting at a time vs the default config and record val loss only."""
    variants = [("n_layer=1", {"n_layer": 1}), ("block_size=16", {"block_size": 16}),
                ("dropout=0", {"dropout": 0.0})]
    rows = []
    for label, change in variants:
        res = train_model({**cfg, **change}, data, verbose=False)
        rows.append({"variant": label, "best_val_loss": res["best_val_loss"], "params": res["params"]})
        print(f"ablation {label:14s} val {res['best_val_loss']:.4f}")
    return rows


if __name__ == "__main__":
    main()
