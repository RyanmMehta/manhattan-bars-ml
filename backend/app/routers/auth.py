from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..context import Ctx
from ..deps import get_ctx, get_session
from ..errors import ApiError
from ..schemas import LoginIn, LoginOut
from ..services import auth as svc

router = APIRouter(tags=["auth"])


@router.post("/api/auth/demo-login", response_model=LoginOut, status_code=201)
def demo_login(
    body: LoginIn, ctx: Ctx = Depends(get_ctx), s: Session = Depends(get_session)
) -> dict:
    if not ctx.settings.demo_auth:
        raise ApiError(404, "not_found", "Demo login is disabled")
    return svc.demo_login(s, ctx, body.display_name, body.role, body.venue_id) | {
        "is_synthetic": False
    }
