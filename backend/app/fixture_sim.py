"""Tiny deterministic stand-in for live-sim's data/live_sim.db (seed 42, one night:
Sat Nov 14 2026 20:00 -> Sun 03:00 ET). Dev/tests only (ALLOW_FIXTURE_SIM=1).
SYNTHETIC: replace with live-sim's data/live_sim.db, then with real app tables."""

import csv
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from .genres import VENDORED_GENRES
from .simdb import EXPECTED
from .timeutil import NY

NIGHT = datetime(2026, 11, 14, 20, 0, tzinfo=NY)
STYLES = ["dive", "cocktail", "club", "lounge", "pub", "restaurant-bar"]


def _iso(dt: datetime) -> str:
    return dt.astimezone(NY).isoformat(timespec="seconds")


def build_fixture_sim(out: str, launch_csv: str, seed: int = 42) -> str:
    rng = random.Random(seed)
    with open(launch_csv, newline="") as f:
        venues = [r["license_id"] for r in csv.DictReader(f)]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(out).with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    conn = sqlite3.connect(tmp)
    for table, cols in EXPECTED.items():
        conn.execute(f"CREATE TABLE {table} ({', '.join(cols)})")

    def ins(table: str, row: dict) -> None:
        cols = EXPECTED[table]
        conn.execute(
            f"INSERT INTO {table} VALUES ({','.join('?' * len(cols))})",
            [row.get(c) for c in cols],
        )

    for v in venues:
        ins("syn_venue_attributes", {
            "venue_id": v, "genres": "|".join(rng.sample(VENDORED_GENRES, 2)),
            "style": rng.choice(STYLES), "has_dance_floor": int(rng.random() < 0.3),
            "typical_cover_usd": rng.choice([0, 0, 0, 10, 15, 20]),
            "capacity": rng.choice([60, 80, 120, 150, 250]), "price_level": rng.randint(1, 4),
            "is_claimed": int(rng.random() < 0.2), "opening_hours": None, "is_synthetic": 1})

    scouts = [f"syn-s-{i:04d}" for i in range(1, 21)]
    reps = {}
    for i, s in enumerate(scouts):
        reps[s] = round(rng.uniform(0.3, 0.95), 2)
        pts = rng.randint(0, 900)
        ins("syn_scouts", {
            "scout_id": s, "display_name": f"Scout {i + 1}", "joined_at": _iso(NIGHT - timedelta(days=60)),
            "reputation": reps[s], "points": pts,
            "level": "Insider" if pts >= 500 else "Regular" if pts >= 100 else "Rookie",
            "reports_count": rng.randint(1, 80), "last_active_at": _iso(NIGHT), "is_synthetic": 1})
    for i in range(1, 6):
        ins("syn_users", {"user_id": f"syn-u-{i:04d}", "display_name": f"User {i}",
                          "home_lat": None, "home_lon": None, "prefs_json": "{}", "is_synthetic": 1})

    hot = venues[:12]
    n = 0
    for k in range(200):
        v = rng.choice(hot) if rng.random() < 0.8 else rng.choice(venues)
        ts = NIGHT + timedelta(minutes=rng.randint(0, 420))
        hour_boost = 1 if ts.hour >= 22 or ts.hour < 2 else 0
        s = rng.choice(scouts)
        n += 1
        ins("syn_scout_reports", {
            "report_id": f"syn-r-{n:06d}", "venue_id": v, "scout_id": s, "ts": _iso(ts),
            "crowd": min(5, rng.randint(2, 4) + hour_boost), "dancing": rng.randint(0, 2),
            "line_minutes": rng.choice([0, 5, 10, 15, 20, 30]),
            "cover_usd": rng.choice([None, None, 0, 10, 20]),
            "music_genre": rng.choice([None] + VENDORED_GENRES[:8]),
            "verified_presence": int(rng.random() < 0.7),
            "status": rng.choice(["accepted"] * 8 + ["pending", "flagged"]),
            "distance_m": rng.randint(5, 140), "is_synthetic": 1})
        ins("syn_points_ledger", {
            "entry_id": f"syn-p-{n:06d}", "scout_id": s, "report_id": f"syn-r-{n:06d}",
            "bounty_id": None, "points": 10, "reason": "report", "ts": _iso(ts), "is_synthetic": 1})

    for i in range(1, 16):
        v = rng.choice(hot)
        ts = NIGHT + timedelta(minutes=rng.randint(0, 300))
        offer = rng.random() < 0.5
        ins("syn_venue_updates", {
            "update_id": f"syn-vu-{i:04d}", "venue_id": v, "ts": _iso(ts),
            "cover_usd": rng.choice([None, 0, 10, 25]), "dj": rng.choice([None, "DJ Demo"]),
            "genres": "|".join(rng.sample(VENDORED_GENRES[:8], 1)), "event": None,
            "offer": "2-for-1 well drinks" if offer else None,
            "offer_expires_at": _iso(ts + timedelta(hours=3)) if offer else None, "is_synthetic": 1})

    for i in range(1, 6):
        created = NIGHT + timedelta(minutes=150 + 15 * i)
        ins("syn_bounties", {
            "bounty_id": f"syn-b-{i:04d}", "venue_id": venues[-i], "created_at": _iso(created),
            "points": 20 + 10 * (i % 3), "reason": "no fresh reports", "claimed_by": None,
            "expires_at": _iso(created + timedelta(minutes=90)), "claimed_at": None,
            "is_synthetic": 1})

    types = ["view"] * 5 + ["tap"] * 3 + ["save", "recommend_impression"]
    for i in range(1, 401):
        ts = NIGHT - timedelta(hours=1) + timedelta(minutes=rng.randint(0, 480))
        ins("syn_venue_events", {
            "event_id": f"syn-e-{i:06d}", "venue_id": rng.choice(venues), "ts": _iso(ts),
            "event_type": rng.choice(types), "user_id": None, "is_synthetic": 1})
    for i in range(1, 6):
        ins("syn_feedback", {
            "feedback_id": f"syn-f-{i:04d}", "user_id": f"syn-u-{i:04d}", "venue_id": hot[i],
            "recommended_at": _iso(NIGHT), "visited": 1, "rating": 4, "is_synthetic": 1})
    ins("syn_disputes", {
        "dispute_id": "syn-d-0001", "report_id": "syn-r-000001", "opened_by": "syn-u-0001",
        "reason": "wrong crowd", "opened_at": _iso(NIGHT + timedelta(hours=1)), "status": "open",
        "resolved_at": None, "is_synthetic": 1})
    conn.commit()
    conn.close()
    tmp.replace(out)
    return out
