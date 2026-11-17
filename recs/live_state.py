"""Live Venue State from scout reports + operator updates (specs PRD §5.1-5.7, CONTRACTS v2 §A/§F).

Public:
    compute(venue_id, reports, updates, now, *, predictor=None) -> dict
    compute_all(reports_df, updates_df, now, *, venue_ids=None, predictor=None) -> list[dict]

Inputs are lists of dicts or DataFrames with CONTRACTS column names. Report rows may carry
`reputation` (backend joins it; default 0.5) and `status` (missing -> accepted).
Pure: no DB, no network. `predicted_crowd` only comes from an explicit `predictor`
(callable venue_ids, times -> list[float|None]) or `predictor="auto"` (lazy crowd-model artifact).
Predictions never overwrite observed fields and never change confidence.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime

from . import config as C
from .inputs import clean, num, rows, round_half_up, split_genres, truthy
from .timeutil import minutes_between, to_dt

STATE_KEYS = (
    "venue_id", "crowd", "dancing", "line_minutes", "cover_usd", "music_genres", "vibe_score",
    "confidence", "freshness_minutes", "n_reports", "trend", "sources", "is_synthetic",
    "display", "predicted_crowd", "predicted_source",
)


# ---------------------------------------------------------------------------------------------- weights
def _decay(age: float, half_life: float) -> float:
    return 0.5 ** (max(age, 0.0) / half_life)


def _eligible_age(ts, now: datetime) -> float | None:
    """Age in minutes, or None if outside [now-180, now+2]."""
    t = to_dt(ts)
    if t is None:
        return None
    age = minutes_between(now, t)
    if age > C.CUTOFF_MINUTES or age < -C.FUTURE_SKEW_MINUTES:
        return None
    return age


def _scout_base_weight(r: dict) -> float:
    rep = num(r.get("reputation"))
    rep = C.DEFAULT_REPUTATION if rep is None else min(1.0, max(0.0, rep))
    w_rep = C.REP_BASE + C.REP_SLOPE * rep
    w_ver = 1.0 if truthy(r.get("verified_presence")) else C.UNVERIFIED_WEIGHT
    status = clean(r.get("status"))
    status = "accepted" if status is None else str(status).lower()
    w_status = C.STATUS_WEIGHT.get(status, 1.0)
    return w_rep * w_ver * w_status


# ---------------------------------------------------------------------------------------------- estimators
def _wmean(pairs):
    W = sum(w for _, w in pairs)
    return (sum(x * w for x, w in pairs) / W) if W > 0 else None, W


def _wsd(pairs, mean):
    W = sum(w for _, w in pairs)
    if W <= 0:
        return 0.0
    return math.sqrt(sum(w * (x - mean) ** 2 for x, w in pairs) / W)


def _wmedian(pairs):
    pairs = sorted((x, w) for x, w in pairs if w > 0)
    W = sum(w for _, w in pairs)
    if W <= 0:
        return None
    cum = 0.0
    for x, w in pairs:
        cum += w
        if cum >= W / 2 - 1e-12:
            return x
    return pairs[-1][0]


def empty_state(venue_id) -> dict:
    """State with zero usable inputs (AC1.10)."""
    return {
        "venue_id": venue_id, "crowd": None, "dancing": None, "line_minutes": None, "cover_usd": None,
        "music_genres": None, "vibe_score": None, "confidence": 0.0, "freshness_minutes": None,
        "n_reports": 0, "trend": None, "sources": [], "is_synthetic": False, "display": "none",
        "predicted_crowd": None, "predicted_source": None,
    }


def display_for(vibe, conf) -> str:
    if vibe is None or conf is None or conf < C.DISPLAY_LOW:
        return "none"
    return "show" if conf >= C.DISPLAY_SHOW else "low"


def vibe_band(vibe) -> str | None:
    """Frontend copy band (CONTRACTS §J)."""
    if vibe is None:
        return None
    for lo, hi, label in C.VIBE_BANDS:
        if lo <= vibe <= hi:
            return label
    return None


def _raw(venue_id, reports: list[dict], updates: list[dict], now: datetime) -> dict:
    """Unrounded estimates; used by compute() and by scoring (G5 needs crowd 3.76, not 3.8)."""
    crowd_p, dance_p, line_p, cover_p = [], [], [], []
    genre_w: dict[str, float] = defaultdict(float)
    genre_W = 0.0
    crowd_scouts = set()
    trend_recent, trend_prior = [], []
    newest_age = None
    n_reports = 0
    sources = set()
    synthetic = False
    op_total = 0.0

    def seen(age):
        nonlocal newest_age
        newest_age = age if newest_age is None else min(newest_age, age)

    for r in reports:
        if r.get("venue_id") is not None and r.get("venue_id") != venue_id:
            continue
        age = _eligible_age(r.get("ts"), now)
        if age is None:
            continue
        base = _scout_base_weight(r)
        if base <= 0:
            continue
        n_reports += 1
        sources.add("scout")
        seen(age)
        synthetic = synthetic or truthy(r.get("is_synthetic"))
        wf = base * _decay(age, C.HALF_LIFE_FAST)
        ws = base * _decay(age, C.HALF_LIFE_SCOUT_SLOW)
        c = num(r.get("crowd"))
        if c is not None:
            crowd_p.append((c, wf))
            crowd_scouts.add(r.get("scout_id"))
            if age <= C.TREND_RECENT_MIN:
                trend_recent.append((c, wf))
            elif age <= C.TREND_PRIOR_MIN:
                trend_prior.append((c, wf))
        d = num(r.get("dancing"))
        if d is not None:
            dance_p.append((d, wf))
        ln = num(r.get("line_minutes"))
        if ln is not None:
            line_p.append((ln, wf))
        cv = num(r.get("cover_usd"))
        if cv is not None:
            cover_p.append((cv, ws))
        g = clean(r.get("music_genre"))
        if g:
            genre_w[str(g).strip().lower()] += ws
            genre_W += ws

    for u in updates:
        if u.get("venue_id") is not None and u.get("venue_id") != venue_id:
            continue
        age = _eligible_age(u.get("ts"), now)
        if age is None:
            continue
        w = _decay(age, C.HALF_LIFE_OPERATOR) * C.OPERATOR_WEIGHT
        cv = num(u.get("cover_usd"))
        gs = split_genres(u.get("genres"))
        dj = clean(u.get("dj"))
        if cv is None and not gs and not dj:
            continue  # contributes nothing to state fields (offers/events live on the profile)
        sources.add("venue_update")
        seen(age)
        op_total += w
        synthetic = synthetic or truthy(u.get("is_synthetic"))
        if cv is not None:
            cover_p.append((cv, w))
        if gs:
            for g in gs:
                genre_w[g] += w
            genre_W += w

    crowd, W_crowd = _wmean(crowd_p)
    dancing, W_d = _wmean(dance_p)
    if W_crowd < C.MIN_FIELD_WEIGHT:
        crowd = None
    if W_d < C.MIN_FIELD_WEIGHT:
        dancing = None
    W_line = sum(w for _, w in line_p)
    line = _wmedian(line_p) if W_line >= C.MIN_FIELD_WEIGHT else None
    W_cover = sum(w for _, w in cover_p)
    cover = _wmedian(cover_p) if W_cover >= C.MIN_FIELD_WEIGHT else None
    if genre_W <= 0:
        genres = None
    elif genre_W < C.MIN_FIELD_WEIGHT:
        genres = None
    else:
        shares = sorted(((w / genre_W, g) for g, w in genre_w.items()), key=lambda t: (-t[0], t[1]))
        genres = [g for s, g in shares if s >= C.GENRE_SHARE_MIN - 1e-12]

    # vibe (crowd is the anchor)
    vibe = None
    if crowd is not None:
        terms = [(C.VIBE_WEIGHTS["crowd"], (crowd - 1) / 4)]
        if dancing is not None:
            terms.append((C.VIBE_WEIGHTS["dance"], dancing / 2))
        if line is not None:
            terms.append((C.VIBE_WEIGHTS["line"], min(line, C.LINE_CAP_MINUTES) / C.LINE_CAP_MINUTES))
        vibe = 100 * sum(a * x for a, x in terms) / sum(a for a, _ in terms)
        vibe = max(0.0, min(100.0, vibe))

    # confidence (independent of vibe)
    if W_crowd > 0:
        support = 1 - math.exp(-W_crowd / C.CONF_K)
        mean_all = sum(x * w for x, w in crowd_p) / W_crowd
        sd = _wsd(crowd_p, mean_all)
        agree = 1 - 0.5 * min(1.0, sd / C.AGREE_SD_SCALE)
        diverse = 1.0 if len(crowd_scouts) >= 2 else C.DIVERSE_SINGLE
        conf = support * agree * diverse
    elif op_total > 0 and n_reports == 0:
        conf = min(C.OPERATOR_ONLY_CONF_CAP, C.OPERATOR_ONLY_CONF_CAP * op_total)
    else:
        conf = 0.0

    trend = None
    r_mean, r_W = _wmean(trend_recent)
    p_mean, p_W = _wmean(trend_prior)
    if r_W >= C.TREND_MIN_WEIGHT and p_W >= C.TREND_MIN_WEIGHT:
        delta = r_mean - p_mean
        trend = "rising" if delta >= C.TREND_DELTA - 1e-9 else ("falling" if delta <= -C.TREND_DELTA + 1e-9 else "steady")

    return {
        "crowd": crowd, "dancing": dancing, "line_minutes": line, "cover_usd": cover,
        "music_genres": genres, "vibe": vibe, "confidence": conf, "trend": trend,
        "freshness_minutes": None if newest_age is None else max(0, math.floor(newest_age)),
        "n_reports": n_reports, "sources": sorted(sources), "is_synthetic": synthetic,
        "W_crowd": W_crowd,
    }


def _finish(venue_id, raw: dict, predicted=None, predicted_synthetic=False) -> dict:
    vibe = None if raw["vibe"] is None else int(round_half_up(raw["vibe"]))
    conf = round_half_up(raw["confidence"], 2)
    pc = None if predicted is None else round_half_up(float(predicted), 1)
    return {
        "venue_id": venue_id,
        "crowd": None if raw["crowd"] is None else round_half_up(raw["crowd"], 1),
        "dancing": None if raw["dancing"] is None else round_half_up(raw["dancing"], 1),
        "line_minutes": None if raw["line_minutes"] is None else int(round_half_up(raw["line_minutes"])),
        "cover_usd": None if raw["cover_usd"] is None else int(round_half_up(raw["cover_usd"])),
        "music_genres": raw["music_genres"],
        "vibe_score": vibe,
        "confidence": conf,
        "freshness_minutes": raw["freshness_minutes"],
        "n_reports": raw["n_reports"],
        "trend": raw["trend"],
        "sources": raw["sources"],
        "is_synthetic": bool(raw["is_synthetic"] or (pc is not None and predicted_synthetic)),
        "display": display_for(vibe, conf),
        "predicted_crowd": pc,
        "predicted_source": None if pc is None else "model",
    }


def _resolve_predictor(predictor):
    if predictor == "auto":
        try:
            from . import crowd_model
            return crowd_model.predict if crowd_model.available() else None
        except Exception:  # noqa: BLE001 - degrade, never crash (PRD N3)
            return None
    return predictor


def _predict(predictor, venue_ids, now):
    if predictor is None or not venue_ids:
        return [None] * len(venue_ids)
    try:
        out = predictor(list(venue_ids), [now] * len(venue_ids))
        return [None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v) for v in out]
    except Exception:  # noqa: BLE001
        return [None] * len(venue_ids)


def compute(venue_id, reports, updates, now, *, predictor=None) -> dict:
    """Live Venue State for one venue at `now` (tz-aware datetime or ISO string).

    reports: scout report rows (crowd 1-5, dancing 0-2, line_minutes, cover_usd, music_genre,
             verified_presence, status, reputation, ts, scout_id).
    updates: operator update rows (cover_usd, genres pipe-separated, dj, ts).
    Rows for other venue_ids are ignored. Returns a JSON-serialisable dict (CONTRACTS Live Venue State
    + v2 §F optional keys `display`, `predicted_crowd`, `predicted_source`).
    """
    now = to_dt(now)
    raw = _raw(venue_id, rows(reports), rows(updates), now)
    pred = _predict(_resolve_predictor(predictor), [venue_id], now)[0]
    return _finish(venue_id, raw, pred, predicted_synthetic=True)  # SYNTHETIC: model trained on live-sim reports


def raw_state(venue_id, reports, updates, now) -> dict:
    """Unrounded internals (crowd/dancing etc. before output rounding). Used by scoring/routing."""
    return _raw(venue_id, rows(reports), rows(updates), to_dt(now))


def compute_all(reports_df, updates_df, now, *, venue_ids=None, predictor=None) -> list[dict]:
    """Live state for every venue appearing in reports/updates (plus `venue_ids`, if given), sorted by venue_id."""
    now = to_dt(now)
    by_r: dict = defaultdict(list)
    by_u: dict = defaultdict(list)
    for r in rows(reports_df):
        by_r[r.get("venue_id")].append(r)
    for u in rows(updates_df):
        by_u[u.get("venue_id")].append(u)
    ids = set(by_r) | set(by_u) | set(venue_ids or [])
    ids.discard(None)
    ids = sorted(ids, key=str)
    preds = _predict(_resolve_predictor(predictor), ids, now)
    out = []
    for vid, p in zip(ids, preds):
        raw = _raw(vid, by_r.get(vid, []), by_u.get(vid, []), now)
        out.append(_finish(vid, raw, p, predicted_synthetic=True))
    return out
