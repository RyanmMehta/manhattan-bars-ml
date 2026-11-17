"""SQL for live tables. Every read goes through Sources.union (real ∪ syn_)."""

from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import config as C
from ..timeutil import parse_ts, to_ny_iso
from .sources import Sources

# ISO strings are compared lexically in SQL, then exactly in Python; the slack covers
# offset changes (-04:00 / -05:00) across DST.
SLACK = timedelta(minutes=90)


def _bounds(start: datetime, end: datetime) -> dict:
    return {"lo": to_ny_iso(start - SLACK), "hi": to_ny_iso(end + SLACK)}


def _in(rows: list[dict], start: datetime, end: datetime, key: str = "ts") -> list[dict]:
    out = []
    for r in rows:
        try:
            t = parse_ts(r[key])
        except (ValueError, TypeError):
            continue
        if start <= t <= end:
            out.append(r)
    return out


def _venue_filter(venue_ids: list[str] | None, params: dict, col: str = "venue_id") -> str:
    if not venue_ids:
        return ""
    names = []
    for i, v in enumerate(venue_ids):
        params[f"v{i}"] = v
        names.append(f":v{i}")
    return f" AND {col} IN ({', '.join(names)})"


def reputations(s: Session, src: Sources, scout_ids: set[str]) -> dict[str, dict]:
    if not scout_ids:
        return {}
    params: dict = {}
    names = []
    for i, sid in enumerate(sorted(scout_ids)):
        params[f"s{i}"] = sid
        names.append(f":s{i}")
    where = f"scout_id IN ({', '.join(names)})"
    rows = s.execute(
        text(f"SELECT scout_id, display_name, reputation FROM {src.union('scouts', where)} x"),
        params,
    ).mappings()
    return {r["scout_id"]: dict(r) for r in rows}


def reports_window(
    s: Session, src: Sources, start: datetime, end: datetime, venue_ids: list[str] | None = None
) -> list[dict]:
    """Scout reports with ts in [start, end], each carrying the scout's CURRENT reputation
    (v2 §F; never syn_scout_reputation_history) and display name."""
    params = _bounds(start, end)
    where = "ts >= :lo AND ts <= :hi" + _venue_filter(venue_ids, params)
    # SYNTHETIC: syn_scout_reports until real scout_reports accumulate
    rows = [dict(r) for r in s.execute(
        text(f"SELECT * FROM {src.union('scout_reports', where)} r"), params
    ).mappings()]
    rows = _in(rows, start, end)
    reps = reputations(s, src, {r["scout_id"] for r in rows})
    for r in rows:
        sc = reps.get(r["scout_id"]) or {}
        rep = sc.get("reputation")
        r["reputation"] = C.NEW_SCOUT_REPUTATION if rep is None else float(rep)
        r["scout_display_name"] = sc.get("display_name")
        r["status"] = r.get("status") or "accepted"
    return rows


def state_inputs(
    s: Session, src: Sources, now: datetime, venue_ids: list[str] | None = None
) -> tuple[list[dict], list[dict]]:
    start = now - timedelta(minutes=C.INPUT_CUTOFF_MIN)
    end = now + timedelta(minutes=C.FUTURE_SKEW_MIN)
    return reports_window(s, src, start, end, venue_ids), updates_window(
        s, src, start, end, venue_ids
    )


def updates_window(
    s: Session, src: Sources, start: datetime, end: datetime, venue_ids: list[str] | None = None
) -> list[dict]:
    params = _bounds(start, end)
    where = "ts >= :lo AND ts <= :hi" + _venue_filter(venue_ids, params)
    # SYNTHETIC: syn_venue_updates until owners post real venue_updates
    rows = [dict(r) for r in s.execute(
        text(f"SELECT * FROM {src.union('venue_updates', where)} u"), params
    ).mappings()]
    return _in(rows, start, end)


def active_offers(s: Session, src: Sources, venue_id: str, now: datetime) -> list[dict]:
    params = {"vid": venue_id, "now": to_ny_iso(now - SLACK)}
    where = "venue_id = :vid AND offer IS NOT NULL AND offer_expires_at >= :now"
    rows = [dict(r) for r in s.execute(
        text(f"SELECT * FROM {src.union('venue_updates', where)} u"), params
    ).mappings()]
    out = []
    for r in rows:
        if parse_ts(r["ts"]) <= now < parse_ts(r["offer_expires_at"]):
            out.append(r)
    return sorted(out, key=lambda r: r["ts"], reverse=True)


def events_window(
    s: Session, src: Sources, venue_id: str, start: datetime, end: datetime
) -> list[dict]:
    params = _bounds(start, end) | {"vid": venue_id}
    where = "venue_id = :vid AND ts >= :lo AND ts <= :hi"
    # SYNTHETIC: syn_venue_events until the API's own venue_events build up
    rows = [dict(r) for r in s.execute(
        text(f"SELECT * FROM {src.union('venue_events', where)} e"), params
    ).mappings()]
    return _in(rows, start, end)


def all_scouts(s: Session, src: Sources) -> list[dict]:
    # SYNTHETIC: syn_scouts until real scouts sign up
    return [dict(r) for r in s.execute(text(f"SELECT * FROM {src.union('scouts')} x")).mappings()]


def ledger_window(s: Session, src: Sources, start: datetime, end: datetime) -> list[dict]:
    params = _bounds(start, end)
    # SYNTHETIC: syn_points_ledger until real points_ledger entries accumulate
    rows = [dict(r) for r in s.execute(
        text(f"SELECT * FROM {src.union('points_ledger', 'ts >= :lo AND ts <= :hi')} p"), params
    ).mappings()]
    return _in(rows, start, end)


def real_points(s: Session) -> dict[str, int]:
    rows = s.execute(text("SELECT scout_id, SUM(points) AS p FROM points_ledger GROUP BY scout_id"))
    return {r[0]: int(r[1] or 0) for r in rows}


def bounties(s: Session, src: Sources) -> list[dict]:
    # SYNTHETIC: syn_bounties until a real bounty-creation job writes `bounties`
    rows = [dict(r) for r in s.execute(text(f"SELECT * FROM {src.union('bounties')} b")).mappings()]
    claims = {
        r["bounty_id"]: dict(r)
        for r in s.execute(text("SELECT * FROM bounty_claims")).mappings()
    }
    for r in rows:
        c = claims.get(r["bounty_id"])
        if c:
            r["claimed_by"], r["claimed_at"] = c["claimed_by"], c["claimed_at"]
    return rows


def open_bounties(s: Session, src: Sources, now: datetime) -> list[dict]:
    out = []
    for b in bounties(s, src):
        if b.get("claimed_by"):
            if b.get("claimed_at") and parse_ts(b["claimed_at"]) <= now:
                continue
            if not b.get("claimed_at"):
                continue
        if parse_ts(b["created_at"]) > now:
            continue
        if b.get("expires_at") and parse_ts(b["expires_at"]) <= now:
            continue
        out.append(b)
    return out


def has_real_rows(s: Session) -> bool:
    for t in ("scout_reports", "venue_updates", "scouts", "users"):
        if s.execute(text(f"SELECT 1 FROM {t} LIMIT 1")).first():
            return True
    return False


def latest_impression(s: Session, src: Sources, user_id: str, venue_id: str) -> str | None:
    where = "user_id = :u AND venue_id = :v AND event_type = 'recommend_impression'"
    row = s.execute(
        text(f"SELECT MAX(ts) FROM {src.union('venue_events', where)} e"),
        {"u": user_id, "v": venue_id},
    ).first()
    return row[0] if row else None
