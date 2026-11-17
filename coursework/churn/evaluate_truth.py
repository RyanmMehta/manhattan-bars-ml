"""EVALUATION ONLY: compare churn predictions with the simulator's hidden truth table.

This is the ONLY file allowed to read syn_scout_truth (a test enforces it). Nothing here
feeds back into features or model choice; it only tells us whether the model is sensible.
Real life has no truth table, so this step disappears once real Scouts replace synthetic ones.

Inputs : outputs/synthetic/scout_churn_risk.csv (train_eval.py), the test churn_dataset CSV,
         syn_scout_truth from data/live_sim.db or standin_scout_truth.csv
Outputs: "truth" section of outputs/report.md
Run    : python -I coursework/churn/evaluate_truth.py
"""
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.churn.build_dataset import TEST_CUTOFF, cutoff_ts  # noqa: E402
from coursework.churn.load import STANDIN_DIR, pick_source, to_ny  # noqa: E402
from coursework.common import LIVE_SIM_DB, connect_read_only, write_section  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs"


def load_truth() -> pd.DataFrame:
    if pick_source() == "db":
        # SYNTHETIC: eval-only truth table from live-sim; no real-world replacement exists
        with connect_read_only(LIVE_SIM_DB) as conn:
            truth = pd.read_sql_query("SELECT * FROM syn_scout_truth", conn)
    else:
        truth = pd.read_csv(STANDIN_DIR / "standin_scout_truth.csv")  # SYNTHETIC: stand-in truth
    truth["churned_at"] = to_ny(truth["churned_at"])
    return truth


def auc_by(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """ROC AUC inside each group (only groups with >= 5 Scouts and both outcomes)."""
    rows = []
    for value, g in df.groupby(column):
        ok = len(g) >= 5 and g["churned"].nunique() == 2
        rows.append({column: value, "n": len(g), "churn_rate": g["churned"].mean(),
                     "roc_auc": roc_auc_score(g["churned"], g["churn_prob"]) if ok else None})
    return pd.DataFrame(rows)


def table(df: pd.DataFrame) -> str:
    fmt = lambda v: "n/a" if v is None or v != v else (f"{v:.3f}" if isinstance(v, float) else str(v))  # noqa: E731
    lines = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    return "\n".join(lines + ["| " + " | ".join(fmt(v) for v in r) + " |" for r in df.itertuples(index=False)])


def main() -> None:
    risk = pd.read_csv(OUT / "synthetic" / "scout_churn_risk.csv")  # SYNTHETIC: predictions on syn Scouts
    test = pd.read_csv(OUT / "synthetic" / f"churn_dataset_{TEST_CUTOFF}.csv")  # SYNTHETIC
    df = test[["scout_id", "churned"]].merge(risk, on="scout_id").merge(load_truth(), on="scout_id")
    window_end = cutoff_ts(TEST_CUTOFF) + pd.Timedelta(days=21)
    # Truth says "quit for good before the end of the label window"
    df["truth_quit"] = (df["churned_at"].notna() & (df["churned_at"] < window_end)).astype(int)
    agree = (df["truth_quit"] == df["churned"]).mean()
    label_only = int(((df["churned"] == 1) & (df["truth_quit"] == 0)).sum())
    truth_only = int(((df["churned"] == 0) & (df["truth_quit"] == 1)).sum())
    auc_label = roc_auc_score(df["churned"], df["churn_prob"])
    auc_truth = roc_auc_score(df["truth_quit"], df["churn_prob"]) if df["truth_quit"].nunique() == 2 else None
    rho, _ = spearmanr(df["churn_prob"], df["true_accuracy"])
    warn = "**Suspiciously easy (AUC > 0.95): check for leakage.**" if auc_label > 0.95 else \
        "AUC is below 0.95, so there is no sign of a 'too easy' leak."
    md = ["## Sanity check against the simulator's truth table (evaluation only, synthetic data)", "",
          f"Test snapshot (cutoff {TEST_CUTOFF}), {len(df)} Scouts.", "",
          f"- Our report-based label (0 reports in 21 days) agrees with the truth 'quit for good before "
          f"{window_end.date()}' for **{agree:.0%}** of Scouts. Disagreements: "
          f"{label_only} Scouts were silent for 21 days but had not quit (label 1, truth 0); "
          f"{truth_only} reported in the window and then quit (label 0, truth 1).",
          f"- ROC AUC of the risk score vs our label: {auc_label:.3f}; vs the truth quit flag: "
          f"{auc_truth:.3f}." if auc_truth is not None else "- truth flag has one class only",
          f"- Spearman correlation of risk with `true_accuracy`: {rho:+.2f} (near 0 means the risk score "
          "is not just tracking how accurate a Scout's reports are).",
          f"- {warn}", "", "### By archetype", "", table(auc_by(df, "archetype")), "",
          "### By cohort week", "", table(auc_by(df, "cohort_week"))]
    write_section(OUT / "report.md", "truth", "\n".join(md))
    print("\n".join(md[2:8]))


if __name__ == "__main__":
    main()
