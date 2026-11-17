"""Real app tables. Each mirrors its `syn_` twin column-for-column (v2 §E) so reads can
UNION ALL. Timestamps are ISO 8601 strings in America/New_York, exactly like the twins."""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    home_lat: Mapped[float | None] = mapped_column(Float)
    home_lon: Mapped[float | None] = mapped_column(Float)
    prefs_json: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class Scout(Base):
    __tablename__ = "scouts"
    scout_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    joined_at: Mapped[str] = mapped_column(String(40))
    reputation: Mapped[float] = mapped_column(Float, default=0.5)
    points: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[str] = mapped_column(String(40), default="Rookie")
    reports_count: Mapped[int] = mapped_column(Integer, default=0)
    last_active_at: Mapped[str | None] = mapped_column(String(40))
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class ApiToken(Base):
    __tablename__ = "api_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(16))
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[str] = mapped_column(String(40))
    revoked: Mapped[int] = mapped_column(Integer, default=0)


class ScoutReport(Base):
    __tablename__ = "scout_reports"
    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_id: Mapped[str] = mapped_column(String(32), index=True)
    scout_id: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[str] = mapped_column(String(40), index=True)
    crowd: Mapped[int] = mapped_column(Integer)
    dancing: Mapped[int] = mapped_column(Integer)
    line_minutes: Mapped[int] = mapped_column(Integer)
    cover_usd: Mapped[float | None] = mapped_column(Float)
    music_genre: Mapped[str | None] = mapped_column(String(40))
    verified_presence: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    distance_m: Mapped[int | None] = mapped_column(Integer)
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class VenueUpdate(Base):
    __tablename__ = "venue_updates"
    update_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_id: Mapped[str] = mapped_column(String(32), index=True)
    ts: Mapped[str] = mapped_column(String(40), index=True)
    cover_usd: Mapped[float | None] = mapped_column(Float)
    dj: Mapped[str | None] = mapped_column(String(120))
    genres: Mapped[str | None] = mapped_column(String(200))
    event: Mapped[str | None] = mapped_column(String(200))
    offer: Mapped[str | None] = mapped_column(String(200))
    offer_expires_at: Mapped[str | None] = mapped_column(String(40))
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class VenueEvent(Base):
    __tablename__ = "venue_events"
    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_id: Mapped[str] = mapped_column(String(32), index=True)
    ts: Mapped[str] = mapped_column(String(40), index=True)
    event_type: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[str | None] = mapped_column(String(64))
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class PointsLedger(Base):
    __tablename__ = "points_ledger"
    entry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scout_id: Mapped[str] = mapped_column(String(64), index=True)
    report_id: Mapped[str | None] = mapped_column(String(64))
    bounty_id: Mapped[str | None] = mapped_column(String(64))
    points: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(80))
    ts: Mapped[str] = mapped_column(String(40))
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class Bounty(Base):
    __tablename__ = "bounties"
    bounty_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    venue_id: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[str] = mapped_column(String(40))
    points: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(120))
    claimed_by: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[str | None] = mapped_column(String(40))
    claimed_at: Mapped[str | None] = mapped_column(String(40))
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class BountyClaim(Base):
    """Real claims of synthetic bounties (sim DB is read-only, so claims live here)."""

    __tablename__ = "bounty_claims"
    bounty_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claimed_by: Mapped[str] = mapped_column(String(64))
    claimed_at: Mapped[str] = mapped_column(String(40))
    report_id: Mapped[str] = mapped_column(String(64))


class Feedback(Base):
    __tablename__ = "feedback"
    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    venue_id: Mapped[str] = mapped_column(String(32))
    recommended_at: Mapped[str | None] = mapped_column(String(40))
    visited: Mapped[int] = mapped_column(Integer)
    rating: Mapped[int | None] = mapped_column(Integer)
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class Dispute(Base):
    __tablename__ = "disputes"
    dispute_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    report_id: Mapped[str] = mapped_column(String(64))
    opened_by: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(200))
    opened_at: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(16))
    resolved_at: Mapped[str | None] = mapped_column(String(40))
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)


class VenueAttributes(Base):
    __tablename__ = "venue_attributes"
    venue_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    genres: Mapped[str | None] = mapped_column(String(200))
    style: Mapped[str | None] = mapped_column(String(32))
    has_dance_floor: Mapped[int | None] = mapped_column(Integer)
    typical_cover_usd: Mapped[float | None] = mapped_column(Float)
    capacity: Mapped[int | None] = mapped_column(Integer)
    price_level: Mapped[int | None] = mapped_column(Integer)
    is_claimed: Mapped[int | None] = mapped_column(Integer)
    opening_hours: Mapped[str | None] = mapped_column(String(200))
    is_synthetic: Mapped[int] = mapped_column(Integer, default=0)
