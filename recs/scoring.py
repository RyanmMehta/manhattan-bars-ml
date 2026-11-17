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
    "excluded", "excluded_reason", "rank_score", "rank", "cluster_label", "cluster_description", "complaint_risk", "is_synthetic",
)


def _is_open(venue: dict, now) -> bool | None:
    """Caller-supplied `is_open_now` wins; else parse OSM `opening_hours` (unknown -> None, never excludes)."""
    v = clean(venue.get("is_open_now"))
    if v is not None:
        return bool(v)
    return H.is_open(clean(venue.get("opening_hours")), now)


def _fmt_num(x: float) -> str:
    return f"{x:g}" if x != int(x) else str(int(x))


def _exclusion(prefs: dict, st: dict, venue: dict, dist: float | None, now) -> str | None:
    """First broken hard limit on a KNOWN value (specs SCORING §5.9 order), else None."""
    if _is_open(venue, now) is False:
        return "closed now"
    if prefs.get("launch_only") and venue.get("is_launch") is False:
        return "outside launch area"
    max_dist = num(prefs.get("max_distance_km"))
    if max_dist is not None and dist is not None and dist > max_dist:
        return f"{dist:.1f} km away, over your {max_dist:g} km"
    max_cover, cover = num(prefs.get("max_cover_usd")), num(st.get("cover_usd"))
    if max_cover is not None and cover is not None and cover > max_cover:
        return f"cover ${_fmt_num(cover)} over your ${_fmt_num(max_cover)}"
    max_line, line = num(prefs.get("max_line_minutes")), num(st.get("line_minutes"))
    if max_line is not None and line is not None and line > max_line:
        return f"line ~{_fmt_num(line)} min over your {_fmt_num(max_line)}"
    return None


def components(prefs: dict, st: dict, venue: dict, dist: float | None) -> dict:
    """{name: (weight, score, reason|None, missing|None)} for the 7 match components (specs §5.10).

    weight 0 means the pref is not set (renormalised away). Unknown inputs score 0.4 and set `missing`.
    """
    W, U = C.MATCH_WEIGHTS, C.UNKNOWN_SCORE
    n, fresh = st.get("n_reports") or 0, st.get("freshness_minutes")
    out = {}

    want = [str(g).lower() for g in (prefs.get("genres") or [])]
    live = st.get("music_genres") or []
    static = split_genres(venue.get("genres"))
    hit = [g for g in live if g in want]
    s_hit = [g for g in static if g in want]
    if not want:
        out["genre"] = (W["genre"], 1.0, None, None)
    elif hit:
        ev = f"({n} reports, {fresh} min ago)" if n else "(posted by venue)"
        out["genre"] = (W["genre"], 1.0, f"{R.genre_label(hit[0])} playing {ev}", None)
    elif s_hit:
        out["genre"] = (W["genre"], C.STATIC_GENRE_SCORE, f"Usually plays {R.genre_label(s_hit[0])}", None)
    elif live or static:
        out["genre"] = (W["genre"], 0.0, None, None)
    else:
        out["genre"] = (W["genre"], U, None, R.MISSING["genre"])

    wd, d = prefs.get("want_dancing"), num(st.get("dancing"))
    if wd is None:
        out["dancing"] = (0.0, 0.0, None, None)
    elif d is None:
        out["dancing"] = (W["dancing"], U, None, R.MISSING["dancing"])
    elif truthy(wd):
        out["dancing"] = (W["dancing"], d / 2, f"Dancing reported ({n} reports)", None)
    else:
        out["dancing"] = (W["dancing"], 1 - d / 2, "Low-key, little dancing", None)

    cp, c = num(prefs.get("crowd_pref")), num(st.get("crowd"))
    if cp is None:
        out["crowd"] = (0.0, 0.0, None, None)
    elif c is None:
        out["crowd"] = (W["crowd"], U, None, R.MISSING["crowd"])
    else:
        out["crowd"] = (W["crowd"], 1 - abs(c - cp) / 4, f"Crowd {c:g} of 5, close to your {_fmt_num(cp)}", None)

    for key, field, pref, what in (("line", "line_minutes", "max_line_minutes", "line"),
                                   ("cover", "cover_usd", "max_cover_usd", "cover")):
        lim, val = num(prefs.get(pref)), num(st.get(field))
        if lim is None:
            out[key] = (0.0, 0.0, None, None)
        elif val is None:
            out[key] = (W[key], U, None, R.MISSING[key])
        elif key == "cover" and val == 0:
            out[key] = (W[key], 1.0, "No cover", None)
        else:
            sc = max(0.0, 1 - 0.5 * val / lim) if lim > 0 else 0.0
            txt = (f"Line ~{_fmt_num(val)} min, under your {_fmt_num(lim)}" if key == "line"
                   else f"Cover ${_fmt_num(val)}, under your ${_fmt_num(lim)}")
            out[key] = (W[key], sc, txt, None)

    md = num(prefs.get("max_distance_km"))
    if md is None:
        out["distance"] = (0.0, 0.0, None, None)
    elif dist is None:
        out["distance"] = (W["distance"], U, None, R.MISSING["distance"])
    else:
        txt = "Under 0.1 km away" if dist < 0.1 else f"{dist:.1f} km away"
        out["distance"] = (W["distance"], max(0.0, 1 - dist / md) if md > 0 else 0.0, txt, None)

    gs, cap = num(prefs.get("group_size")), num(venue.get("capacity"))
    if not gs:
        out["group"] = (0.0, 0.0, None, None)
    elif cap is None:
        out["group"] = (W["group"], U, None, R.MISSING["group"])
    else:
        out["group"] = (W["group"], min(1.0, cap / (10 * gs)), f"Room for your group of {_fmt_num(gs)}", None)
    return out


def match_raw(comps: dict) -> float:
    tw = sum(w for w, *_ in comps.values())
    if tw <= 0:
        return 0.0
    return 100 * sum(w * s for w, s, *_ in comps.values()) / tw


def rank_value(match: float, conf, energy: float = 1.0) -> float:
    """rank_score = match · (0.75 + 0.25·confidence) · energy_penalty (energy_penalty = 1 unless demoted)."""
    conf = num(conf) or 0.0
    return match * (C.RANK_BASE + C.RANK_CONF * conf) * energy


def energy_penalty(comps: dict) -> float:
    """1.0 unless the venue's KNOWN crowd/dancing contradict the request (e.g. a confirmed-empty bar for a
    'crowd 4, want dancing' group). Unknown values never trigger it, so missing data is never punished twice."""
    # unweighted mean of the KNOWN crowd/dancing component scores (specs SCORING §9 energy_fit)
    known = [comps[k][1] for k in ("crowd", "dancing") if comps[k][0] > 0 and comps[k][3] is None]
    if not known:
        return 1.0
    fit = sum(known) / len(known)
    return 1.0 if fit >= C.ENERGY_FIT_MIN else C.ENERGY_PENALTY_FLOOR + fit


def _lookup(venue: dict, key: str):
    v = clean(venue.get(key))
    if v is not None:
        return v
    try:
        if key == "cluster_label":
            from . import clustering
            return clustering.label_for(venue.get("venue_id"))
        if key == "cluster_description":
            from . import clustering
            return clustering.description_for(venue.get("venue_id"))
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
    energy = energy_penalty(comps)
    rs = rank_value(match, st.get("confidence"), energy)
    excl = _exclusion(prefs, st, venue, dist, now)
    reasons = R.reasons(comps)
    missing = R.missing(comps)
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
        "cluster_description": _lookup(venue, "cluster_description"),
        "complaint_risk": None if cr is None else round_half_up(float(cr), 3),
        "is_synthetic": bool(st.get("is_synthetic") or truthy(venue.get("is_synthetic"))),
        "_rs": rs,
        "_energy": energy,
        "_dist": dist if dist is not None else 1e9,
    }


def recommend(prefs: dict, states, venues, now) -> list[dict]:
    """Rank `venues` for `prefs` at `now` (datetime or ISO). Order and fields follow specs' reference_scoring.

    Sorted by (excluded, -rank_score, distance_km, venue_id); `rank` is 1-based over the whole list, so excluded
    venues come last with excluded=true and excluded_reason set (frontend shows "N hidden by your limits").
    Venues in prefs.exclude_venue_ids are dropped. Unknown values never exclude; they are listed in `missing`.
    """
    now = to_dt(now)
    prefs = dict(prefs or {})
    skip = set(prefs.get("exclude_venue_ids") or [])
    st_by = by_key(rows(states))
    out = []
    for v in rows(venues):
        vid = v.get("venue_id") or v.get("license_id")
        if vid is None or vid in skip:
            continue
        v["venue_id"] = vid
        st = st_by.get(vid) or live_state.empty_state(vid)
        out.append(score_one(prefs, st, v, now))
    out.sort(key=lambda r: (r["excluded"], -r["rank_score"], r["_dist"], str(r["venue_id"])))
    for i, r in enumerate(out, 1):
        r["rank"] = i
        r.pop("_rs")
        r.pop("_dist")
        r.pop("_energy")
    return out
