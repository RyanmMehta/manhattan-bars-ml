from collections.abc import Iterator

from fastapi import Depends, Header, Query, Request
from sqlalchemy.orm import Session

from .context import Ctx
from .errors import ApiError
from .services.auth import Principal, principal_from_token
from .timeutil import NaiveTimeError


def get_ctx(request: Request) -> Ctx:
    return request.app.state.ctx


def get_session(ctx: Ctx = Depends(get_ctx)) -> Iterator[Session]:
    yield from ctx.db.session()


def get_now(
    now: str | None = Query(default=None, description="ISO 8601 replay time, e.g. 2026-11-14T23:30:00-05:00"),
    ctx: Ctx = Depends(get_ctx),
):
    try:
        return ctx.read_now(now)
    except (NaiveTimeError, ValueError) as exc:
        raise ApiError(422, "validation_error", f"bad `now`: {exc}") from exc


def get_principal(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
    ctx: Ctx = Depends(get_ctx),
) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "unauthorized", "Missing bearer token")
    p = principal_from_token(session, ctx, authorization.split(" ", 1)[1].strip())
    if p is None:
        raise ApiError(401, "unauthorized", "Invalid or revoked token")
    return p


def get_optional_principal(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
    ctx: Ctx = Depends(get_ctx),
) -> Principal | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return principal_from_token(session, ctx, authorization.split(" ", 1)[1].strip())
