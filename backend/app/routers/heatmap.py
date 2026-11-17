from typing import Literal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..context import Ctx
from ..deps import get_ctx, get_now, get_session
from ..errors import ApiError
from ..schemas import HeatCell
from ..services import venues as svc
from .common import set_list_headers

router = APIRouter(tags=["heatmap"])


@router.get("/api/heatmap", response_model=list[HeatCell])
def heatmap(response: Response, by: Literal["hour"] | None = None, now=Depends(get_now),
            ctx: Ctx = Depends(get_ctx), s: Session = Depends(get_session)) -> list[dict]:
    if not ctx.settings.feature_heatmap:
        raise ApiError(404, "not_found", "Heatmap is disabled (FEATURE_HEATMAP=0)")
    rows = svc.heatmap(s, ctx, now, by_hour=by == "hour")
    set_list_headers(response, rows)
    return rows
