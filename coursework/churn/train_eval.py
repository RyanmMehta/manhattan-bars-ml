"""Compare a majority baseline, logistic regression and three tree models for Scout churn.

Goal [N1]: rank Scouts by their risk of going quiet, so bounties can be aimed at them.

Inputs : outputs/synthetic/churn_dataset_<train cutoff>.csv and _<test cutoff>.csv (build_dataset.py)
Outputs: outputs/metrics.json, the "results" section of outputs/report.md,
         outputs/synthetic/scout_churn_risk.csv (test-snapshot risk from the selected model)
Run    : python -I coursework/churn/train_eval.py

Steps
  1. For each model family, pick its settings by repeated stratified 5-fold CV (5 x 3) ROC AUC
     on the TRAIN snapshot only                                                       [N5][N6][N7]
  2. Out-of-fold (OOF) predictions -> pick the threshold that maximises F1 (never on test) [N8]
  3. Refit on the whole train snapshot, score ONCE on the later TEST snapshot           [N4]
  4. ROC AUC, PR AUC (+ base rate), Brier, P/R/F1 at the threshold, confusion matrix;
     bootstrap 95% CIs on the test AUCs                                                  [N8]
  5. The model with the best mean CV ROC AUC is "selected" (the test set never chooses)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_recall_curve, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import RepeatedStratifiedKFold, StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from coursework.churn.build_dataset import FEATURES, TEST_CUTOFF, TRAIN_CUTOFF  # noqa: E402
from coursework.common import write_section  # noqa: E402

OUT = Path(__file__).resolve().parent / "outputs"
SEED = 0


def make_model(name: str, params: dict):
    """Every model is a Pipeline: median imputation (fit on training rows only) -> model.  [N5]"""
    if name == "majority":
        return make_pipeline(SimpleImputer(strategy="median"), DummyClassifier(strategy="most_frequent"))
    if name == "logistic":  # [N6] scale first: L2 penalty and coefficients assume comparable units
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             LogisticRegression(C=params["C"], class_weight="balanced", max_iter=2000))
    if name == "tree":      # [N7] shallow on purpose, so it can be printed and read
        return make_pipeline(SimpleImputer(strategy="median"), DecisionTreeClassifier(
            max_depth=params["max_depth"], min_samples_leaf=5, class_weight="balanced", random_state=SEED))
    if name == "forest":
        return make_pipeline(SimpleImputer(strategy="median"), RandomForestClassifier(
            n_estimators=300, min_samples_leaf=params["min_samples_leaf"], class_weight="balanced",
            random_state=SEED, n_jobs=-1))
    if name == "boosting":
        return make_pipeline(SimpleImputer(strategy="median"), HistGradientBoostingClassifier(
            learning_rate=params["learning_rate"], random_state=SEED))
    raise ValueError(name)


# The whole hyperparameter search, written out in full (PRD: "small, listed grid").
GRIDS = {"majority": [{}],
         "logistic": [{"C": c} for c in (0.1, 1.0, 10.0)],
         "tree": [{"max_depth": d} for d in (2, 3, 4)],
         "forest": [{"min_samples_leaf": m} for m in (5, 20)],
         "boosting": [{"learning_rate": lr} for lr in (0.05, 0.1)]}


def cv_auc(name: str, params: dict, X: pd.DataFrame, y: pd.Series) -> list[float]:
    """ROC AUC on each of the 15 folds of repeated stratified 5-fold CV."""
    folds = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=SEED)
    scores = []
    for train_idx, val_idx in folds.split(X, y):
        model = make_model(name, params).fit(X.iloc[train_idx], y.iloc[train_idx])
        prob = model.predict_proba(X.iloc[val_idx])[:, 1]
        scores.append(roc_auc_score(y.iloc[val_idx], prob))
    return scores


def choose_threshold(y: np.ndarray, prob: np.ndarray) -> float:
    """[N8] Threshold with the highest F1 on OUT-OF-FOLD predictions (not 0.5, not the test set)."""
    precision, recall, thresholds = precision_recall_curve(y, prob)
    f1 = 2 * precision * recall / np.clip(precision + recall, 1e-12, None)
    return float(thresholds[np.argmax(f1[:-1])])  # the last P/R point has no threshold


def metrics_at(y: np.ndarray, prob: np.ndarray, threshold: float) -> dict:
    """[N8] All headline metrics for one set of predictions."""
    pred = (prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"roc_auc": roc_auc_score(y, prob), "pr_auc": average_precision_score(y, prob),
            "base_rate": float(np.mean(y)), "brier": brier_score_loss(y, prob), "threshold": threshold,
            "precision": precision_score(y, pred, zero_division=0), "recall": recall_score(y, pred),
            "f1": f1_score(y, pred, zero_division=0), "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}


def bootstrap_ci(y: np.ndarray, prob: np.ndarray, metric, n: int = 1000) -> list[float]:
    """[N8] 95% CI: resample Scouts with replacement 1,000 times, recompute, take 2.5/97.5 percentiles."""
    rng = np.random.default_rng(SEED)
    values = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() != y[idx].max():   # need both classes in the resample
            values.append(metric(y[idx], prob[idx]))
    return [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]


def evaluate_family(name: str, train: pd.DataFrame, test: pd.DataFrame) -> dict:
    X, y = train[FEATURES], train["churned"]
    tried = [(params, cv_auc(name, params, X, y)) for params in GRIDS[name]]
    params, fold_aucs = max(tried, key=lambda t: np.mean(t[1]))           # step 1
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    oof = cross_val_predict(make_model(name, params), X, y, cv=folds, method="predict_proba")[:, 1]
    threshold = choose_threshold(y.to_numpy(), oof)                        # step 2
    model = make_model(name, params).fit(X, y)                             # step 3
    test_prob = model.predict_proba(test[FEATURES])[:, 1]
    y_test = test["churned"].to_numpy()
    return {"params": params, "cv_auc_mean": float(np.mean(fold_aucs)), "cv_auc_sd": float(np.std(fold_aucs)),
            "grid": [{"params": p, "cv_auc_mean": float(np.mean(a))} for p, a in tried],
            "cv_oof": metrics_at(y.to_numpy(), oof, threshold),
            "test": metrics_at(y_test, test_prob, threshold),
            "test_roc_auc_ci": bootstrap_ci(y_test, test_prob, roc_auc_score),
            "test_pr_auc_ci": bootstrap_ci(y_test, test_prob, average_precision_score),
            "test_prob": test_prob.tolist()}


def results_markdown(results: dict, train: pd.DataFrame, test: pd.DataFrame, selected: str) -> str:
    lines = ["## Results: 5 models x (CV on train snapshot, out-of-time test) (synthetic data)", "",
             f"Train snapshot cutoff {TRAIN_CUTOFF}: {len(train)} Scouts, base rate {train.churned.mean():.1%}. "
             f"Test snapshot cutoff {TEST_CUTOFF}: {len(test)} Scouts, base rate {test.churned.mean():.1%}.", "",
             "| model | settings | split | ROC AUC | PR AUC (base) | Brier | threshold | precision | recall | F1 |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        for split, m in [("CV (OOF)", r["cv_oof"]), ("test", r["test"])]:
            auc = f"{m['roc_auc']:.3f}"
            if split == "test":
                auc += " [{:.2f}, {:.2f}]".format(*r["test_roc_auc_ci"])
            else:
                auc += f" (15-fold {r['cv_auc_mean']:.3f} ± {r['cv_auc_sd']:.3f})"
            lines.append(f"| {name}{' **(selected)**' if name == selected else ''} | {r['params']} | {split} | {auc} "
                         f"| {m['pr_auc']:.3f} ({m['base_rate']:.2f}) | {m['brier']:.3f} | {m['threshold']:.2f} "
                         f"| {m['precision']:.2f} | {m['recall']:.2f} | {m['f1']:.2f} |")
    sel = results[selected]
    lift = sel["test"]["pr_auc"] / sel["test"]["base_rate"]
    best_brier = min((n for n in results if n != "majority"), key=lambda n: results[n]["test"]["brier"])
    lines += ["", "Threshold = max F1 on out-of-fold train predictions, then applied unchanged to test. "
              "Test ROC AUC brackets are bootstrap 95% CIs (1,000 resamples of Scouts). "
              "With under 100 Scouts per snapshot the CIs overlap a lot, so the ranking between the "
              "non-baseline models is not reliable; only 'better than the majority baseline' is.", "",
              "### PRD targets (placeholders) vs result", "",
              f"- Selected model test ROC AUC >= 0.75: **{sel['test']['roc_auc']:.3f}** "
              f"({'met' if sel['test']['roc_auc'] >= 0.75 else 'MISSED'})",
              f"- PR AUC lift >= 2x base rate: **{lift:.2f}x** ({'met' if lift >= 2 else 'MISSED'})",
              f"- Best test Brier <= logistic regression's: best is {best_brier} "
              f"({results[best_brier]['test']['brier']:.3f} vs logistic {results['logistic']['test']['brier']:.3f})",
              f"- Snapshot sizes: train {len(train)} Scouts / {int(train.churned.sum())} churners "
              f"(plan wanted >= 60 / >= 15: {'met' if len(train) >= 60 and train.churned.sum() >= 15 else 'MISSED'})"]
    return "\n".join(lines)


def main() -> None:
    # SYNTHETIC: datasets built from synthetic Scouts; rebuild from real tables to swap
    train = pd.read_csv(OUT / "synthetic" / f"churn_dataset_{TRAIN_CUTOFF}.csv")
    test = pd.read_csv(OUT / "synthetic" / f"churn_dataset_{TEST_CUTOFF}.csv")
    results = {}
    for name in GRIDS:
        results[name] = evaluate_family(name, train, test)
        r = results[name]
        print(f"{name:9s} {str(r['params']):28s} CV AUC {r['cv_auc_mean']:.3f}  test AUC {r['test']['roc_auc']:.3f}"
              f"  test PR AUC {r['test']['pr_auc']:.3f}  Brier {r['test']['brier']:.3f}")
    selected = max((n for n in results if n != "majority"), key=lambda n: results[n]["cv_auc_mean"])
    print(f"selected by CV: {selected}")
    risk = pd.DataFrame({"scout_id": test["scout_id"], "cutoff": TEST_CUTOFF,
                         "churn_prob": np.round(results[selected]["test_prob"], 4), "is_synthetic": 1})
    risk.to_csv(OUT / "synthetic" / "scout_churn_risk.csv", index=False)  # SYNTHETIC: predictions on syn Scouts
    for r in results.values():
        r.pop("test_prob")
    summary = {"train_cutoff": TRAIN_CUTOFF, "test_cutoff": TEST_CUTOFF, "n_train": len(train),
               "n_test": len(test), "selected_model": selected, "features": FEATURES, "models": results}
    (OUT / "metrics.json").write_text(json.dumps(summary, indent=2, default=float))
    write_section(OUT / "report.md", "header", "# Scout churn report (synthetic data)\n\n"
                  "Built by the scripts in `coursework/churn/` (see NOTES.md). All Scouts are "
                  "SYNTHETIC; nothing here is evidence about real Scouts.")
    write_section(OUT / "report.md", "results", results_markdown(results, train, test, selected))


if __name__ == "__main__":
    main()
