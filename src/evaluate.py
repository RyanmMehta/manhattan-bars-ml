"""Test synthetic data against the real data with ML models.

Protocol (repeated over several random seeds):
  1. Split the real venues 70/30 into real_train / real_test (stratified).
  2. Fit each generator on real_train ONLY, sample synthetic rows.
  3. Utility - train models and score them on real_test, which no generator saw:
       TRTR  train on real_train                    (the ceiling)
       TSTR  train on synthetic only                (can synthetic replace real?)
       AUG   train on real_train + 2x synthetic     (does synthetic add value?)
     Task A: classify high_noise (>=3 noise complaints in 3 yrs)  - ROC AUC, PR AUC, F1
     Task B: regress log(1 + noise_complaints)                   - MAE, R^2
  4. Fidelity - per-column KS / TVD, correlation-matrix error, and a
     discriminator that tries to tell real from synthetic (AUC 0.5 = can't).
  5. Privacy - distance from each synthetic row to its closest real_train row,
     compared with the same distance for real_test rows; exact-copy rate.

Usage:  python -I src/evaluate.py [--seeds 3]
Writes reports/results.json and reports/report.md
"""
import argparse
import json
import pathlib
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, mean_absolute_error, r2_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from simulate import load_real, synthesize  # noqa: E402
from synth import GENERATORS, split_types  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
TARGETS = ["noise_complaints", "high_noise"]
CLASSIFIERS = {
    "LogisticRegression": lambda s: LogisticRegression(max_iter=2000, C=0.5),
    "RandomForest": lambda s: RandomForestClassifier(400, min_samples_leaf=3, n_jobs=-1, random_state=s),
    "GradientBoosting": lambda s: HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=s),
}


def preprocessor(df):
    cats, nums = split_types(df)
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=5, sparse_output=False), cats),
        ("num", StandardScaler(), nums),
    ])


def features(df):
    return df.drop(columns=TARGETS)


# ---------------------------------------------------------------- utility
def utility(train, test, seed):
    Xtr, Xte = features(train), features(test)
    out = {}
    for name, make in CLASSIFIERS.items():
        model = make_pipeline(preprocessor(Xtr), make(seed)).fit(Xtr, train["high_noise"])
        p = model.predict_proba(Xte)[:, 1]
        out[name] = {"roc_auc": roc_auc_score(test["high_noise"], p),
                     "pr_auc": average_precision_score(test["high_noise"], p),
                     "f1": f1_score(test["high_noise"], p >= 0.5)}
    reg = make_pipeline(preprocessor(Xtr), HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05,
                                                                         random_state=seed))
    reg.fit(Xtr, np.log1p(train["noise_complaints"]))
    pred = reg.predict(Xte)
    y = np.log1p(test["noise_complaints"])
    out["Regression"] = {"mae_log": mean_absolute_error(y, pred), "r2_log": r2_score(y, pred),
                         "spearman": stats.spearmanr(y, pred).statistic}
    return out


# ---------------------------------------------------------------- fidelity
def fidelity(real, syn, seed):
    cats, nums = split_types(real.drop(columns=["high_noise"]))
    col = {}
    for c in nums:
        col[c] = {"metric": "KS", "value": stats.ks_2samp(real[c], syn[c]).statistic}
    for c in cats:
        p = real[c].value_counts(normalize=True)
        q = syn[c].value_counts(normalize=True)
        col[c] = {"metric": "TVD", "value": 0.5 * p.subtract(q, fill_value=0).abs().sum()}
    corr_err = np.abs(real[nums].corr("spearman") - syn[nums].corr("spearman")).to_numpy()
    corr_err = np.nanmean(corr_err[np.triu_indices(len(nums), 1)])

    both = pd.concat([real, syn.sample(len(real), random_state=seed, replace=len(syn) < len(real))])
    label = np.r_[np.zeros(len(real)), np.ones(len(real))]
    clf = make_pipeline(preprocessor(both), HistGradientBoostingClassifier(max_iter=200, random_state=seed))
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    p = cross_val_predict(clf, both, label, cv=cv, method="predict_proba")[:, 1]
    return {"columns": col,
            "mean_ks": float(np.mean([col[c]["value"] for c in nums])),
            "mean_tvd": float(np.mean([col[c]["value"] for c in cats])),
            "corr_error": float(corr_err),
            "discriminator_auc": roc_auc_score(label, p)}


# ---------------------------------------------------------------- privacy
def privacy(train, test, syn):
    pre = preprocessor(train).fit(train)
    nn = NearestNeighbors(n_neighbors=1).fit(pre.transform(train))
    d_syn = nn.kneighbors(pre.transform(syn))[0][:, 0]
    d_test = nn.kneighbors(pre.transform(test))[0][:, 0]
    return {"dcr_median_synthetic": float(np.median(d_syn)),
            "dcr_median_holdout": float(np.median(d_test)),
            "dcr_ratio": float(np.median(d_syn) / np.median(d_test)),
            "exact_copy_rate": float((d_syn < 1e-8).mean())}


# ---------------------------------------------------------------- driver
def mean_std(values):
    return {"mean": float(np.mean(values)), "std": float(np.std(values))}


def aggregate(runs):
    """runs: list of nested dicts with numeric leaves -> same shape with mean/std."""
    first = runs[0]
    if isinstance(first, dict):
        return {k: aggregate([r[k] for r in runs]) for k in first if not isinstance(first[k], str)}
    return mean_std(runs)


def run(seeds):
    real = load_real()
    results = {"n_real": len(real), "high_noise_rate": float(real["high_noise"].mean()),
               "seeds": seeds, "utility": {}, "fidelity": {}, "privacy": {}}
    util_runs = {"TRTR": []}
    fid_runs, priv_runs = {}, {}
    for seed in range(seeds):
        train, test = train_test_split(real, test_size=0.3, stratify=real["high_noise"], random_state=seed)
        print(f"seed {seed}: train {len(train):,}  test {len(test):,}")
        util_runs["TRTR"].append(utility(train, test, seed))
        for method in GENERATORS:
            t0 = time.time()
            syn = synthesize(train, method, n=3 * len(train), seed=seed)
            tstr_part, aug_part = syn.iloc[:len(train)], syn.iloc[len(train):]
            util_runs.setdefault(f"TSTR:{method}", []).append(utility(tstr_part, test, seed))
            util_runs.setdefault(f"AUG:{method}", []).append(
                utility(pd.concat([train, aug_part], ignore_index=True), test, seed))
            fid_runs.setdefault(method, []).append(fidelity(train, tstr_part, seed))
            priv_runs.setdefault(method, []).append(privacy(train, test, tstr_part))
            print(f"  {method:<12} done in {time.time() - t0:.0f}s")
    results["utility"] = {k: aggregate(v) for k, v in util_runs.items()}
    results["fidelity"] = {k: aggregate(v) for k, v in fid_runs.items()}
    results["privacy"] = {k: aggregate(v) for k, v in priv_runs.items()}
    return results


def fmt(m, digits=3):
    return f"{m['mean']:.{digits}f} ± {m['std']:.{digits}f}"


def write_report(res):
    u, f, p = res["utility"], res["fidelity"], res["privacy"]
    lines = [
        "# Manhattan bars - synthetic vs real evaluation", "",
        f"Real venues: {res['n_real']:,}  ·  high_noise base rate: {res['high_noise_rate']:.1%}  ·  "
        f"seeds: {res['seeds']}  ·  every score is measured on held-out REAL venues.", "",
        "## Task A: predict high-noise venues (≥3 noise complaints in 3 years)", "",
        "| Training data | Model | ROC AUC | PR AUC | F1 |", "|---|---|---|---|---|",
    ]
    for scen, models in u.items():
        for m in CLASSIFIERS:
            r = models[m]
            lines.append(f"| {scen} | {m} | {fmt(r['roc_auc'])} | {fmt(r['pr_auc'])} | {fmt(r['f1'])} |")
    lines += ["", "## Task B: predict log(1 + noise complaints), gradient boosting", "",
              "| Training data | MAE (log) | R² (log) | Spearman |", "|---|---|---|---|"]
    for scen, models in u.items():
        r = models["Regression"]
        lines.append(f"| {scen} | {fmt(r['mae_log'])} | {fmt(r['r2_log'])} | {fmt(r['spearman'])} |")
    lines += ["", "## Fidelity and privacy of each generator", "",
              "| Generator | mean KS ↓ | mean TVD ↓ | corr error ↓ | discriminator AUC (0.5 best) | "
              "DCR ratio (≈1 good, ≪1 copies) | exact copies |",
              "|---|---|---|---|---|---|---|"]
    for g in f:
        lines.append(f"| {g} | {fmt(f[g]['mean_ks'])} | {fmt(f[g]['mean_tvd'])} | {fmt(f[g]['corr_error'])} | "
                     f"{fmt(f[g]['discriminator_auc'])} | {fmt(p[g]['dcr_ratio'], 2)} | "
                     f"{p[g]['exact_copy_rate']['mean']:.1%} |")
    lines += ["", "## Worst-matched columns per generator (KS or TVD)", ""]
    for g in f:
        cols = sorted(f[g]["columns"].items(), key=lambda kv: -kv[1]["value"]["mean"])[:5]
        lines.append(f"- **{g}**: " + ", ".join(f"{c} {v['value']['mean']:.3f}" for c, v in cols))
    (REPORTS / "report.md").write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    REPORTS.mkdir(exist_ok=True)
    res = run(args.seeds)
    (REPORTS / "results.json").write_text(json.dumps(res, indent=2))
    write_report(res)
    print(f"\nwrote reports/results.json and reports/report.md")
    print((REPORTS / "report.md").read_text())


if __name__ == "__main__":
    main()
