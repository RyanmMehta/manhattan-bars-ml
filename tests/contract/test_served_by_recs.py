"""/api/recommend and /api/plan-night are served by recs, with no stub or validation fallback,
and the demo-night top pick for the contract prefs is a lively venue (master request, ml-recs 48d4ace)."""
from __future__ import annotations

import os

import pytest

from tests.contract.constants import DEFAULT_PREFS, DEMO_NOW

NOW = {"now": DEMO_NOW}


@pytest.fixture
def stub_calls(clean_api, monkeypatch):
    if os.environ.get("API_URL"):
        pytest.skip("in-process only (needs to patch the backend's stub engine)")
    from backend.app.engine import stub
    calls: list[str] = []
    for name in ("compute", "compute_all", "recommend", "plan_night"):
        orig = getattr(stub.StubEngine, name, None)
        if orig is None:
            continue

        def spy(self, *a, _n=name, _o=orig, **k):
            calls.append(_n)
            return _o(self, *a, **k)
        monkeypatch.setattr(stub.StubEngine, name, spy)
    return calls


def test_recommend_and_plan_served_by_recs(clean_api, stub_calls):
    api = clean_api
    assert api.get("/api/health").json()["recs"] == "real"
    r = api.post("/api/recommend", params=NOW, json=DEFAULT_PREFS)
    assert r.status_code == 200, r.text
    p = api.post("/api/plan-night", params=NOW, json={**DEFAULT_PREFS, "n_stops": 3})
    assert p.status_code == 200, p.text
    engine = api.app.state.ctx.engine
    assert getattr(engine, "last_served", "recs") == "recs"
    assert stub_calls == [], f"stub fallback used for: {sorted(set(stub_calls))}"


def test_top_pick_is_lively(api):
    """Hip-hop/r&b + dancing + crowd 4 at DEMO_NOW: #1 must not be a vibe < 35 ("Chill") venue."""
    out = api.post("/api/recommend", params=NOW, json=DEFAULT_PREFS).json()
    top = next(r for r in out if not r["excluded"])
    assert top["vibe_score"] is not None and top["vibe_score"] >= 35, top
