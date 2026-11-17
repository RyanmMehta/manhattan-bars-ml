"""CONTRACTS.md v2 §A constants and §B demo time, transcribed once for tests."""
DEMO_NOW = "2026-11-14T23:30:00-05:00"
HALF_LIFE_CROWD_MIN = 30
HALF_LIFE_SCOUT_COVER_GENRE_MIN = 60
HALF_LIFE_OPERATOR_MIN = 120
INPUT_CUTOFF_MIN = 180
FUTURE_TOLERANCE_MIN = 2
UNVERIFIED_WEIGHT = 0.6
CONFIDENCE_K = 1.5
DISPLAY_SHOW = 0.40
DISPLAY_LOW = 0.20
UNKNOWN_COMPONENT = 0.4
PRESENCE_RADIUS_M = 150
TREND_DELTA = 0.4
GENRES = [
    "hip-hop", "r&b", "afrobeats", "latin", "reggaeton", "house", "techno", "edm", "disco",
    "pop", "top-40", "throwbacks", "indie", "rock", "punk", "jazz", "soul-funk",
]
# Golden vectors (specs): G1 vibe 65 / conf 0.67, G5 match 83.
G1 = {"vibe_score": 65, "confidence": 0.67}
G5 = {"match_score": 83}
VIBE_BANDS = [(0, 34, "Chill"), (35, 64, "Lively"), (65, 100, "Packed")]
DEFAULT_PREFS = {
    "genres": ["hip-hop", "r&b"], "want_dancing": True, "crowd_pref": 4, "max_cover_usd": 20,
    "max_line_minutes": 15, "max_distance_km": 1.5, "lat": 40.7203, "lon": -73.9881, "group_size": 4,
}
SIM_FIRST_NIGHT = "2026-08-27"
SIM_LAST_NIGHT = "2026-11-14"
SIM_NIGHTS = 36


def rep_weight(r: float) -> float:
    return 0.25 + 0.75 * r


def rank_score(match: float, conf: float) -> float:
    return match * (0.75 + 0.25 * conf)


def vibe_label(v):
    if v is None:
        return None
    for lo, hi, label in VIBE_BANDS:
        if lo <= v <= hi:
            return label
    return None
