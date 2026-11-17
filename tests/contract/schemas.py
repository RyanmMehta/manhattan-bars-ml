"""CONTRACTS.md (v1 + v2 amendments) transcribed as column sets and JSON schemas.

The one place tests read the contract from. Update only when CONTRACTS.md changes.
"""
NUM = {"type": ["number", "null"]}
NUM_REQ = {"type": "number"}
STR = {"type": ["string", "null"]}
STR_REQ = {"type": "string"}
INT01 = {"type": ["integer", "boolean"]}
SYN = {"type": ["integer", "boolean"]}

# --- SQLite tables in data/live_sim.db (CSV columns = SQLite columns) ---------------
APP_TABLES: dict[str, set[str]] = {
    "syn_venue_attributes": {"venue_id", "genres", "style", "has_dance_floor", "typical_cover_usd",
                             "capacity", "price_level", "is_claimed", "opening_hours", "is_synthetic"},
    "syn_scouts": {"scout_id", "display_name", "joined_at", "reputation", "points", "level",
                   "reports_count", "last_active_at", "is_synthetic"},
    "syn_users": {"user_id", "display_name", "home_lat", "home_lon", "prefs_json", "is_synthetic"},
    "syn_scout_reports": {"report_id", "venue_id", "scout_id", "ts", "crowd", "dancing", "line_minutes",
                          "cover_usd", "music_genre", "verified_presence", "status", "distance_m",
                          "is_synthetic"},
    "syn_venue_updates": {"update_id", "venue_id", "ts", "cover_usd", "dj", "genres", "event", "offer",
                          "offer_expires_at", "is_synthetic"},
    "syn_feedback": {"feedback_id", "user_id", "venue_id", "recommended_at", "visited", "rating",
                     "is_synthetic"},
    "syn_bounties": {"bounty_id", "venue_id", "created_at", "points", "reason", "claimed_by",
                     "expires_at", "claimed_at", "is_synthetic"},
    "syn_venue_events": {"event_id", "venue_id", "ts", "event_type", "user_id", "is_synthetic"},
    "syn_disputes": {"dispute_id", "report_id", "opened_by", "reason", "opened_at", "status",
                     "resolved_at", "is_synthetic"},
    "syn_points_ledger": {"entry_id", "scout_id", "report_id", "bounty_id", "points", "reason", "ts",
                          "is_synthetic"},
    "syn_scout_reputation_history": {"scout_id", "as_of_date", "reputation", "points", "level",
                                     "is_synthetic"},
}
EVAL_ONLY_TABLES: dict[str, set[str]] = {
    "syn_true_state": {"venue_id", "ts", "crowd_true", "dancing_true", "line_minutes_true",
                       "cover_usd_true", "genre_true", "occupancy", "is_synthetic"},
    "syn_scout_truth": {"scout_id", "archetype", "home_venue_id", "true_accuracy", "cohort_week",
                        "churned_at", "is_synthetic"},
}
PRIMARY_KEYS = {
    "syn_scouts": "scout_id", "syn_users": "user_id", "syn_scout_reports": "report_id",
    "syn_venue_updates": "update_id", "syn_feedback": "feedback_id", "syn_bounties": "bounty_id",
    "syn_venue_events": "event_id", "syn_disputes": "dispute_id", "syn_points_ledger": "entry_id",
}
REAL_TWINS = ["scout_reports", "venue_updates", "venue_events", "feedback", "bounties", "disputes",
              "points_ledger"]
REPORT_STATUS = {"pending", "accepted", "flagged", "disputed", "removed"}
EVENT_TYPES = {"view", "tap", "save", "recommend_impression"}
STYLES = {"dive", "cocktail", "club", "lounge", "pub", "restaurant-bar"}
ARCHETYPES = {"honest", "casual", "sloppy", "gamer", "shill"}
SNAPSHOT_COLUMNS = {"venue_id", "snapshot_ts", "crowd", "dancing", "line_minutes", "vibe_score",
                    "confidence", "n_reports", "is_synthetic"}

# --- JSON objects ---------------------------------------------------------------------
LIVE_STATE = {
    "type": "object",
    "required": ["venue_id", "crowd", "dancing", "line_minutes", "cover_usd", "music_genres",
                 "vibe_score", "confidence", "freshness_minutes", "n_reports", "trend", "sources",
                 "is_synthetic"],
    "properties": {
        "venue_id": STR_REQ, "crowd": NUM, "dancing": NUM, "line_minutes": NUM, "cover_usd": NUM,
        "music_genres": {"type": ["array", "null"], "items": {"type": "string"}},
        "vibe_score": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
        "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "freshness_minutes": NUM, "n_reports": {"type": "integer", "minimum": 0},
        "trend": {"enum": ["rising", "steady", "falling", None]},
        "sources": {"type": "array", "items": {"type": "string"}},
        "display": {"enum": ["show", "low", "none"]},
        "predicted_crowd": NUM, "predicted_source": STR,
        "is_synthetic": SYN,
    },
}
RECOMMENDATION = {
    "type": "object",
    "required": ["venue_id", "name", "match_score", "vibe_score", "confidence", "distance_km",
                 "reasons", "missing", "excluded", "rank_score", "rank", "excluded_reason",
                 "is_synthetic"],
    "properties": {
        "venue_id": STR_REQ, "name": STR_REQ,
        "match_score": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
        "vibe_score": {"type": ["number", "null"], "minimum": 0, "maximum": 100},
        "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
        "distance_km": NUM, "reasons": {"type": "array", "items": {"type": "string"}},
        "missing": {"type": "array", "items": {"type": "string"}}, "excluded": {"type": "boolean"},
        "rank_score": NUM, "rank": {"type": ["integer", "null"]}, "excluded_reason": STR,
        "cluster_label": STR, "complaint_risk": {"type": ["number", "object", "null"]}, "is_synthetic": SYN,
    },
}
PLAN_STOP = {
    "type": "object",
    "required": ["order", "venue_id", "name", "lat", "lon", "arrive_at", "leave_at",
                 "walk_minutes_from_prev", "distance_km", "expected_vibe", "match_score", "confidence",
                 "reasons"],
}
VENUE_CARD = {
    "type": "object",
    "required": ["venue_id", "name", "display_name", "style", "genres", "price_level",
                 "typical_cover_usd", "lat", "lon", "opening_hours", "is_claimed", "state",
                 "complaint_risk", "is_synthetic"],
    "properties": {"venue_id": STR_REQ, "genres": {"type": "array"}, "lat": NUM_REQ, "lon": NUM_REQ,
                   "state": {"type": ["object", "null"]}, "is_synthetic": SYN},
}
VENUE_DETAIL = {"type": "object", "required": ["venue", "state", "recent_reports", "offers"]}
LEADERBOARD_ROW = {"type": "object", "required": ["rank", "scout_id", "display_name", "level", "points",
                                                   "points_week", "reputation", "is_synthetic"]}
BOUNTY_ROW = {"type": "object", "required": sorted(APP_TABLES["syn_bounties"] | {"venue_name"})}
OWNER_DASHBOARD = {
    "type": "object",
    "required": ["venue_id", "views", "taps", "saves", "reports_tonight", "rec_appearances",
                 "demand_by_hour", "is_synthetic"],
    "properties": {"demand_by_hour": {"type": "array", "items": {"type": "object", "required": ["hour", "value"]}}},
}
HEATMAP_ITEM = {"type": "object", "required": ["venue_id", "lat", "lon", "vibe_score", "confidence",
                                                "n_reports", "is_synthetic"]}
HEALTH = {
    "type": "object", "required": ["ok", "recs", "data", "demo_now"],
    "properties": {"ok": {"const": True}, "recs": {"enum": ["real", "stub"]},
                   "data": {"enum": ["synthetic", "real", "mixed"]}, "demo_now": STR},
}
REPORT_CREATED = {"type": "object", "required": ["report_id", "ts", "status", "points_pending"]}
LOGIN = {"type": "object", "required": ["token"]}
ERROR = {
    "type": "object", "required": ["error"],
    "properties": {"error": {"type": "object", "required": ["code", "message", "details"]}},
}
