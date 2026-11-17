import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..context import Ctx
from ..deps import get_ctx, get_principal, get_session
from ..errors import ApiError
from ..models import Feedback
from ..repo import live
from ..schemas import FeedbackIn, FeedbackOut
from ..services.auth import Principal

router = APIRouter(tags=["feedback"])


@router.post("/api/feedback", response_model=FeedbackOut, status_code=201)
def post_feedback(
    body: FeedbackIn,
    p: Principal = Depends(get_principal),
    ctx: Ctx = Depends(get_ctx),
    s: Session = Depends(get_session),
) -> dict:
    if p.role not in ("user", "admin"):
        raise ApiError(403, "forbidden", "Only users can leave feedback")
    user_id = body.user_id or p.subject_id
    if p.role == "user" and user_id != p.subject_id:
        raise ApiError(403, "forbidden", "user_id does not match your token")
    if body.venue_id not in ctx.catalog.by_id:
        raise ApiError(404, "not_found", f"Unknown venue {body.venue_id}")
    row = Feedback(
        feedback_id=str(uuid.uuid4()),
        user_id=user_id,
        venue_id=body.venue_id,
        recommended_at=live.latest_impression(s, ctx.src, user_id, body.venue_id),
        visited=body.visited,
        rating=body.rating,
        is_synthetic=0,
    )
    s.add(row)
    s.commit()
    return {
        c: getattr(row, c)
        for c in ("feedback_id", "user_id", "venue_id", "recommended_at", "visited", "rating")
    } | {"is_synthetic": False}
