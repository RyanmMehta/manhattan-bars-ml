"""Churn dataset tests on a hand-made 3-Scout fixture (tests/fixtures/synthetic/)."""
import re
from pathlib import Path

import pandas as pd

from coursework.churn.build_dataset import FEATURES, build
from coursework.churn.load import load
from coursework.tests.conftest import FIXTURES

CUTOFF = "2026-10-01"


def fixture():
    return load("standin", directory=FIXTURES)  # SYNTHETIC: hand-written fixture


def test_labels_and_eligibility():
    df = build(fixture(), CUTOFF).set_index("scout_id")
    assert df.loc["syn-s-0001", "churned"] == 0      # reported Oct 3 -> stayed
    assert df.loc["syn-s-0002", "churned"] == 1      # only a removed report, then Oct 25 (after 21 days)
    assert "syn-s-0003" not in df.index              # joined after the cutoff -> excluded


def test_no_leakage_post_cutoff_rows_do_not_change_features():
    data = fixture()
    full = build(data, CUTOFF)
    cut = pd.Timestamp(f"{CUTOFF} 12:00", tz="America/New_York")
    trimmed = dict(data)
    trimmed["reports"] = data["reports"][data["reports"]["ts"] < cut]
    trimmed["ledger"] = data["ledger"][data["ledger"]["ts"] < cut]
    trimmed["bounties"] = data["bounties"][~(data["bounties"]["claimed_at"] >= cut)]
    trimmed["rep_history"] = data["rep_history"][pd.to_datetime(data["rep_history"]["as_of_date"]) < pd.Timestamp(CUTOFF)]
    pd.testing.assert_frame_equal(full[FEATURES], build(trimmed, CUTOFF)[FEATURES])


def test_asof_reputation_not_final_snapshot():
    row = build(fixture(), CUTOFF).set_index("scout_id").loc["syn-s-0001"]
    assert row["reputation_asof"] == 0.60   # history row of Sep 30, not 0.90 (Oct 10) or 0.99 (syn_scouts)
    assert row["points_asof"] == 45 and row["points_total"] == 45
    assert row["bounties_claimed_28d"] == 1  # the Oct 3 claim is after the cutoff


def test_hand_computed_features():
    row = build(fixture(), CUTOFF).set_index("scout_id").loc["syn-s-0001"]
    assert row["reports_28d"] == 3 and row["reports_7d"] == 2          # Sep 10, 25, 27 (flagged counts)
    assert row["share_flagged_or_removed"] == 1 / 3
    assert row["share_saturday_reports"] == 1 / 3                      # 01:00 Sun Sep 27 = Sat night


def test_snapshot_columns_never_features():
    for col in ["reputation", "points", "level", "reports_count", "last_active_at"]:
        assert col not in FEATURES


def test_truth_table_only_in_evaluate_truth():
    churn_dir = Path(__file__).resolve().parents[1] / "churn"
    for path in churn_dir.glob("*.py"):
        if path.name in ("evaluate_truth.py", "make_standin_data.py"):
            continue  # the evaluator reads it; the stand-in generator writes it
        assert not re.search(r"truth", path.read_text()), f"{path.name} mentions the truth table"
