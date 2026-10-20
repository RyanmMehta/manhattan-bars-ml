"""Generate synthetic Manhattan-bar training data from venue_features.

Examples
  python -I src/simulate.py --method cart --n 20000
  python -I src/simulate.py --method copula --n 5000 --where "venue_type == 'Bar/Tavern'"
  python -I src/simulate.py --method cart --n 2000 --where "neighborhood == 'East Village' and osm_closes_late == 1"

Output: data/synthetic/<method>_<n>.csv and table synthetic_<method>_<n> in the database.
"""
import argparse
import pathlib
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from synth import GENERATORS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "manhattan_bars.db"
HIGH_NOISE_THRESHOLD = 3


def load_real():
    with sqlite3.connect(DB) as con:
        df = pd.read_sql("SELECT * FROM venue_features", con)
    return df.drop(columns=["license_id"])


def synthesize(real, method, n, seed=0, where=None):
    """Fit `method` on `real` and draw n rows. high_noise is derived from the
    synthetic complaint count so the label always agrees with it."""
    gen = GENERATORS[method](seed).fit(real.drop(columns=["high_noise"]))
    syn = gen.sample(n, where=where)
    syn["high_noise"] = (syn["noise_complaints"] >= HIGH_NOISE_THRESHOLD).astype(int)
    return syn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=sorted(GENERATORS), default="cart")
    ap.add_argument("--n", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--where", help="pandas query to condition the synthetic rows on")
    args = ap.parse_args()

    real = load_real()
    syn = synthesize(real, args.method, args.n, args.seed, args.where)
    out_dir = ROOT / "data" / "synthetic"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{args.method}_{args.n}.csv"
    syn.to_csv(path, index=False)
    with sqlite3.connect(DB) as con:
        syn.to_sql(f"synthetic_{args.method}_{args.n}", con, index=False, if_exists="replace")
    print(f"fitted {args.method} on {len(real):,} real venues, wrote {len(syn):,} synthetic rows")
    print(f"  {path.relative_to(ROOT)}  +  table synthetic_{args.method}_{args.n}")
    print(f"  high_noise rate: real {real['high_noise'].mean():.1%}  synthetic {syn['high_noise'].mean():.1%}")


if __name__ == "__main__":
    main()
