from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..context import Ctx
from ..deps import get_ctx, get_now, get_session
from ..errors import ApiError
from ..schemas import LiveState, VenueCard, VenueDetail
from ..services import venues as svc
from .common import set_list_headers

router = APIRouter(tags=["venues"])


def _venue(ctx: Ctx, venue_id: str) -> dict:
    v = ctx.catalog.by_id.get(venue_id)
    if v is None:
        raise ApiError(404, "not_found", f"Unknown venue {venue_id}")
    return v


@router.get("/api/venues", response_model=list[VenueCard])
def list_venues(
    response: Response,
    q: str | None = None,
    neighborhood: str | None = None,
    style: str | None = None,
    genre: str | None = None,
    launch_only: bool = True,
    lat: float | None = Query(default=None, ge=-90, le=90),
    lon: float | None = Query(default=None, ge=-180, le=180),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    now=Depends(get_now),
    ctx: Ctx = Depends(get_ctx),
    s: Session = Depends(get_session),
) -> list[dict]:
    cards = svc.list_cards(s, ctx, now, q=q, neighborhood=neighborhood, style=style, genre=genre,
                           launch_only=launch_only, lat=lat, lon=lon)
    page = cards[offset : offset + limit]
    set_list_headers(response, page, total=len(cards))
    return page


@router.get("/api/venues/{venue_id}", response_model=VenueDetail)
def venue_detail(venue_id: str, now=Depends(get_now), ctx: Ctx = Depends(get_ctx),
                 s: Session = Depends(get_session)) -> dict:
    out = svc.detail(s, ctx, now, _venue(ctx, venue_id))
    svc.log_event(s, ctx, venue_id, "view")
    s.commit()
    return out


@router.get("/api/venues/{venue_id}/state", response_model=LiveState)
def venue_state(venue_id: str, now=Depends(get_now), ctx: Ctx = Depends(get_ctx),
                s: Session = Depends(get_session)) -> dict:
    _venue(ctx, venue_id)
    st = svc.state_one(s, ctx, now, venue_id)
    svc.log_event(s, ctx, venue_id, "tap")
    s.commit()
    return st
