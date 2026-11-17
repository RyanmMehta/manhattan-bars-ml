"""End-to-end churn pipeline on the stand-in data + a metrics check against sklearn."""
import subprocess
import sys

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, f1_score, roc_auc_score

from coursework.churn import train_eval
from coursework.churn.build_dataset import TEST_CUTOFF, TRAIN_CUTOFF, build
from coursework.churn.load import STANDIN_DIR, load
from coursework.tests.conftest import ROOT


def test_metrics_match_sklearn():
    y = np.array([0, 0, 1, 1, 0, 1, 0, 0])
    p = np.array([0.1, 0.4, 0.35, 0.8, 0.2, 0.9, 0.6, 0.05])
    m = train_eval.metrics_at(y, p, 0.5)
    assert m["roc_auc"] == roc_auc_score(y, p)
    assert m["pr_auc"] == average_precision_score(y, p)
    assert m["brier"] == brier_score_loss(y, p)
    assert m["f1"] == f1_score(y, (p >= 0.5).astype(int))
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (2, 1, 1, 4)


def test_pipeline_end_to_end_on_standin():
    if not (STANDIN_DIR / "standin_scouts.csv").exists():  # SYNTHETIC: build the stand-in if needed
        subprocess.run([sys.executable, "-I", str(ROOT / "coursework/churn/make_standin_data.py")], check=True)
    data = load("standin")
    train, test = build(data, TRAIN_CUTOFF), build(data, TEST_CUTOFF)
    assert train["is_synthetic"].eq(1).all() and len(train) > 0 and len(test) > 0
    results = {name: train_eval.evaluate_family(name, train, test) for name in train_eval.GRIDS}
    assert len(results) == 5
    for r in results.values():
        assert 0 <= r["test"]["roc_auc"] <= 1 and 0 <= r["cv_oof"]["roc_auc"] <= 1
    best = max(r["cv_auc_mean"] for n, r in results.items() if n != "majority")
    assert best > results["majority"]["cv_auc_mean"]
