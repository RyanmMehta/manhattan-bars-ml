"""Ranked recommendations (specs PRD §5.9-5.11, CONTRACTS Recommendation result + v2 §F).

Public:
    recommend(prefs, states, venues, now) -> list[dict]

prefs: CONTRACTS Preferences (+ optional exclude_venue_ids). Missing pref -> that component's weight is 0
       (renormalised away) and its limit is not applied.
states: Live Venue State dicts (from live_state). A venue without a state is scored as "no reports".
venues: rows with venue_id, name, lat, lon + optional syn_venue_attributes fields
        (genres, style, has_dance_floor, typical_cover_usd, capacity, price_level, opening_hours)
        and optional cluster_label / complaint_risk (looked up from artifacts when absent).
complaint_risk is passed through only ("311 noise-complaint risk"); it never feeds any score or reason.
"""
from __future__ import annotations

from . import config as C
from . import hours as H
from . import live_state
from . import reasons as R
from .geo import haversine_km
from .inputs import by_key, clean, num, rows, round_half_up, split_genres, truthy
from .timeutil import to_dt

REC_KEYS = (
    "venue_id", "name", "match_score", "vibe_score", "confidence", "distance_km", "reasons", "missing",
    "excluded", "excluded_reason", "rank_score", "rank", "cluster_label", "complaint_risk", "is_synthetic",
)


def _exclusion(prefs: dict, st: dict, venue: dict, dist: float | None, now) -> str | None:
    """First broken hard limit on a KNOWN value, else None. Unknown values never exclude."""
    max_cover = num(prefs.get("max_cover_usd"))
    max_line = num(prefs.get("max_line_minutes"))
    max_dist = num(prefs.get("max_distance_km"))
    cover, line = num(st.get("cover_usd")), num(st.get("line_minutes"))
    if venue.get("venue_id") in set(prefs.get("exclude_venue_ids") or []):
        return "excluded by you"
    if max_cover is not None and cover is not None and cover > max_cover:
        return f"cover ${cover:.0f} over your ${max_cover:.0f}"
    if max_line is not None and line is not None and line > max_line:
        return f"line ~{line:.0f} min over your {max_line:.0f}"
    if max_dist is not None and dist is not None and dist > max_dist + 1e-9:
        return f"{dist:.1f} km away, over your {max_dist:g} km"
    if H.is_open(clean(venue.get("opening_hours")), now) is False:
        return "closed now"
    return None


def components(prefs: dict, st: dict, venue: dict, dist: float | None) -> dict:
    """{name: (weight, score, known, evidence)} for the 7 match components (specs §5.10)."""
    W = C.MATCH_WEIGHTS
    U = C.UNKNOWN_SCORE
    out = {}

    # genre
    want = [g.lower() for g in (prefs.get("genres") or [])]
    live = st.get("music_genres")
    static = split_genres(venue.get("genres"))
    if not want:
        out["genre"] = (W["genre"], 1.0, True, {"kind": "any"})
    elif live and set(live) & set(want):
        g = next(x for x in live if x in want)
        out["genre"] = (W["genre"], 1.0, True, {"kind": "live", "genre": g})
    elif static and set(static) & set(want):
        g = next(x for x in static if x in want)
        out["genre"] = (W["genre"], C.STATIC_GENRE_SCORE, True, {"kind": "static", "genre": g})
    elif live or static:
        out["genre"] = (W["genre"], 0.0, True, {"kind": "none"})
    else:
        out["genre"] = (W["genre"], U, False, {})

    # dancing
    wd = prefs.get("want_dancing")
    d = num(st.get("dancing"))
    if wd is None:
        out["dancing"] = (0.0, 0.0, True, {})
    elif d is None:
        out["dancing"] = (W["dancing"], U, False, {})
    else:
        s = d / 2 if truthy(wd) else 1 - d / 2
        out["dancing"] = (W["dancing"], min(1.0, max(0.0, s)), True, {"want": truthy(wd), "dancing": d})

    # crowd
    cp = num(prefs.get("crowd_pref"))
    c = num(st.get("crowd"))
    if cp is None:
        out["crowd"] = (0.0, 0.0, True, {})
    elif c is None:
        out["crowd"] = (W["crowd"], U, False, {})
    else:
        out["crowd"] = (W["crowd"], max(0.0, 1 - abs(c - cp) / 4), True, {"crowd": c, "pref": cp})

    # line
    ml = num(prefs.get("max_line_minutes"))
    ln = num(st.get("line_minutes"))
    if ml is None:
        out["line"] = (0.0, 0.0, True, {})
    elif ln is None:
        out["line"] = (W["line"], U, False, {})
    else:
        s = 1 - 0.5 * ln / ml if ml > 0 else (1.0 if ln == 0 else 0.0)
        out["line"] = (W["line"], min(1.0, max(0.0, s)), True, {"line": ln, "max": ml})

    # cover
    mc = num(prefs.get("max_cover_usd"))
    cv = num(st.get("cover_usd"))
    if mc is None:
        out["cover"] = (0.0, 0.0, True, {})
    elif cv is None:
        out["cover"] = (W["cover"], U, False, {})
    else:
        s = 1.0 if cv == 0 else (1 - 0.5 * cv / mc if mc > 0 else 0.0)
        out["cover"] = (W["cover"], min(1.0, max(0.0, s)), True, {"cover": cv, "max": mc})

    # distance
    md = num(prefs.get("max_distance_km"))
    if md is None:
        out["distance"] = (0.0, 0.0, True, {})
    elif dist is None:
        out["distance"] = (W["distance"], U, False, {})
    else:
        s = 1 - dist / md if md > 0 else 0.0
        out["distance"] = (W["distance"], min(1.0, max(0.0, s)), True, {"km": dist})

    # group
    gs = num(prefs.get("group_size"))
    cap = num(venue.get("capacity"))
    if gs is None or gs <= 0:
        out["group"] = (0.0, 0.0, True, {})
    elif cap is None:
        out["group"] = (W["group"], U, False, {})
    else:
        out["group"] = (W["group"], min(1.0, cap / (10 * gs)), True, {"group_size": gs, "capacity": cap})
    return out


def match_raw(comps: dict) -> float:
    tw = sum(w for w, _, _, _ in comps.values())
    if tw <= 0:
        return 0.0
    return 100 * sum(w * s for w, s, _, _ in comps.values()) / tw


def rank_value(match: float, conf) -> float:
    conf = num(conf) or 0.0
    return match * (C.RANK_BASE + C.RANK_CONF * conf)


def _lookup(venue: dict, key: str):
    v = clean(venue.get(key))
    if v is not None:
        return v
    try:
        if key == "cluster_label":
            from . import clustering
            return clustering.label_for(venue.get("venue_id"))
        if key == "complaint_risk":
            from . import complaint_risk
            return complaint_risk.score_for(venue.get("venue_id"))
    except Exception:  # noqa: BLE001 - artifacts optional (PRD N3)
        return None
    return None


def score_one(prefs: dict, st: dict, venue: dict, now) -> dict:
    """Recommendation result for one venue (rank filled in by recommend)."""
    vid = venue.get("venue_id")
    dist = haversine_km(num(prefs.get("lat")), num(prefs.get("lon")), num(venue.get("lat")), num(venue.get("lon")))
    comps = components(prefs, st, venue, dist)
    m = match_raw(comps)
    match = int(round_half_up(m))
    rs = rank_value(match, st.get("confidence"))
    excl = _exclusion(prefs, st, venue, dist, now)
    reasons = R.reasons(comps, st, prefs)
    missing = R.missing(comps, st, prefs)
    if excl:
        reasons = [f"Excluded: {excl}"] + reasons[: C.MAX_REASONS - 1]
    cr = _lookup(venue, "complaint_risk")
    return {
        "venue_id": vid,
        "name": clean(venue.get("name")) or clean(venue.get("display_name")) or vid,
        "match_score": match,
        "vibe_score": st.get("vibe_score"),
        "confidence": st.get("confidence") if st.get("confidence") is not None else 0.0,
        "distance_km": None if dist is None else round_half_up(dist, 2),
        "reasons": reasons,
        "missing": missing,
        "excluded": excl is not None,
        "excluded_reason": excl,
        "rank_score": round_half_up(rs, 1),
        "rank": None,
        "cluster_label": _lookup(venue, "cluster_label"),
        "complaint_risk": None if cr is None else round_half_up(float(cr), 3),
        "is_synthetic": bool(st.get("is_synthetic") or truthy(venue.get("is_synthetic"))),
        "_rs": rs,
        "_dist": dist if dist is not None else float("inf"),
    }


def recommend(prefs: dict, states, venues, now) -> list[dict]:
    """Rank `venues` for `prefs` at `now` (datetime or ISO).

    Returns included venues sorted by rank_score desc, distance asc, venue_id (rank 1..n), then excluded
    venues (excluded=true, rank=null, excluded_reason set and repeated as reasons[0]).
    match_score/rank_score are still computed for excluded venues (debugging; frontend shows only a count).
    """
    now = to_dt(now)
    prefs = dict(prefs or {})
    st_by = by_key(rows(states))
    out = []
    for v in rows(venues):
        vid = v.get("venue_id") or v.get("license_id")
        if vid is None:
            continue
        v["venue_id"] = vid
        st = st_by.get(vid) or live_state.empty_state(vid)
        out.append(score_one(prefs, st, v, now))
    key = lambda r: (-r["_rs"], r["_dist"], str(r["venue_id"]))  # noqa: E731
    inc = sorted((r for r in out if not r["excluded"]), key=key)
    exc = sorted((r for r in out if r["excluded"]), key=key)
    for i, r in enumerate(inc, 1):
        r["rank"] = i
    res = inc + exc
    for r in res:
        r.pop("_rs")
        r.pop("_dist")
    return res
