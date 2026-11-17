"""Golden vectors from specs PRD §5.8 (G1) and §5.10 (G5)."""

from datetime import datetime, timedelta

from app.timeutil import NY

NOW = datetime(2026, 11, 14, 23, 30, tzinfo=NY)
VENUE = "0370-24-138636"

G1_REPORTS = [
    {"report_id": f"g1-{i}", "venue_id": VENUE, "scout_id": f"s{i}", "reputation": 0.8,
     "verified_presence": 1, "status": "accepted", "ts": (NOW - timedelta(minutes=age)).isoformat(),
     "crowd": c, "dancing": d, "line_minutes": ln, "cover_usd": None, "music_genre": None,
     "is_synthetic": 1}
    for i, (age, c, d, ln) in enumerate([(5, 4, 2, 10), (12, 4, 1, 15), (20, 3, 1, 10), (40, 4, 2, 5)])
]
G1_EXPECTED = {"vibe_score": 65, "confidence": 0.67}

PREFS = {
    "genres": ["hip-hop", "r&b"], "want_dancing": True, "crowd_pref": 4, "max_cover_usd": 20,
    "max_line_minutes": 15, "max_distance_km": 1.5, "lat": 40.7203, "lon": -73.9881,
    "group_size": 4,
}
G5_EXPECTED = {"match_score": 83, "rank_score": 76}
