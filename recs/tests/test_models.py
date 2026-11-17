# SYNTHETIC: crowd-model tests run on recs' stub generator (live-sim's data/live_sim.db replaces it).
import re
from pathlib import Path

import pandas as pd
import pytest

from recs import chain, crowd_model, data, live_state
from recs.synthetic import stub_nights

PKG = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def tables():
    return stub_nights.generate(data.launch_venues())


def test_stub_deterministic(tables):
    again = stub_nights.generate(data.launch_venues())
    pd.testing.assert_frame_equal(tables["syn_scout_reports"], again["syn_scout_reports"])
    assert (tables["syn_scout_reports"]["is_synthetic"] == 1).all()
    assert tables["syn_scout_reports"]["report_id"].str.startswith("syn-r-").all()
    assert len(stub_nights.nights()) == 36


def test_build_table(tables):
    df = crowd_model.build_table(tables)
    assert {"venue_id", "night", "slot", "crowd", "w"} <= set(df.columns)
    assert df["slot"].between(0, 6).all() and df["crowd"].between(1, 5).all()
    assert not {"crowd_true", "archetype", "true_accuracy"} & set(df.columns)


def test_future_reputation_does_not_change_training_table(tables):
    a = crowd_model.build_table(tables)
    t2 = dict(tables)
    h = tables["syn_scout_reputation_history"].copy()
    future = h["as_of_date"] > "2026-10-01"
    h.loc[future, "reputation"] = 0.0
    t2["syn_scout_reputation_history"] = h
    b = crowd_model.build_table(t2)
    early = a["night"] <= "2026-09-30"
    pd.testing.assert_frame_equal(a[early].reset_index(drop=True), b[b["night"] <= "2026-09-30"].reset_index(drop=True))
    # and final syn_scouts.reputation is never used
    t3 = dict(tables, syn_scouts=tables["syn_scouts"].assign(reputation=0.0))
    pd.testing.assert_frame_equal(a, crowd_model.build_table(t3))


def test_model_beats_baseline_on_holdout(tables):
    df = crowd_model.build_table(tables)
    hold = ["2026-11-13", "2026-11-14"]
    tr, te = df[~df["night"].isin(hold)], df[df["night"].isin(hold)]
    m = crowd_model.GBModel().fit(tr).predict(te)
    b = crowd_model.Baseline().fit(tr).predict(te)
    s = crowd_model.SlotMean().fit(tr).predict(te)
    mae = lambda p: abs(te["crowd"].to_numpy() - p).mean()  # noqa: E731
    assert mae(m) < mae(b) < mae(s)
    # test nights never in the venue target encoding
    gb = crowd_model.GBModel().fit(tr)
    assert gb.te == tr.groupby("venue_id")["crowd"].mean().to_dict()


def test_predict_unknown_and_missing_artifact(monkeypatch):
    out = crowd_model.predict(["no-such-venue"], ["2026-11-14T23:30:00-05:00"])
    assert out == [None]
    monkeypatch.setattr(crowd_model, "_load", lambda: None)
    assert crowd_model.predict(["x"], ["2026-11-14T23:30:00-05:00"]) == [None]
    assert crowd_model.slot_of("2026-11-14T12:00:00-05:00") is None


def test_snapshots_shape(tables):
    rep = tables["syn_scout_reports"].merge(tables["syn_scouts"][["scout_id", "reputation"]], on="scout_id")
    ids = list(data.launch_venues()["venue_id"])
    s = chain.snapshots(rep, tables["syn_venue_updates"], "2026-11-14T20:00:00-05:00", "2026-11-15T03:00:00-05:00",
                        venue_ids=ids)
    assert list(s.columns) == chain.SNAPSHOT_COLS
    assert (s.groupby("venue_id").size() == 15).all() and len(s) == 15 * 35
    row = s[s["snapshot_ts"] == "2026-11-14T23:30:00-05:00"].set_index("venue_id")
    direct = {x["venue_id"]: x for x in live_state.compute_all(rep, tables["syn_venue_updates"], "2026-11-14T23:30:00-05:00",
                                                               venue_ids=ids)}
    for vid, r in row.iterrows():
        assert (None if pd.isna(r["vibe_score"]) else r["vibe_score"]) == direct[vid]["vibe_score"]
        assert r["confidence"] == direct[vid]["confidence"]


def test_no_truth_leak_in_library():
    allowed = {"crowd_model.py", "__main__.py", "chain.py", "stub_nights.py", "data.py"}
    pat = re.compile(r"syn_true_state|syn_scout_truth")
    for f in PKG.rglob("*.py"):
        if "tests" in f.parts:
            continue
        if pat.search(f.read_text()):
            assert f.name in allowed, f
    for f in ("live_state.py", "scoring.py", "routing.py", "reasons.py"):
        assert not pat.search((PKG / f).read_text())
    # in crowd_model only evaluate/_truth_by_slot/true_crowd_lookup touch truth; build_table never does
    src = (PKG / "crowd_model.py").read_text()
    body = src[src.index("def build_table"):src.index("# ---", src.index("def build_table"))]
    assert not pat.search(body)


def test_complaint_risk_not_in_scoring_paths():
    for f in ("live_state.py", "routing.py", "reasons.py"):
        assert "complaint_risk" not in (PKG / f).read_text()
    src = (PKG / "scoring.py").read_text()
    comp = src[src.index("def components"):src.index("def match_raw")]
    assert "complaint" not in comp


def test_synthetic_markers():
    for f in ("data.py", "chain.py", "crowd_model.py", "synthetic/stub_nights.py", "live_state.py"):
        assert "SYNTHETIC:" in (PKG / f).read_text(), f


@pytest.mark.db
@pytest.mark.skipif(not data.has_bars_db(), reason="needs data/manhattan_bars.db")
def test_clustering_and_complaint_risk_artifacts():
    from recs import clustering, complaint_risk
    a = clustering.assignments()
    launch = set(data.launch_venues()["venue_id"])
    assert launch <= set(a["venue_id"]) and a["cluster_label"].str.len().gt(0).all()
    sc = complaint_risk.scores()
    assert all(0 <= sc[v] <= 1 for v in launch)


@pytest.mark.db
@pytest.mark.skipif(not data.has_bars_db(), reason="needs data/manhattan_bars.db")
def test_clustering_deterministic():
    from recs import clustering
    a = clustering.fit(write=False)["_df"]["cluster_id"].tolist()
    b = clustering.fit(write=False)["_df"]["cluster_id"].tolist()
    assert a == b


def test_chain_run_under_5s():
    import time
    t = time.perf_counter()
    res = chain.run()
    assert time.perf_counter() - t < 5
    assert len(res["states"]) == 35 and res["recommendations"] and res["plan"]
