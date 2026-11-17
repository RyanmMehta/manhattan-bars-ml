"""Pydantic models with exact CONTRACTS.md field names (+ v2 §F/§G); feed /openapi.json."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Out(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Health(Out):
    ok: bool
    recs: Literal["real", "stub"]
    data: Literal["synthetic", "real", "mixed"]
    demo_now: str | None
    is_synthetic: bool


class LiveState(Out):
    venue_id: str
    crowd: float | None = None
    dancing: float | None = None
    line_minutes: int | None = None
    cover_usd: float | None = None
    music_genres: list[str] | None = None
    vibe_score: int | None = None
    confidence: float | None = None
    freshness_minutes: int | None = None
    n_reports: int = 0
    trend: Literal["rising", "steady", "falling"] | None = None
    sources: list[str] = []
    display: Literal["show", "low", "none"] | None = None
    predicted_crowd: float | None = None
    predicted_source: str | None = None
    is_synthetic: bool = False


class ComplaintRisk(Out):
    label: str
    noise_complaints_3y: int | None
    level: Literal["low", "medium", "high"] | None
    score: float | None = None  # recs' modelled risk (0-1) when recs supplies it


class VenueCard(Out):
    venue_id: str
    name: str
    display_name: str
    address: str | None = None
    neighborhood: str | None = None
    style: str | None
    genres: list[str]
    price_level: int | None
    typical_cover_usd: float | None
    lat: float
    lon: float
    distance_km: float | None = None
    opening_hours: str | None
    is_claimed: bool | None
    state: LiveState
    complaint_risk: ComplaintRisk
    is_synthetic: bool


class ReportOut(Out):
    report_id: str
    venue_id: str
    scout_id: str
    scout_display_name: str | None
    reputation: float | None
    ts: str
    crowd: int | None
    dancing: int | None
    line_minutes: int | None
    cover_usd: float | None
    music_genre: str | None
    verified_presence: int
    status: str
    is_synthetic: bool


class UpdateOut(Out):
    update_id: str
    venue_id: str
    ts: str
    cover_usd: float | None = None
    dj: str | None = None
    genres: str | None = None
    event: str | None = None
    offer: str | None = None
    offer_expires_at: str | None = None
    is_synthetic: bool


class VenueDetail(Out):
    venue: VenueCard
    state: LiveState
    recent_reports: list[ReportOut]
    offers: list[UpdateOut]
    is_synthetic: bool


GenreSlug = str


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    venue_id: str
    crowd: int = Field(ge=1, le=5)
    dancing: int = Field(ge=0, le=2)
    line_minutes: int = Field(ge=0, le=180)
    cover_usd: float | None = Field(default=None, ge=0, le=200)
    music_genre: GenreSlug | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)


class ReportCreated(Out):
    report_id: str
    ts: str
    status: str
    points_pending: int
    verified_presence: int
    distance_m: int | None
    is_synthetic: bool = False


class Preferences(BaseModel):
    model_config = ConfigDict(extra="ignore")
    genres: list[str] | None = None
    want_dancing: bool | None = None
    crowd_pref: float | None = Field(default=None, ge=1, le=5)
    max_cover_usd: float | None = Field(default=None, ge=0, le=500)
    max_line_minutes: int | None = Field(default=None, ge=0, le=300)
    max_distance_km: float | None = Field(default=None, gt=0, le=50)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    group_size: int | None = Field(default=None, ge=1, le=50)
    start_time: str | None = None
    dwell_minutes: int | None = Field(default=None, ge=10, le=240)
    max_total_walk_minutes: int | None = Field(default=None, ge=0, le=240)
    exclude_venue_ids: list[str] | None = None
    launch_only: bool = True


class PlanNightIn(Preferences):
    n_stops: int = Field(default=3, ge=1, le=5)


class Recommendation(Out):
    venue_id: str
    name: str
    match_score: int
    vibe_score: int | None
    confidence: float | None
    distance_km: float | None
    reasons: list[str]
    missing: list[str]
    excluded: bool
    excluded_reason: str | None = None
    rank_score: float
    rank: int
    cluster_label: str | None = None
    complaint_risk: ComplaintRisk | None = None
    is_synthetic: bool

    @field_validator("match_score", mode="before")
    @classmethod
    def _round(cls, v: float) -> int:
        return int(round(v))


class Stop(Out):
    order: int
    venue_id: str
    name: str
    lat: float
    lon: float
    arrive_at: str
    leave_at: str
    walk_minutes_from_prev: float
    distance_km: float | None
    expected_vibe: float | None
    match_score: float | None
    confidence: float | None
    reasons: list[str]
    is_synthetic: bool = False


class LeaderRow(Out):
    rank: int
    scout_id: str
    display_name: str
    level: str
    points: int
    points_week: int
    reputation: float
    is_synthetic: bool


class BountyRow(Out):
    bounty_id: str
    venue_id: str
    venue_name: str | None
    created_at: str
    points: int
    reason: str | None
    claimed_by: str | None
    expires_at: str | None
    claimed_at: str | None
    is_synthetic: bool


class HourValue(Out):
    hour: int
    value: int


class OwnerDashboard(Out):
    venue_id: str
    views: int
    taps: int
    saves: int
    reports_tonight: int
    rec_appearances: int
    demand_by_hour: list[HourValue]
    is_synthetic: bool


class OwnerUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cover_usd: float | None = Field(default=None, ge=0, le=500)
    dj: str | None = Field(default=None, max_length=120)
    genres: list[str] | str | None = None
    event: str | None = Field(default=None, max_length=200)
    offer: str | None = Field(default=None, max_length=200)
    offer_expires_at: str | None = None


class HeatCell(Out):
    venue_id: str
    lat: float
    lon: float
    hour: int | None = None
    vibe_score: int | None
    confidence: float | None
    n_reports: int
    is_synthetic: bool


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=80)
    role: Literal["user", "scout", "owner"]
    venue_id: str | None = None


class LoginOut(Out):
    token: str
    role: str
    user_id: str | None = None
    scout_id: str | None = None
    venue_id: str | None = None
    is_synthetic: bool = False


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: str | None = None
    venue_id: str
    visited: int = Field(ge=0, le=1)
    rating: int | None = Field(default=None, ge=1, le=5)


class FeedbackOut(Out):
    feedback_id: str
    user_id: str
    venue_id: str
    recommended_at: str | None
    visited: int
    rating: int | None
    is_synthetic: bool = False


class ErrorBody(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
