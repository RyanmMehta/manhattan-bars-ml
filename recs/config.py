"""Constants for recs. Values = CONTRACTS v2 §A / specs PRD §5 (placeholders until pilot data).

Do not tune locally: raise changes with specs.
"""
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
SEED = 42  # spec: CONTRACTS.md#B
DEMO_NOW = "2026-11-14T23:30:00-05:00"  # spec: CONTRACTS.md#B

# --- eligibility / decay -------------------------------------------------- spec: docs/specs/SCORING.md#5.1-5.2
CUTOFF_MINUTES = 180
FUTURE_SKEW_MINUTES = 2
HALF_LIFE_FAST = 30.0       # crowd, dancing, line_minutes
HALF_LIFE_SCOUT_SLOW = 60.0  # scout cover_usd, music_genre
HALF_LIFE_OPERATOR = 120.0  # operator cover/genres/dj

# --- weighting ------------------------------------------------------------ spec: docs/specs/SCORING.md#5.3
DEFAULT_REPUTATION = 0.5
REP_BASE = 0.25
REP_SLOPE = 0.75
UNVERIFIED_WEIGHT = 0.6
STATUS_WEIGHT = {"accepted": 1.0, "pending": 1.0, "disputed": 0.5, "flagged": 0.0, "removed": 0.0}
OPERATOR_WEIGHT = 0.8

# --- field estimates ------------------------------------------------------ spec: docs/specs/SCORING.md#5.4
MIN_FIELD_WEIGHT = 0.30
GENRE_SHARE_MIN = 0.30

# --- vibe ------------------------------------------------------------------ spec: docs/specs/SCORING.md#5.5
VIBE_WEIGHTS = {"crowd": 0.50, "dance": 0.35, "line": 0.15}
LINE_CAP_MINUTES = 30
VIBE_BANDS = [(0, 34, "Chill"), (35, 64, "Lively"), (65, 100, "Packed")]  # spec: CONTRACTS.md#J

# --- confidence ------------------------------------------------------------ spec: docs/specs/SCORING.md#5.6
CONF_K = 1.5
AGREE_SD_SCALE = 1.5
DIVERSE_SINGLE = 0.6
OPERATOR_ONLY_CONF_CAP = 0.25
DISPLAY_SHOW = 0.40
DISPLAY_LOW = 0.20
STALE_TAG_MINUTES = 60  # spec: CONTRACTS.md#J (frontend shows "stale")

# --- trend ----------------------------------------------------------------- spec: docs/specs/SCORING.md#5.7
TREND_RECENT_MIN = 30
TREND_PRIOR_MIN = 90
TREND_MIN_WEIGHT = 0.5
TREND_DELTA = 0.4

# --- match ----------------------------------------------------------------- spec: docs/specs/SCORING.md#5.10
MATCH_WEIGHTS = {
    "genre": 0.25, "dancing": 0.20, "crowd": 0.15, "line": 0.10,
    "cover": 0.10, "distance": 0.15, "group": 0.05,
}
UNKNOWN_SCORE = 0.4
STATIC_GENRE_SCORE = 0.6
RANK_BASE = 0.75
RANK_CONF = 0.25
MAX_REASONS = 3
# recs addition (CCR-D to specs, not in SCORING.md): demote venues whose KNOWN crowd/dancing contradict the request.
# energy_fit = weighted mean of the crowd and dancing component scores (known values only). Below ENERGY_FIT_MIN,
# rank_score is multiplied by (ENERGY_PENALTY_FLOOR + fit). match_score itself is unchanged (= specs oracle).
ENERGY_FIT_MIN = 0.5
ENERGY_PENALTY_FLOOR = 0.5

# --- routing --------------------------------------------------------------- spec: docs/specs/SCORING.md#5.12
WALK_KMH = 4.5
WALK_COST_PER_KM = 10.0
DEFAULT_DWELL_MIN = 60
DEFAULT_MAX_TOTAL_WALK_MIN = 30
ROUTING_CANDIDATES = 15

# --- shared genre vocabulary ----------------------------------------------- source: simulator/config/genres.json (live-sim)
GENRES = [
    "hip-hop", "r&b", "afrobeats", "latin", "reggaeton", "house", "techno", "edm", "disco",
    "pop", "top-40", "throwbacks", "indie", "rock", "punk", "jazz", "soul-funk",
]

# --- crowd-model split ------------------------------------------------------ spec: CONTRACTS.md#B
HOLDOUT_NIGHTS = ["2026-11-13", "2026-11-14"]
