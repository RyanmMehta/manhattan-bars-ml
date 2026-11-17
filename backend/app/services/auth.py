import hashlib
import secrets
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models import ApiToken, Scout, User
from ..timeutil import to_ny_iso

if TYPE_CHECKING:
    from ..context import Ctx


@dataclass
class Principal:
    role: str  # user | scout | owner | admin
    subject_id: str


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def principal_from_token(session: Session, ctx: "Ctx", token: str) -> Principal | None:
    admin = ctx.settings.admin_token
    if admin and secrets.compare_digest(token, admin):
        return Principal("admin", "admin")
    row = session.get(ApiToken, _hash(token))
    if row is None or row.revoked:
        return None
    return Principal(row.role, row.subject_id)


def demo_login(
    session: Session, ctx: "Ctx", display_name: str, role: str, venue_id: str | None
) -> dict:
    now = to_ny_iso(ctx.write_now())
    out: dict = {"role": role, "user_id": None, "scout_id": None, "venue_id": None}
    if role == "user":
        uid = str(uuid.uuid4())
        session.add(User(user_id=uid, display_name=display_name, prefs_json=None, is_synthetic=0))
        subject = out["user_id"] = uid
    elif role == "scout":
        sid = str(uuid.uuid4())
        session.add(
            Scout(
                scout_id=sid,
                display_name=display_name,
                joined_at=now,
                reputation=0.5,
                points=0,
                level="Rookie",
                reports_count=0,
                is_synthetic=0,
            )
        )
        subject = out["scout_id"] = sid
    else:
        if not venue_id or venue_id not in {v["venue_id"] for v in ctx.catalog.launch}:
            raise ApiError(
                422, "validation_error", "owner login needs the venue_id of a launch venue"
            )
        # One owner per venue (v2 §J): the owner identity IS the venue; a second login gets a
        # fresh token for the same identity so the demo can't lock itself out.
        subject = out["venue_id"] = venue_id
    token = secrets.token_urlsafe(32)
    session.add(ApiToken(token_hash=_hash(token), role=role, subject_id=subject, created_at=now))
    session.commit()
    out["token"] = token
    return out


def require(p: Principal, *roles: str) -> None:
    if p.role not in roles and p.role != "admin":
        raise ApiError(403, "forbidden", f"needs role {' or '.join(roles)}")


def scout_exists(session: Session, scout_id: str) -> bool:
    return (
        session.execute(select(Scout.scout_id).where(Scout.scout_id == scout_id)).first()
        is not None
    )
