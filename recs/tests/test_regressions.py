"""Regression tests for bugs found in live testing."""
# SYNTHETIC: hand-built venue states (shape of live-sim seed-42 data at DEMO_NOW).
from recs import live_state, scoring

from .conftest import NOW

PREFS = {"genres": ["hip-hop", "r&b"], "want_dancing": True, "crowd_pref": 4, "max_cover_usd": 20,
         "max_line_minutes": 15, "max_distance_km": 1.5, "lat": 40.7203, "lon": -73.9881, "group_size": 4}


def _st(vid, **kw):
    s = live_state.empty_state(vid)
    s.update({"n_reports": 5, "freshness_minutes": 1, "sources": ["scout"], "display": "show", **kw})
    return s


def test_confirmed_empty_bar_does_not_top_crowd4_dancing_request():
    """Bug (frontend, Nov 17): Brick (crowd 1.0, dancing 0, vibe 0, conf 0.75, R&B, no line/cover) ranked #1 for a
    'hip-hop/r&b, want dancing, crowd 4' group because genre+line+cover+distance+group (65% of match weight) reward
    an empty bar, and its high confidence lifted rank_score above livelier, less-certain venues."""
    venues = [
        {"venue_id": "syn-brick", "name": "Syn Brick", "lat": 40.7230, "lon": -73.9881, "capacity": 120},
        {"venue_id": "syn-hsh", "name": "Syn Home Sweet Home", "lat": 40.7239, "lon": -73.9881, "capacity": 120},
        {"venue_id": "syn-mayfly", "name": "Syn Mayfly", "lat": 40.7230, "lon": -73.9881, "capacity": 120},
    ]
    states = [
        _st("syn-brick", crowd=1.0, dancing=0.0, line_minutes=0, cover_usd=0, music_genres=["r&b"], vibe_score=0,
            confidence=0.75),
        _st("syn-hsh", crowd=2.9, dancing=None, line_minutes=None, cover_usd=None, music_genres=["r&b"], vibe_score=26,
            confidence=0.36, display="low"),
        _st("syn-mayfly", crowd=4.4, dancing=1.5, line_minutes=10, cover_usd=None, music_genres=["house"], vibe_score=78,
            confidence=0.50),
    ]
    recs = scoring.recommend(PREFS, states, venues, NOW)
    assert recs[0]["venue_id"] != "syn-brick"
    brick = next(r for r in recs if r["venue_id"] == "syn-brick")
    assert brick["rank"] == 3
    # match_score is unchanged (= specs oracle, mid-60s); only rank_score is demoted
    assert 60 <= brick["match_score"] <= 70
    assert brick["rank_score"] < 0.7 * brick["match_score"] * (0.75 + 0.25 * 0.75)
    assert not any("Dancing" in x or "Crowd" in x for x in brick["reasons"])


def test_energy_penalty_never_triggers_on_unknowns():
    s = live_state.empty_state("v")
    comps = scoring.components(PREFS, s, {"venue_id": "v"}, 0.3)
    assert scoring.energy_penalty(comps) == 1.0


def test_energy_penalty_not_applied_when_close():
    s = _st("v", crowd=3.8, dancing=1.5)
    assert scoring.energy_penalty(scoring.components(PREFS, s, {"venue_id": "v"}, 0.3)) == 1.0
    p = dict(PREFS, want_dancing=False, crowd_pref=1)
    quiet = _st("v", crowd=1.0, dancing=0.0)
    assert scoring.energy_penalty(scoring.components(p, quiet, {"venue_id": "v"}, 0.3)) == 1.0  # quiet wanted


def test_cluster_label_is_short_and_description_kept():
    from recs import clustering
    a = clustering.assignments()
    if a.empty:
        return
    assert a["cluster_label"].str.len().max() <= 40
    assert "cluster_description" in a.columns and (a["cluster_label"] != a["cluster_description"]).all()
