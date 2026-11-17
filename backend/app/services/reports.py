"""Scout vibe check write path: validation, distance_m, presence, rate limit, points, bounty."""

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config as C
from ..context import Ctx
from ..engine.geo import haversine_km
from ..errors import ApiError
from ..models import Bounty, BountyClaim, PointsLedger, Scout, ScoutReport
from ..repo import live
from ..schemas import ReportIn
from ..timeutil import night_start, parse_ts, to_ny_iso
from .auth import Principal


def level_for(points: int) -> str:
    return next(name for floor, name in C.LEVELS if points >= floor)


def create_report(s: Session, ctx: Ctx, p: Principal, body: ReportIn, now_q: str | None) -> dict:
    if p.role == "owner":
        if p.subject_id == body.venue_id:
            raise ApiError(403, "forbidden", "Owners cannot report their own venue")
        raise ApiError(403, "forbidden", "Owner accounts cannot submit scout reports")
    if p.role != "scout":
        raise ApiError(403, "forbidden", "Only scouts can submit reports")
    venue = ctx.catalog.by_id.get(body.venue_id)
    if venue is None or not venue["is_launch"]:
        raise ApiError(404, "not_found", f"Unknown launch venue {body.venue_id}")
    if body.music_genre is not None and body.music_genre not in ctx.genres:
        raise ApiError(422, "validation_error", f"music_genre must be one of {list(ctx.genres)}")
    scout = s.get(Scout, p.subject_id)
    if scout is None:
        raise ApiError(401, "unauthorized", "Scout not found")

    now = ctx.write_now(now_q)
    ts = to_ny_iso(now)
    recent = (
        s.execute(
            select(ScoutReport.ts).where(
                ScoutReport.scout_id == scout.scout_id, ScoutReport.venue_id == body.venue_id
            )
        )
        .scalars()
        .all()
    )
    limit = timedelta(minutes=C.REPORT_RATE_LIMIT_MIN)
    if any(abs(now - parse_ts(t)) < limit for t in recent):
        raise ApiError(
            429, "rate_limited", f"One report per venue every {C.REPORT_RATE_LIMIT_MIN} minutes"
        )

    distance_m = None
    if body.lat is not None and body.lon is not None:
        # Raw lat/lon are used only here and never stored or logged (v2 §A).
        distance_m = int(round(1000 * haversine_km(body.lat, body.lon, venue["lat"], venue["lon"])))
    verified = int(distance_m is not None and distance_m <= C.PRESENCE_RADIUS_M)

    first_tonight = not live.reports_window(s, ctx.src, night_start(now), now, [body.venue_id])
    bounties = live.open_bounties(s, ctx.src, now)
    rid = str(uuid.uuid4())
    s.add(
        ScoutReport(
            report_id=rid,
            venue_id=body.venue_id,
            scout_id=scout.scout_id,
            ts=ts,
            crowd=body.crowd,
            dancing=body.dancing,
            line_minutes=body.line_minutes,
            cover_usd=body.cover_usd,
            music_genre=body.music_genre,
            verified_presence=verified,
            status="pending",
            distance_m=distance_m,
            is_synthetic=0,
        )
    )

    entries = [(C.POINTS_BASE, "report", None)]
    if verified:
        entries.append((C.POINTS_VERIFIED, "verified_presence", None))
    if first_tonight:
        entries.append((C.POINTS_FIRST_TONIGHT, "first_report_tonight", None))
    for b in bounties:
        if b["venue_id"] == body.venue_id and verified:
            # Implicit claim by the first qualifying report (v2 §E). Synthetic bounties live in
            # the read-only sim DB, so their claim is recorded in bounty_claims.
            real = s.get(Bounty, b["bounty_id"])
            if real is not None:
                real.claimed_by, real.claimed_at = scout.scout_id, ts
            else:
                s.add(
                    BountyClaim(
                        bounty_id=b["bounty_id"],
                        claimed_by=scout.scout_id,
                        claimed_at=ts,
                        report_id=rid,
                    )
                )
            entries.append((int(b["points"]), "bounty", b["bounty_id"]))
            break
    for pts, reason, bounty_id in entries:
        s.add(
            PointsLedger(
                entry_id=str(uuid.uuid4()),
                scout_id=scout.scout_id,
                report_id=rid,
                bounty_id=bounty_id,
                points=pts,
                reason=reason,
                ts=ts,
                is_synthetic=0,
            )
        )
    total = sum(e[0] for e in entries)
    scout.points += total
    scout.level = level_for(scout.points)
    scout.reports_count += 1
    scout.last_active_at = ts
    s.commit()
    return {
        "report_id": rid,
        "ts": ts,
        "status": "pending",
        "points_pending": total,
        "verified_presence": verified,
        "distance_m": distance_m,
        "is_synthetic": False,
    }
