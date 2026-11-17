"""Build golden vectors G1–G8 (synthetic test fixtures) from hand-written inputs.

Inputs are defined here; `expected` blocks are computed by reference_scoring.py.
G1 and G5 were also checked by hand against PRD §5.8 / §5.10.
Writes docs/specs/golden_synthetic/G*.json and the bundle docs/specs/golden_vectors.json.

    python -I docs/specs/tools/build_golden.py      # (check_golden.py --regen calls this)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_scoring as R  # noqa: E402

SPECS = Path(__file__).resolve().parent.parent
OUT_DIR = SPECS / "golden_synthetic"
BUNDLE = SPECS / "golden_vectors.json"
NOW = "2026-11-14T23:30:00-05:00"  # DEMO_NOW (Contracts v2 §B)
CONTRACT_PREFS = {"genres": ["hip-hop", "r&b"], "want_dancing": True, "crowd_pref": 4,
                  "max_cover_usd": 20, "max_line_minutes": 15, "max_distance_km": 1.5,
                  "lat": 40.7203, "lon": -73.9881, "group_size": 4}

# SYNTHETIC: venue attributes (capacity, genres) imitate syn_venue_attributes; real
# source = data/venue_attributes_manual.csv once the team labels venues. ids/lat/lon are
# real rows of data/launch_venues.csv.
VENUES = {
    "HSH": {"venue_id": "0370-24-119240", "name": "HOME SWEET HOME, FIG19",
            "lat": 40.7194, "lon": -73.99319, "capacity": 120, "genres": "hip-hop|house"},
    "MEH": {"venue_id": "0370-23-127248", "name": "MEHANATA BULGARIAN BAR",
            "lat": 40.71943, "lon": -73.98868, "capacity": 150, "genres": None},
    "ATT": {"venue_id": "0370-24-138636", "name": "ATTABOY COCKTAILS LLC",
            "lat": 40.71893, "lon": -73.99157, "capacity": 40, "genres": "soul-funk|jazz"},
    "VER": {"venue_id": "0370-23-127506", "name": "VERLAINE",
            "lat": 40.71993, "lon": -73.98786, "capacity": 90, "genres": "pop|top-40"},
    "NUR": {"venue_id": "0370-23-139176", "name": "NURSE BETTIE",
            "lat": 40.7189, "lon": -73.9871, "capacity": 60, "genres": None},
    "DON": {"venue_id": "0370-24-136624", "name": "DONNYBROOK",
            "lat": 40.71999, "lon": -73.98461, "capacity": 100, "genres": "rock"},
    "SUB": {"venue_id": "0370-21-116653", "name": "SUBJECT",
            "lat": 40.7215, "lon": -73.98479, "capacity": 80, "genres": "hip-hop"},
    "MAY": {"venue_id": "0370-23-138427", "name": "MAYFLY",
            "lat": 40.72162, "lon": -73.98457, "capacity": 70, "genres": None},
}


def ts(minutes_ago: float) -> str:
    """ISO timestamp `minutes_ago` before DEMO_NOW (negative = future)."""
    t = datetime.fromisoformat(NOW) - timedelta(minutes=minutes_ago)
    return t.isoformat()


class Ids:
    """Sequential synthetic ids (syn-r-000001, syn-u-000001)."""

    def __init__(self) -> None:
        self.r = 0
        self.u = 0

    def report(self) -> str:
        self.r += 1
        return f"syn-r-{self.r:06d}"

    def update(self) -> str:
        self.u += 1
        return f"syn-u-{self.u:06d}"


def report(ids: Ids, venue: str, scout: int, age: float, crowd: int, dancing: int, line: int,
           genre: str | None = None, cover: int | None = None, verified: int = 1,
           status: str = "accepted", rep: float = 0.8) -> dict:
    """One syn_scout_reports row (+ joined reputation)."""
    return {"report_id": ids.report(), "venue_id": VENUES[venue]["venue_id"],
            "scout_id": f"syn-s-{scout:04d}", "ts": ts(age), "crowd": crowd,
            "dancing": dancing, "line_minutes": line, "cover_usd": cover, "music_genre": genre,
            "verified_presence": verified, "distance_m": 40 if verified else None,
            "status": status, "reputation": rep, "is_synthetic": 1}


def update(ids: Ids, venue: str, age: float, cover: int | None, genres: str | None,
           dj: str | None = None) -> dict:
    """One syn_venue_updates row."""
    return {"update_id": ids.update(), "venue_id": VENUES[venue]["venue_id"], "ts": ts(age),
            "cover_usd": cover, "dj": dj, "genres": genres, "event": None, "offer": None,
            "offer_expires_at": None, "is_synthetic": 1}


def g1_reports(ids: Ids, shift: float = 0.0) -> list[dict]:
    """PRD §5.8 worked example: 4 scouts, r=0.8, verified, ages 5/12/20/40."""
    rows = [(1, 5, 4, 2, 10), (2, 12, 4, 1, 15), (3, 20, 3, 1, 10), (4, 40, 4, 2, 5)]
    return [report(ids, "HSH", s, a + shift, c, d, l, genre="hip-hop") for s, a, c, d, l in rows]


def vector_inputs() -> list[dict]:
    """Hand-written inputs for G1–G8."""
    v = []
    i = Ids()
    v.append(dict(id="G1", name="G1_normal_four_scouts", venues=["HSH"], prefs=None,
                  description="4 fresh agreeing scouts (PRD §5.8). Expect vibe 65 Packed, conf 0.67, show.",
                  reports=g1_reports(i), updates=[], hand_checked=True))
    i = Ids()
    reps = g1_reports(i, shift=120) + [report(i, "HSH", 5, 200, 5, 2, 30, genre="techno")]
    v.append(dict(id="G2", name="G2_stale_reports", venues=["HSH"], prefs=None,
                  description="G1 aged +120 min plus one 200-min report (ignored: > cutoff). Crowd too thin → vibe null, conf < 0.20, display none, stale.",
                  reports=reps, updates=[], hand_checked=False))
    i = Ids()
    reps = [report(i, "HSH", 7, a, 4, 1, 10, genre="house") for a in (5, 15, 25)]
    v.append(dict(id="G3", name="G3_single_scout", venues=["HSH"], prefs=None,
                  description="3 reports from one scout: diverse = 0.6 caps confidence.",
                  reports=reps, updates=[], hand_checked=False))
    i = Ids()
    v.append(dict(id="G4", name="G4_operator_only", venues=["MEH"], prefs=CONTRACT_PREFS,
                  description="Operator update only (cover 20, hip-hop). vibe null, conf ≤ 0.25, display none; missing dancing/crowd entries.",
                  reports=[], updates=[update(i, "MEH", 10, 20, "hip-hop", dj="syn-DJ Nova")],
                  hand_checked=False))
    i = Ids()
    v.append(dict(id="G5", name="G5_match_contract_prefs", venues=["HSH"], prefs=CONTRACT_PREFS,
                  description="G1 + operator cover 15 + contract Preferences. Expect match 83, rank_score 76.2.",
                  reports=g1_reports(i), updates=[update(i, "HSH", 30, 15, "hip-hop")],
                  hand_checked=True))
    i = Ids()
    reps = [report(i, "ATT", 11, 8, 4, 1, 5, genre="hip-hop", cover=25),
            report(i, "ATT", 12, 15, 4, 2, 10, genre="hip-hop", cover=25),
            report(i, "VER", 13, 6, 3, 1, 5, genre="r&b"),
            report(i, "VER", 14, 14, 4, 0, 5, genre="r&b")]
    v.append(dict(id="G6", name="G6_exclusion_known_vs_unknown", venues=["ATT", "VER"],
                  prefs=CONTRACT_PREFS,
                  description="Known cover $25 > max $20 excludes ATT; VER cover unknown is NOT excluded and lists 'cover not reported tonight'.",
                  reports=reps, updates=[], hand_checked=False))
    i = Ids()
    reps = [report(i, "NUR", 21, 10, 4, 1, 10),
            report(i, "NUR", 22, 10, 2, 0, 0, status="disputed"),
            report(i, "NUR", 23, 5, 5, 2, 30, status="flagged"),
            report(i, "NUR", 24, -5, 1, 0, 0),
            report(i, "NUR", 25, 15, 3, 1, 5, verified=0, status="pending", rep=0.5),
            report(i, "NUR", 26, 3, 5, 2, 30, status="removed")]
    v.append(dict(id="G7", name="G7_disputed_and_flagged", venues=["NUR"], prefs=None,
                  description="accepted + disputed (×0.5) + flagged (0) + future-dated +5 min (ignored) + pending unverified (×0.6) + removed (0).",
                  reports=reps, updates=[], hand_checked=False))
    i = Ids()
    rising = [report(i, "DON", 31 + k, a, c, 1, 5) for k, (a, c) in
              enumerate([(5, 4), (10, 4), (20, 4), (40, 2), (50, 2), (60, 2)])]
    falling = [report(i, "SUB", 41 + k, a, c, 1, 5) for k, (a, c) in
               enumerate([(5, 2), (10, 2), (20, 2), (40, 4), (50, 4), (60, 4)])]
    thin = [report(i, "MAY", 51 + k, a, c, 1, 5) for k, (a, c) in
            enumerate([(5, 4), (10, 4), (20, 4), (80, 2)])]
    v.append(dict(id="G8", name="G8_trend_rising_falling", venues=["DON", "SUB", "MAY"], prefs=None,
                  description="Crowd 2→4 (rising), 4→2 (falling), thin prior window (null).",
                  reports=rising + falling + thin, updates=[], hand_checked=False))
    return v


def scouts_of(reports: list[dict]) -> list[dict]:
    """syn_scouts-like rows for the scouts used (reputation as of the report date)."""
    seen = {}
    for r in reports:
        seen[r["scout_id"]] = {"scout_id": r["scout_id"], "reputation": r["reputation"],
                               "is_synthetic": 1}
    return [seen[k] for k in sorted(seen)]


def build_vector(spec: dict) -> dict:
    """Attach venues, scouts and the oracle's expected outputs to one input spec."""
    venues = [VENUES[k] for k in spec["venues"]]
    vids = [x["venue_id"] for x in venues]
    states = R.compute_all(spec["reports"], spec["updates"], NOW, venue_ids=vids)
    debug = {s: R.compute_state(s, spec["reports"], spec["updates"], NOW, debug=True)["_debug"]
             for s in vids}
    recs = None
    if spec["prefs"] is not None:
        recs = R.recommend(spec["prefs"], states, venues, NOW, debug=True)
        for rec in recs:
            debug[rec["venue_id"]]["match_raw"] = rec.pop("_match_raw")
    return {
        "id": spec["id"], "name": spec["name"], "description": spec["description"],
        "is_synthetic": 1, "now": NOW, "hand_checked": spec["hand_checked"],
        "scouts": scouts_of(spec["reports"]), "reports": spec["reports"],
        "updates": spec["updates"],
        "venues": [{**x, "is_synthetic": 1} for x in venues], "prefs": spec["prefs"],
        "expected": {"states": states, "ui": {s["venue_id"]: R.ui_labels(s) for s in states},
                     "recommendations": recs, "debug": debug},
    }


def build_all() -> list[dict]:
    """All vectors, in id order."""
    return [build_vector(s) for s in vector_inputs()]


def dump(obj: object) -> str:
    """Canonical JSON text: 2-space indent, sorted keys, trailing newline."""
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def bundle(vectors: list[dict]) -> dict:
    """golden_vectors.json content."""
    return {"description": "Golden vectors G1–G8 for docs/specs/SCORING.md (synthetic test fixtures).",
            "is_synthetic": 1, "now": NOW, "parameters": R.P,
            "tolerance": {"vibe_score": 1, "confidence": 0.01, "match_score": 0,
                          "crowd": 0.05, "dancing": 0.05, "rank_score": 0.15},
            "vectors": vectors}


def write_all() -> None:
    """Write per-vector files and the bundle."""
    vectors = build_all()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for vec in vectors:
        # SYNTHETIC: hand-written fixture; stays synthetic (test data, not replaced)
        (OUT_DIR / f"{vec['name']}.json").write_text(dump(vec), encoding="utf-8")
    BUNDLE.write_text(dump(bundle(vectors)), encoding="utf-8")


if __name__ == "__main__":
    write_all()
    print(f"wrote {len(build_all())} vectors to {OUT_DIR} and {BUNDLE}")
