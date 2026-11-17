from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..context import Ctx
from ..deps import get_ctx, get_session
from ..repo import live
from ..schemas import Health
from ..timeutil import parse_ts, to_ny_iso

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=Health)
def health(ctx: Ctx = Depends(get_ctx), s: Session = Depends(get_session)) -> dict:
    data = ctx.src.data_label(live.has_real_rows(s))
    demo = to_ny_iso(parse_ts(ctx.settings.demo_now)) if ctx.settings.demo_now else None
    return {"ok": True, "recs": ctx.engine_label, "data": data, "demo_now": demo,
            "is_synthetic": data != "real"}
