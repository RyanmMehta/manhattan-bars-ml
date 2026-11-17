"""Venue card / detail / state assembly."""

import uuid
from datetime import datetime, timedelta

from pydantic import ValidationError
from sqlalchemy.orm import Session

from .. import config as C
from ..context import Ctx
from ..engine.geo import haversine_km
from ..models import VenueEvent
from ..repo import live
from ..repo.venues import complaint_risk, load_attributes
from ..schemas import LiveState
from ..timeutil import parse_ts, to_ny_iso


def validate_state(
    ctx: Ctx, raw: dict, venue_id: str, reports: list, updates: list, now: datetime
) -> dict:
    """recs output is validated; a malformed state falls back to the stub (RULES §4)."""
    try:
        return LiveState.model_validate(raw).model_dump()
    except (ValidationError, TypeError):
        from ..engine.stub import StubEngine

        return StubEngine().compute(venue_id, reports, updates, now)


def states_for(s: Session, ctx: Ctx, now: datetime, venue_ids: list[str]) -> dict[str, dict]:
    reports, updates = live.state_inputs(s, ctx.src, now, venue_ids)
    by_r: dict[str, list] = {}
    by_u: dict[str, list] = {}
    for r in reports:
        by_r.setdefault(r["venue_id"], []).append(r)
    for u in updates:
        by_u.setdefault(u["venue_id"], []).append(u)
    computed = ctx.engine.compute_all(reports, updates, now) if (reports or updates) else []
    out = {}
    for st in computed or []:
        vid = st.get("venue_id")
        if vid in venue_ids:
            out[vid] = validate_state(ctx, st, vid, by_r.get(vid, []), by_u.get(vid, []), now)
    for vid in venue_ids:
        if vid not in out:
            raw = ctx.engine.compute(vid, by_r.get(vid, []), by_u.get(vid, []), now)
            out[vid] = validate_state(ctx, raw, vid, by_r.get(vid, []), by_u.get(vid, []), now)
    return out


def card(
    v: dict,
    attrs: dict | None,
    state: dict,
    origin: tuple | None = None,
    cluster: tuple[str | None, str | None] = (None, None),
) -> dict:
    a = attrs or {}
    dist = None
    if origin and origin[0] is not None and origin[1] is not None:
        dist = round(haversine_km(origin[0], origin[1], v["lat"], v["lon"]), 2)
    claimed = a.get("is_claimed")
    return {
        "venue_id": v["venue_id"],
        "name": v["name"],
        "display_name": v["display_name"],
        "address": v.get("address"),
        "neighborhood": v.get("neighborhood"),
        "style": a.get("style"),
        "genres": [g for g in str(a.get("genres") or "").split("|") if g],
        "price_level": a.get("price_level"),
        "typical_cover_usd": a.get("typical_cover_usd"),
        "lat": v["lat"],
        "lon": v["lon"],
        "distance_km": dist,
        "opening_hours": v.get("osm_opening_hours") or a.get("opening_hours"),
        "is_claimed": None if claimed is None else bool(claimed),
        "cluster_label": cluster[0],
        "cluster_description": cluster[1],
        "state": state,
        "complaint_risk": complaint_risk(v),
        "is_synthetic": bool(state.get("is_synthetic") or a.get("is_synthetic")),
    }


def engine_venues(ctx: Ctx, attrs: dict, venues: list[dict]) -> list[dict]:
    """`venues` arg for recs (v2 §F): venue_id, name, lat, lon + attribute fields."""
    out = []
    for v in venues:
        a = attrs.get(v["venue_id"]) or {}
        row = {
            k: a.get(k)
            for k in (
                "genres",
                "style",
                "has_dance_floor",
                "typical_cover_usd",
                "capacity",
                "price_level",
                "is_claimed",
                "opening_hours",
            )
        }
        row.update(
            venue_id=v["venue_id"],
            name=v["name"],
            display_name=v["display_name"],
            lat=v["lat"],
            lon=v["lon"],
            is_synthetic=bool(a.get("is_synthetic")),
        )
        if v.get("osm_opening_hours"):
            row["opening_hours"] = v["osm_opening_hours"]
        out.append(row)
    return out


def list_cards(
    s: Session,
    ctx: Ctx,
    now: datetime,
    *,
    q: str | None,
    neighborhood: str | None,
    style: str | None,
    genre: str | None,
    launch_only: bool,
    lat: float | None,
    lon: float | None,
) -> list[dict]:
    venues = ctx.catalog.launch if launch_only else ctx.catalog.all_bars
    attrs = load_attributes(s, ctx.src, ctx.settings.manual_attributes_csv)
    if q:
        ql = q.lower()
        venues = [
            v
            for v in venues
            if ql in v["display_name"].lower()
            or ql in v["name"].lower()
            or ql in (v.get("address") or "").lower()
        ]
    if neighborhood:
        venues = [
            v for v in venues if (v.get("neighborhood") or "").lower() == neighborhood.lower()
        ]
    if style:
        venues = [v for v in venues if (attrs.get(v["venue_id"]) or {}).get("style") == style]
    if genre:
        venues = [
            v
            for v in venues
            if genre in str((attrs.get(v["venue_id"]) or {}).get("genres") or "").split("|")
        ]
    ids = [v["venue_id"] for v in venues]
    states = states_for(s, ctx, now, ids) if len(ids) <= 300 else _bulk_states(s, ctx, now, ids)
    cards = [
        card(
            v,
            attrs.get(v["venue_id"]),
            states[v["venue_id"]],
            (lat, lon),
            _cluster(ctx, v["venue_id"]),
        )
        for v in venues
    ]
    if lat is not None and lon is not None:
        cards.sort(key=lambda c: (c["distance_km"], c["display_name"]))
    else:
        cards.sort(key=lambda c: (c["display_name"].lower(), c["venue_id"]))
    return cards


def _cluster(ctx: Ctx, venue_id: str) -> tuple[str | None, str | None]:
    fn = getattr(ctx.engine, "cluster_info", None)
    return fn(venue_id) if fn else (None, None)


def _bulk_states(s: Session, ctx: Ctx, now: datetime, ids: list[str]) -> dict[str, dict]:
    """All-bars list: compute states only where inputs exist (no venue filter in SQL)."""
    reports, updates = live.state_inputs(s, ctx.src, now, None)
    active = {r["venue_id"] for r in reports} | {u["venue_id"] for u in updates}
    out = states_for(s, ctx, now, sorted(active & set(ids))) if active else {}
    empty = ctx.engine.compute("_", [], [], now)
    for vid in ids:
        if vid not in out:
            out[vid] = validate_state(ctx, dict(empty, venue_id=vid), vid, [], [], now)
    return out


def state_one(s: Session, ctx: Ctx, now: datetime, venue_id: str) -> dict:
    return states_for(s, ctx, now, [venue_id])[venue_id]


def detail(s: Session, ctx: Ctx, now: datetime, v: dict) -> dict:
    attrs = load_attributes(s, ctx.src, ctx.settings.manual_attributes_csv)
    st = state_one(s, ctx, now, v["venue_id"])
    reps = live.reports_window(
        s, ctx.src, now - timedelta(minutes=C.INPUT_CUTOFF_MIN), now, [v["venue_id"]]
    )
    reps = [r for r in reps if r["status"] in ("accepted", "pending")]
    reps.sort(key=lambda r: parse_ts(r["ts"]), reverse=True)
    recent = [
        {
            k: r.get(k)
            for k in (
                "report_id",
                "venue_id",
                "scout_id",
                "scout_display_name",
                "reputation",
                "ts",
                "crowd",
                "dancing",
                "line_minutes",
                "cover_usd",
                "music_genre",
                "verified_presence",
                "status",
            )
        }
        | {"is_synthetic": bool(r.get("is_synthetic"))}
        for r in reps[:10]
    ]
    offers = [
        dict(o, is_synthetic=bool(o.get("is_synthetic")))
        for o in live.active_offers(s, ctx.src, v["venue_id"], now)
    ]
    c = card(v, attrs.get(v["venue_id"]), st, cluster=_cluster(ctx, v["venue_id"]))
    synth = (
        c["is_synthetic"]
        or any(r["is_synthetic"] for r in recent)
        or any(o["is_synthetic"] for o in offers)
    )
    return {
        "venue": c,
        "state": st,
        "recent_reports": recent,
        "offers": offers,
        "is_synthetic": synth,
    }


def log_event(
    s: Session,
    ctx: Ctx,
    venue_id: str,
    event_type: str,
    user_id: str | None = None,
    when: datetime | None = None,
) -> None:
    s.add(
        VenueEvent(
            event_id=str(uuid.uuid4()),
            venue_id=venue_id,
            ts=to_ny_iso(when or ctx.write_now()),
            event_type=event_type,
            user_id=user_id,
            is_synthetic=0,
        )
    )


def heatmap(s: Session, ctx: Ctx, now: datetime, by_hour: bool) -> list[dict]:
    venues = ctx.catalog.launch
    ids = [v["venue_id"] for v in venues]
    if not by_hour:
        st = states_for(s, ctx, now, ids)
        return [_cell(v, st[v["venue_id"]], None) for v in venues]
    from ..timeutil import NY

    local = now.astimezone(NY)
    night = local.date() if local.hour >= 12 else local.date() - timedelta(days=1)
    out = []
    for h in C.HEATMAP_HOURS:
        day = night if h >= 12 else night + timedelta(days=1)
        hour_start = datetime(day.year, day.month, day.day, h, tzinfo=NY)
        if hour_start > now:
            continue
        at = min(hour_start + timedelta(minutes=30), now)
        st = states_for(s, ctx, at, ids)
        out.extend(_cell(v, st[v["venue_id"]], h) for v in venues)
    return out


def _cell(v: dict, st: dict, hour: int | None) -> dict:
    return {
        "venue_id": v["venue_id"],
        "lat": v["lat"],
        "lon": v["lon"],
        "hour": hour,
        "vibe_score": st.get("vibe_score"),
        "confidence": st.get("confidence"),
        "n_reports": st.get("n_reports") or 0,
        "is_synthetic": bool(st.get("is_synthetic")),
    }


def parse_iso_or_none(v: str | None) -> datetime | None:
    return parse_ts(v) if v else None
