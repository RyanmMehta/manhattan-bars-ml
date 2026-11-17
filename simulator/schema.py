"""Column lists, enums and checks for every live-sim table (CONTRACTS base + v2 §E + v2.2 §J).

Column order: contract base columns, then v2 additions, with `is_synthetic` always last.
"""
from __future__ import annotations

import pandas as pd

TABLES: dict[str, list[str]] = {
    "syn_venue_attributes": ["venue_id", "genres", "style", "has_dance_floor", "typical_cover_usd", "capacity",
                             "price_level", "is_claimed", "opening_hours", "is_synthetic"],
    "syn_scouts": ["scout_id", "display_name", "joined_at", "reputation", "points", "level", "reports_count",
                   "last_active_at", "is_synthetic"],
    "syn_users": ["user_id", "display_name", "home_lat", "home_lon", "prefs_json", "is_synthetic"],
    "syn_scout_reports": ["report_id", "venue_id", "scout_id", "ts", "crowd", "dancing", "line_minutes", "cover_usd",
                          "music_genre", "verified_presence", "status", "distance_m", "is_synthetic"],
    "syn_venue_updates": ["update_id", "venue_id", "ts", "cover_usd", "dj", "genres", "event", "offer",
                          "offer_expires_at", "is_synthetic"],
    "syn_feedback": ["feedback_id", "user_id", "venue_id", "recommended_at", "visited", "rating", "is_synthetic"],
    "syn_bounties": ["bounty_id", "venue_id", "created_at", "points", "reason", "claimed_by", "expires_at",
                     "claimed_at", "is_synthetic"],
    "syn_venue_events": ["event_id", "venue_id", "ts", "event_type", "user_id", "is_synthetic"],
    "syn_disputes": ["dispute_id", "report_id", "opened_by", "reason", "opened_at", "status", "resolved_at",
                     "is_synthetic"],
    "syn_points_ledger": ["entry_id", "scout_id", "report_id", "bounty_id", "points", "reason", "ts", "is_synthetic"],
    "syn_scout_reputation_history": ["scout_id", "as_of_date", "reputation", "points", "level", "is_synthetic"],
    "syn_true_state": ["venue_id", "ts", "crowd_true", "dancing_true", "line_minutes_true", "cover_usd_true",
                       "genre_true", "occupancy", "is_synthetic"],
    "syn_scout_truth": ["scout_id", "archetype", "home_venue_id", "true_accuracy", "cohort_week", "churned_at",
                        "is_synthetic"],
}
EVAL_ONLY = {"syn_true_state", "syn_scout_truth"}
SNAPSHOT_COLUMNS = ["venue_id", "snapshot_ts", "crowd", "dancing", "line_minutes", "vibe_score", "confidence",
                    "n_reports", "is_synthetic"]

STYLES = {"dive", "cocktail", "club", "lounge", "pub", "restaurant-bar"}
REPORT_STATUS_STORED = {"accepted", "flagged", "disputed", "removed"}
REPORT_STATUS = REPORT_STATUS_STORED | {"pending"}
EVENT_TYPES = {"view", "tap", "save", "recommend_impression"}
ARCHETYPES = {"honest", "casual", "sloppy", "gamer", "shill"}
DISPUTE_STATUS = {"open", "upheld", "rejected", "auto_rejected"}
ID_PREFIX = {"syn_scout_reports": ("report_id", "syn-r-"), "syn_scouts": ("scout_id", "syn-s-"),
             "syn_users": ("user_id", "syn-u-"), "syn_venue_updates": ("update_id", "syn-up-"),
             "syn_feedback": ("feedback_id", "syn-f-"), "syn_bounties": ("bounty_id", "syn-b-"),
             "syn_venue_events": ("event_id", "syn-e-"), "syn_disputes": ("dispute_id", "syn-d-"),
             "syn_points_ledger": ("entry_id", "syn-p-")}
RANGES = {("syn_scout_reports", "crowd"): (1, 5), ("syn_scout_reports", "dancing"): (0, 2),
          ("syn_scout_reports", "line_minutes"): (0, 240), ("syn_scouts", "reputation"): (0, 1),
          ("syn_venue_attributes", "price_level"): (1, 4), ("syn_feedback", "rating"): (1, 5),
          ("syn_true_state", "crowd_true"): (1, 5), ("syn_true_state", "dancing_true"): (0, 2)}
ENUMS = {("syn_venue_attributes", "style"): STYLES, ("syn_scout_reports", "status"): REPORT_STATUS_STORED,
         ("syn_venue_events", "event_type"): EVENT_TYPES, ("syn_scout_truth", "archetype"): ARCHETYPES,
         ("syn_disputes", "status"): DISPUTE_STATUS}
NOT_NULL = {"syn_scout_reports": ["report_id", "venue_id", "scout_id", "ts", "crowd", "verified_presence", "status"],
            "syn_bounties": ["bounty_id", "venue_id", "created_at", "points", "reason", "expires_at"],
            "syn_points_ledger": ["entry_id", "scout_id", "points", "reason", "ts"]}


def check(df: pd.DataFrame, table: str) -> list[str]:
    """Return a list of problems (empty = OK) for `df` against the `table` contract."""
    errs: list[str] = []
    cols = SNAPSHOT_COLUMNS if table == "demo_night_snapshots" else TABLES[table]
    if list(df.columns) != cols:
        return [f"{table}: columns {list(df.columns)} != {cols}"]
    if len(df) and not (df["is_synthetic"] == 1).all():
        errs.append(f"{table}: is_synthetic != 1")
    if table in ID_PREFIX:
        col, pre = ID_PREFIX[table]
        if not df[col].astype(str).str.startswith(pre).all():
            errs.append(f"{table}.{col}: ids must start with {pre}")
        if not df[col].is_unique:
            errs.append(f"{table}.{col}: duplicate ids")
    for (t, c), (lo, hi) in RANGES.items():
        if t == table:
            v = pd.to_numeric(df[c], errors="coerce").dropna()
            if len(v) and (v.min() < lo or v.max() > hi):
                errs.append(f"{table}.{c}: out of range [{lo},{hi}]")
    for (t, c), allowed in ENUMS.items():
        if t == table:
            bad = set(df[c].dropna().unique()) - allowed
            if bad:
                errs.append(f"{table}.{c}: bad values {sorted(bad)}")
    for c in NOT_NULL.get(table, []):
        if df[c].isna().any():
            errs.append(f"{table}.{c}: has nulls")
    return errs
