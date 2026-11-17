from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from .. import config as C
from ..context import Ctx
from ..deps import get_ctx, get_now, get_session
from ..repo import live
from ..schemas import BountyRow, LeaderRow
from ..timeutil import parse_ts
from .common import set_list_headers

router = APIRouter(tags=["scouts"])


@router.get("/api/scouts/leaderboard", response_model=list[LeaderRow])
def leaderboard(
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    now=Depends(get_now),
    ctx: Ctx = Depends(get_ctx),
    s: Session = Depends(get_session),
) -> list[dict]:
    week = live.ledger_window(s, ctx.src, now - timedelta(days=7), now)
    pw: dict[str, int] = {}
    for e in week:
        pw[e["scout_id"]] = pw.get(e["scout_id"], 0) + int(e["points"] or 0)
    rows = []
    for sc in live.all_scouts(s, ctx.src):
        if sc.get("joined_at"):
            try:
                if parse_ts(sc["joined_at"]) > now:
                    continue
            except ValueError:
                pass
        rep = sc.get("reputation")
        rows.append(
            {
                "scout_id": sc["scout_id"],
                "display_name": sc["display_name"],
                "level": sc.get("level") or "Rookie",
                "points": int(sc.get("points") or 0),
                "points_week": pw.get(sc["scout_id"], 0),
                "reputation": C.NEW_SCOUT_REPUTATION if rep is None else float(rep),
                "is_synthetic": bool(sc.get("is_synthetic")),
            }
        )
    rows.sort(key=lambda r: (-r["points"], -r["points_week"], r["display_name"]))
    rows = rows[:limit]
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    set_list_headers(response, rows)
    return rows


@router.get("/api/bounties", response_model=list[BountyRow], tags=["scouts"])
def bounties(
    response: Response,
    now=Depends(get_now),
    ctx: Ctx = Depends(get_ctx),
    s: Session = Depends(get_session),
) -> list[dict]:
    rows = []
    for b in live.open_bounties(s, ctx.src, now):
        v = ctx.catalog.by_id.get(b["venue_id"]) or {}
        rows.append(
            b | {"venue_name": v.get("display_name"), "is_synthetic": bool(b.get("is_synthetic"))}
        )
    rows.sort(key=lambda r: (-int(r["points"]), r["created_at"]))
    set_list_headers(response, rows)
    return rows
