from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..context import Ctx
from ..deps import get_ctx, get_now, get_principal, get_session
from ..schemas import OwnerDashboard, OwnerUpdateIn, UpdateOut
from ..services import owner as svc
from ..services.auth import Principal

router = APIRouter(tags=["owner"])


@router.get("/api/owner/{venue_id}/dashboard", response_model=OwnerDashboard)
def dashboard(venue_id: str, now=Depends(get_now), p: Principal = Depends(get_principal),
              ctx: Ctx = Depends(get_ctx), s: Session = Depends(get_session)) -> dict:
    svc.check_owner(ctx, p, venue_id)
    return svc.dashboard(s, ctx, venue_id, now)


@router.post("/api/owner/{venue_id}/updates", response_model=UpdateOut, status_code=201)
def post_update(venue_id: str, body: OwnerUpdateIn,
                now: str | None = Query(default=None, include_in_schema=False),
                p: Principal = Depends(get_principal), ctx: Ctx = Depends(get_ctx),
                s: Session = Depends(get_session)) -> dict:
    svc.check_owner(ctx, p, venue_id)
    return svc.create_update(s, ctx, venue_id, body, now)
