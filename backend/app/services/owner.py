import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from ..context import Ctx
from ..errors import ApiError
from ..models import VenueUpdate
from ..repo import live
from ..schemas import OwnerUpdateIn
from ..timeutil import NY, night_start, parse_ts, to_ny_iso
from .auth import Principal


def check_owner(ctx: Ctx, p: Principal, venue_id: str) -> dict:
    venue = ctx.catalog.by_id.get(venue_id)
    if venue is None or not venue["is_launch"]:
        raise ApiError(404, "not_found", f"Unknown launch venue {venue_id}")
    if p.role == "admin":
        return venue
    if p.role != "owner" or p.subject_id != venue_id:
        raise ApiError(403, "forbidden", "Only this venue's owner can do that")
    return venue


def dashboard(s: Session, ctx: Ctx, venue_id: str, now) -> dict:
    start = night_start(now)
    events = live.events_window(s, ctx.src, venue_id, start, now)
    reports = live.reports_window(s, ctx.src, start, now, [venue_id])
    counts = {t: 0 for t in ("view", "tap", "save", "recommend_impression")}
    by_hour: dict[int, int] = {}
    for e in events:
        if e["event_type"] in counts:
            counts[e["event_type"]] += 1
        h = parse_ts(e["ts"]).astimezone(NY).hour
        by_hour[h] = by_hour.get(h, 0) + 1
    hours = []
    t = start
    while t <= now:
        h = t.astimezone(NY).hour
        hours.append({"hour": h, "value": by_hour.get(h, 0)})
        t += timedelta(hours=1)
    synth = any(e.get("is_synthetic") for e in events) or any(r.get("is_synthetic") for r in reports)
    return {"venue_id": venue_id, "views": counts["view"], "taps": counts["tap"],
            "saves": counts["save"], "reports_tonight": len(reports),
            "rec_appearances": counts["recommend_impression"], "demand_by_hour": hours,
            "is_synthetic": synth}


def create_update(s: Session, ctx: Ctx, venue_id: str, body: OwnerUpdateIn, now_q: str | None) -> dict:
    now = ctx.write_now(now_q)
    genres = body.genres
    if isinstance(genres, list):
        bad = [g for g in genres if g not in ctx.genres]
        if bad:
            raise ApiError(422, "validation_error", f"unknown genres {bad}")
        genres = "|".join(genres)
    expires = None
    if body.offer_expires_at:
        try:
            expires = to_ny_iso(parse_ts(body.offer_expires_at))
        except ValueError as exc:
            raise ApiError(422, "validation_error", f"bad offer_expires_at: {exc}") from exc
    elif body.offer:
        expires = to_ny_iso(now + timedelta(hours=2))  # SPEC(specs §5.2): offer else 120 min
    row = VenueUpdate(update_id=str(uuid.uuid4()), venue_id=venue_id, ts=to_ny_iso(now),
                      cover_usd=body.cover_usd, dj=body.dj, genres=genres or None,
                      event=body.event, offer=body.offer, offer_expires_at=expires, is_synthetic=0)
    s.add(row)
    s.commit()
    return {c: getattr(row, c) for c in ("update_id", "venue_id", "ts", "cover_usd", "dj", "genres",
                                         "event", "offer", "offer_expires_at")} | {"is_synthetic": False}
