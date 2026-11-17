"""Interpret the churn models: odds ratios, the printed tree, permutation importance, and plots.

Inputs : the two churn_dataset CSVs + outputs/metrics.json (chosen settings) from train_eval.py
Outputs: "interpretation" section of outputs/report.md; PNGs in outputs/:
         timeline.png, roc_pr_test.png, calibration_test.png, permutation_importance.png
Run    : python -I coursework/churn/explain.py

Every model is refit here with the settings train_eval.py picked by CV (same seed -> same model),
so no pickled model files are needed.                                                     [N9]
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.metrics import precision_recall_curve, roc_curve  # noqa: E402
from sklearn.tree import export_text  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.churn.build_dataset import FEATURES, TEST_CUTOFF, TRAIN_CUTOFF  # noqa: E402
from coursework.churn.train_eval import make_model  # noqa: E402
from coursework.common import write_section  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs"
SUFFIX = " (synthetic data)"  # every plot built on synthetic data says so


def md_table(df: pd.DataFrame) -> str:
    """A small markdown table writer (avoids an extra dependency)."""
    fmt = lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)  # noqa: E731
    rows = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    rows += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in df.itertuples(index=False)]
    return "\n".join(rows)


def odds_ratio_table(model) -> pd.DataFrame:
    """[N6] exp(coefficient) = how the odds of churn multiply for +1 standard deviation of a feature."""
    coef = model[-1].coef_[0]
    table = pd.DataFrame({"feature": FEATURES, "coef_per_sd": coef, "odds_ratio_per_sd": np.exp(coef)})
    return table.reindex(table["coef_per_sd"].abs().sort_values(ascending=False).index)


def plot_timeline(path: Path) -> None:
    """[N2] The two snapshots: feature window, cutoff, label window."""
    dates = lambda s: pd.Timestamp(s)  # noqa: E731
    fig, ax = plt.subplots(figsize=(8, 2.4))
    for y, cut, label in [(1, TRAIN_CUTOFF, "train"), (0, TEST_CUTOFF, "test")]:
        c = dates(cut)
        ax.barh(y, (c - dates("2026-08-27")).days, left=dates("2026-08-27"), color="#cfd8e3", height=0.5)
        ax.barh(y, 28, left=c - pd.Timedelta(days=28), color="#4a78b5", height=0.5, label="28-day lookback" if y else None)
        ax.barh(y, 21, left=c, color="#e07b39", height=0.5, label="21-day label window" if y else None)
        ax.text(c, y + 0.32, f"{label} cutoff {cut}", ha="center", fontsize=8)
    ax.set_yticks([1, 0], ["train snapshot", "test snapshot"])
    ax.set_xlim(dates("2026-08-25"), dates("2026-11-16"))
    ax.legend(loc="lower left", fontsize=7)
    ax.set_title("Churn snapshots: features before the cutoff, label after" + SUFFIX, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plot_curves(models: dict, test: pd.DataFrame) -> None:
    """ROC + PR curves and a calibration curve on the out-of-time test snapshot."""
    y = test["churned"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 4))
    fig_c, ac = plt.subplots(figsize=(4.8, 4))
    for name, model in models.items():
        prob = model.predict_proba(test[FEATURES])[:, 1]
        fpr, tpr, _ = roc_curve(y, prob)
        prec, rec, _ = precision_recall_curve(y, prob)
        a1.plot(fpr, tpr, label=name)
        a2.plot(rec, prec, label=name)
        if name != "majority":
            frac_pos, mean_pred = calibration_curve(y, prob, n_bins=5, strategy="quantile")
            ac.plot(mean_pred, frac_pos, marker="o", label=name)
    a1.plot([0, 1], [0, 1], "k:", lw=0.8)
    a2.axhline(y.mean(), color="k", ls=":", lw=0.8, label=f"base rate {y.mean():.2f}")
    a1.set(xlabel="false positive rate", ylabel="true positive rate", title="ROC, test" + SUFFIX)
    a2.set(xlabel="recall", ylabel="precision", title="Precision-recall, test" + SUFFIX)
    a1.legend(fontsize=7)
    a2.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "roc_pr_test.png", dpi=100)
    ac.plot([0, 1], [0, 1], "k:", lw=0.8)
    ac.set(xlabel="mean predicted risk", ylabel="share that churned", title="Calibration, test" + SUFFIX)
    ac.title.set_fontsize(9)
    ac.legend(fontsize=7)
    fig_c.tight_layout()
    fig_c.savefig(OUT / "calibration_test.png", dpi=100)
    plt.close("all")


def importance(model, test: pd.DataFrame, name: str) -> pd.DataFrame:
    """[N9] Shuffle one feature at a time on the TEST snapshot; the ROC AUC drop = how much it mattered."""
    res = permutation_importance(model, test[FEATURES], test["churned"], scoring="roc_auc",
                                 n_repeats=30, random_state=0)
    table = pd.DataFrame({"feature": FEATURES, "auc_drop_mean": res.importances_mean,
                          "auc_drop_sd": res.importances_std}).sort_values("auc_drop_mean", ascending=False)
    top = table.head(10)[::-1]
    plt.figure(figsize=(6, 4))
    plt.barh(top["feature"], top["auc_drop_mean"], xerr=top["auc_drop_sd"], color="#4a78b5")
    plt.xlabel("drop in test ROC AUC when shuffled")
    plt.title(f"Permutation importance, {name}" + SUFFIX, fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT / "permutation_importance.png", dpi=100)
    plt.close()
    return table


def top_risk_table(model, test: pd.DataFrame) -> pd.DataFrame:
    """[N9] The business view: if we only contact the riskiest X% of Scouts, how many really churn?"""
    ranked = test.assign(prob=model.predict_proba(test[FEATURES])[:, 1]).sort_values("prob", ascending=False)
    rows = []
    for share in (0.10, 0.25, 0.50):
        top = ranked.head(max(1, round(len(ranked) * share)))
        rows.append({"riskiest share": f"{share:.0%}", "scouts": len(top), "churned": int(top["churned"].sum()),
                     "churn rate": float(top["churned"].mean()), "lift vs base": float(top["churned"].mean() / ranked["churned"].mean())})
    return pd.DataFrame(rows)


def main() -> None:
    summary = json.loads((OUT / "metrics.json").read_text())
    # SYNTHETIC: datasets built from synthetic Scouts
    train = pd.read_csv(OUT / "synthetic" / f"churn_dataset_{TRAIN_CUTOFF}.csv")
    test = pd.read_csv(OUT / "synthetic" / f"churn_dataset_{TEST_CUTOFF}.csv")
    models = {name: make_model(name, r["params"]).fit(train[FEATURES], train["churned"])
              for name, r in summary["models"].items()}
    selected = summary["selected_model"]
    odds = odds_ratio_table(models["logistic"])
    tree_text = export_text(models["tree"][-1], feature_names=FEATURES, decimals=1, show_weights=True)
    imp = importance(models[selected], test, selected)
    plot_timeline(OUT / "timeline.png")
    plot_curves(models, test)
    md = ["## Interpretation (synthetic data)", "",
          "### Logistic regression odds ratios (per +1 standard deviation, sorted by size)", "",
          md_table(odds), "",
          f"### Decision tree (depth {summary['models']['tree']['params']['max_depth']}), printed", "",
          "Each leaf shows the class-weighted counts [stay, churn] and the predicted class (1 = churn). "
          "Two sibling leaves can both say 1: the split still made one of them purer.", "",
          "```", tree_text.strip(), "```", "",
          f"### Permutation importance on the test snapshot ({selected}, 30 shuffles)", "",
          md_table(imp.head(10)), "",
          f"### Targeting view: churn rate among the riskiest Scouts (test snapshot, {selected})", "",
          md_table(top_risk_table(models[selected], test)), "",
          "Plots: `timeline.png`, `roc_pr_test.png`, `calibration_test.png`, `permutation_importance.png`."]
    write_section(OUT / "report.md", "interpretation", "\n".join(md))
    print(odds.head(6).to_string(index=False))
    print(tree_text)


if __name__ == "__main__":
    main()
