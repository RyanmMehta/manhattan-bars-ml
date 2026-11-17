"""All configuration. Nothing else reads os.environ (RULES §4)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

# ---- Scoring constants: SPEC(v2 §A) / specs PRD §5 (placeholders until pilot data) ----
HALF_LIFE_ENERGY_MIN = 30.0  # SPEC(v2 §A) crowd / dancing / line
HALF_LIFE_SCOUT_COVER_GENRE_MIN = 60.0  # SPEC(v2 §A)
HALF_LIFE_OPERATOR_MIN = 120.0  # SPEC(v2 §A) operator cover / genres / dj
INPUT_CUTOFF_MIN = 180.0  # SPEC(v2 §A)
FUTURE_SKEW_MIN = 2.0  # SPEC(v2 §A) ts > now + 2 min ignored
NEW_SCOUT_REPUTATION = 0.5  # SPEC(v2 §A)
UNVERIFIED_WEIGHT = 0.6  # SPEC(v2 §A)
DISPUTED_WEIGHT = 0.5  # SPEC(specs §5.3)
OPERATOR_SOURCE_WEIGHT = 0.8  # SPEC(specs §5.3)
CONFIDENCE_K = 1.5  # SPEC(v2 §A)
DISPLAY_SHOW = 0.40  # SPEC(v2 §A)
DISPLAY_LOW = 0.20  # SPEC(v2 §A)
UNKNOWN_COMPONENT = 0.4  # SPEC(v2 §A)
PRESENCE_RADIUS_M = 150  # SPEC(v2 §A)
MIN_FIELD_WEIGHT = 0.30  # SPEC(specs §5.4)
GENRE_SHARE_MIN = 0.30  # SPEC(specs §5.4)
VIBE_WEIGHTS = {"crowd": 0.50, "dance": 0.35, "line": 0.15}  # SPEC(specs §5.5)
MATCH_WEIGHTS = {  # SPEC(specs §5.10)
    "genre": 0.25,
    "dancing": 0.20,
    "crowd": 0.15,
    "line": 0.10,
    "cover": 0.10,
    "distance": 0.15,
    "group": 0.05,
}
ENERGY_FIT_MIN = 0.5  # SPEC(contracts c3fd169) energy-contradiction penalty threshold
ENERGY_PENALTY_FLOOR = 0.5  # SPEC(contracts c3fd169) rank_score *= floor + fit
TREND_DELTA = 0.4  # SPEC(v2 §A)
TREND_MIN_WEIGHT = 0.5  # SPEC(specs §5.7)
WALK_KMH = 4.5  # SPEC(specs §5.12)

# ---- Values specs has not fixed yet ----
POINTS_BASE = 10  # PLACEHOLDER(specs): specs §7.2 accepted-report points
POINTS_VERIFIED = 5  # PLACEHOLDER(specs): specs §7.2 verified-presence bonus
POINTS_FIRST_TONIGHT = 5  # PLACEHOLDER(specs): specs §7.2 first report at venue tonight
REPORT_RATE_LIMIT_MIN = 15  # PLACEHOLDER(specs): same scout + venue once per N minutes
LEVELS = [(1500, "Legend"), (500, "Insider"), (100, "Regular"), (0, "Rookie")]  # PLACEHOLDER
NOISE_RISK_BANDS = (25, 100)  # PLACEHOLDER(specs): low < 25 <= medium < 100 <= high
NIGHT_START_HOUR = 18  # owner dashboard counts since 18:00 ET of the current night
HEATMAP_HOURS = [20, 21, 22, 23, 0, 1, 2, 3]  # v2 §J


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", case_sensitive=False)

    database_url: str = f"sqlite:///{BACKEND_DIR / 'app.db'}"
    live_sim_db: str = str(REPO_ROOT / "data" / "live_sim.db")
    include_synthetic: bool = True
    demo_now: str | None = None
    cors_origins: str = "http://localhost:5173,https://nightlife-autopilot.vercel.app"
    feature_routing: bool = True
    feature_heatmap: bool = True

    public_db_path: str = str(REPO_ROOT / "data" / "manhattan_bars.db")
    launch_venues_csv: str = str(REPO_ROOT / "data" / "launch_venues.csv")
    launch_venues_full_csv: str = str(REPO_ROOT / "data" / "launch_venues_full.csv")
    manual_attributes_csv: str = str(REPO_ROOT / "data" / "venue_attributes_manual.csv")
    genres_json: str = str(REPO_ROOT / "simulator" / "config" / "genres.json")
    allow_fixture_sim: bool = True
    fixture_sim_db: str = str(
        BACKEND_DIR / "tests" / "fixtures" / "synthetic" / "fixture_live_sim.db"
    )
    demo_auth: bool = True
    admin_token: str | None = None
    recs_mode: str = "auto"  # auto | recs | stub
    log_level: str = "INFO"
    allow_write_now: bool = False

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
