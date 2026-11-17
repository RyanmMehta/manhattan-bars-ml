from fastapi import APIRouter, Depends, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..context import Ctx
from ..deps import get_ctx, get_now, get_optional_principal, get_session
from ..engine.stub import StubEngine
from ..errors import ApiError
from ..repo.venues import complaint_risk, load_attributes
from ..schemas import PlanNightIn, Preferences, Recommendation, Stop
from ..services import venues as svc
from ..services.auth import Principal
from ..timeutil import NaiveTimeError, parse_ts
from .common import set_list_headers

router = APIRouter(tags=["recommend"])


def _inputs(s: Session, ctx: Ctx, now, prefs: Preferences) -> tuple[dict, list, list]:
    venues = ctx.catalog.launch if prefs.launch_only else ctx.catalog.all_bars
    attrs = load_attributes(s, ctx.src, ctx.settings.manual_attributes_csv)
    ids = [v["venue_id"] for v in venues]
    states = svc.states_for(s, ctx, now, ids)
    p = prefs.model_dump(exclude_none=True)
    return p, [states[i] for i in ids], svc.engine_venues(ctx, attrs, venues)


def order_and_rank(rows: list) -> list:
    """Non-excluded by rank_score desc (ties: nearer first), then excluded; ranks 1..n.
    recs may leave `rank` null on excluded rows, so the backend always assigns it."""
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return rows

    def key(r: dict) -> tuple:
        d = r.get("distance_km")
        return (bool(r.get("excluded")), -(r.get("rank_score") or 0), d if d is not None else 1e9)

    out = sorted(rows, key=key)
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out


def _validated(model, rows: list, fallback):
    try:
        return [model.model_validate(r).model_dump() for r in rows]
    except (ValidationError, TypeError, AttributeError):
        return [model.model_validate(r).model_dump() for r in fallback()]


@router.post("/api/recommend", response_model=list[Recommendation])
def recommend(
    prefs: Preferences,
    response: Response,
    now=Depends(get_now),
    ctx: Ctx = Depends(get_ctx),
    s: Session = Depends(get_session),
    who: Principal | None = Depends(get_optional_principal),
) -> list[dict]:
    user_id = who.subject_id if who and who.role == "user" else None
    p, states, venues = _inputs(s, ctx, now, prefs)
    raw = order_and_rank(ctx.engine.recommend(p, states, venues, now))
    rows = _validated(
        Recommendation, raw, lambda: order_and_rank(StubEngine().recommend(p, states, venues, now))
    )
    for r in rows:
        v = ctx.catalog.by_id.get(r["venue_id"]) or {}
        r["complaint_risk"] = complaint_risk(v)
        if not r["excluded"]:
            svc.log_event(s, ctx, r["venue_id"], "recommend_impression", user_id)
    s.commit()
    set_list_headers(response, rows)
    return rows


@router.post("/api/plan-night", response_model=list[Stop])
def plan_night(
    body: PlanNightIn,
    response: Response,
    now=Depends(get_now),
    ctx: Ctx = Depends(get_ctx),
    s: Session = Depends(get_session),
) -> list[dict]:
    if not ctx.settings.feature_routing:
        raise ApiError(404, "not_found", "Run My Night is disabled (FEATURE_ROUTING=0)")
    try:
        start = parse_ts(body.start_time) if body.start_time else now
    except (NaiveTimeError, ValueError) as exc:
        raise ApiError(422, "validation_error", f"bad start_time: {exc}") from exc
    p, states, venues = _inputs(s, ctx, start, body)
    p.pop("n_stops", None)
    raw = ctx.engine.plan_night(p, states, venues, start, body.n_stops)
    rows = _validated(
        Stop, raw, lambda: StubEngine().plan_night(p, states, venues, start, body.n_stops)
    )
    set_list_headers(response, rows)
    return rows
