from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..context import Ctx
from ..deps import get_ctx, get_principal, get_session
from ..schemas import ReportCreated, ReportIn
from ..services.auth import Principal
from ..services.reports import create_report

router = APIRouter(tags=["scouts"])


@router.post("/api/reports", response_model=ReportCreated, status_code=201)
def post_report(
    body: ReportIn,
    now: str | None = Query(default=None, include_in_schema=False),
    p: Principal = Depends(get_principal),
    ctx: Ctx = Depends(get_ctx),
    s: Session = Depends(get_session),
) -> dict:
    return create_report(s, ctx, p, body, now)
