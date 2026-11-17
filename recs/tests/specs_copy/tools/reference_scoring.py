"""Reference scoring oracle for docs/specs/SCORING.md (test tool, stdlib only).

Purpose: a line-by-line translation of SCORING.md used to compute and check the
golden vectors. It is NOT imported by the app; ml-recs owns production code
(`recs.live_state`, `recs.scoring`). Run with `python -I`.

Public functions mirror the Contracts Python interface:
    compute_state(venue_id, reports, updates, now) -> dict   # Live Venue State
    compute_all(reports, updates, now) -> list[dict]
    recommend(prefs, states, venues, now) -> list[dict]       # Recommendation results
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

PARAMS_PATH = Path(__file__).resolve().parent.parent / "PARAMETERS.md"


def load_params(path: Path = PARAMS_PATH) -> dict[str, float]:
    """Return the first ```json block of PARAMETERS.md as a dict."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\n(.*?)\n```", text, re.S)
    if not match:
        raise ValueError("PARAMETERS.md has no ```json block")
    return json.loads(match.group(1))


P = load_params()

STATUS_WEIGHT = {"accepted": 1.0, "pending": 1.0, "disputed": P["w_disputed"],
                 "flagged": 0.0, "removed": 0.0}
GENRE_LABELS = {"hip-hop": "Hip-hop", "r&b": "R&B", "edm": "EDM", "top-40": "Top 40",
                "soul-funk": "Soul/funk"}
COMPONENTS = ["genre", "dancing", "crowd", "line", "cover", "distance", "group"]


# ---------------------------------------------------------------- helpers
def parse_ts(value: str | datetime) -> datetime:
    """Parse an ISO 8601 timestamp with offset."""
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


def round_half_up(x: float, ndigits: int = 0) -> float:
    """Round half away from zero (SCORING §0). Goldens avoid exact ties."""
    q = 10 ** ndigits
    return math.copysign(math.floor(abs(x) * q + 0.5) / q, x)


def age_minutes(ts: str | datetime, now: datetime) -> float:
    """Minutes between ts and now (negative if ts is in the future)."""
    return (now - parse_ts(ts)).total_seconds() / 60.0


def decay(age: float, half_life: float) -> float:
    """w_time = 0.5 ** (max(age, 0) / H)."""
    return 0.5 ** (max(age, 0.0) / half_life)


def in_window(age: float) -> bool:
    """Eligibility by time: −future_skew ≤ age ≤ cutoff."""
    return -P["future_skew_min"] <= age <= P["cutoff_age_min"]


def wmean(pairs: list[tuple[float, float]]) -> float:
    """Weighted mean of (value, weight) pairs (weights sum > 0)."""
    return sum(v * w for v, w in pairs) / sum(w for _, w in pairs)


def wsd(pairs: list[tuple[float, float]]) -> float:
    """Weighted population standard deviation."""
    mu = wmean(pairs)
    return math.sqrt(sum(w * (v - mu) ** 2 for v, w in pairs) / sum(w for _, w in pairs))


def wmedian(pairs: list[tuple[float, float]]) -> float:
    """Smallest value whose cumulative weight ≥ half the total weight."""
    total = sum(w for _, w in pairs)
    cum = 0.0
    for v, w in sorted(pairs, key=lambda p: p[0]):
        cum += w
        if cum >= total / 2 - 1e-12:
            return v
    raise ValueError("empty pairs")


def split_genres(value: Any) -> list[str]:
    """Genres may be a list or a pipe-separated string; null → []."""
    if value is None:
        return []
    if isinstance(value, str):
        return [g for g in value.split("|") if g]
    return list(value)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km (R = earth_radius_km)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * P["earth_radius_km"] * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- weights
def scout_base_weight(report: dict) -> float:
    """w_rep · w_ver · w_status (time decay applied per field)."""
    r = report.get("reputation")
    r = P["rep_new_scout"] if r is None else float(r)
    w_rep = P["rep_base"] + P["rep_slope"] * r
    w_ver = 1.0 if report.get("verified_presence") == 1 else P["w_unverified"]
    w_status = STATUS_WEIGHT[report.get("status") or "accepted"]
    return w_rep * w_ver * w_status


def eligible_reports(reports: Iterable[dict], now: datetime) -> list[tuple[dict, float, float]]:
    """(report, age, base_weight) for reports with weight > 0 inside the window."""
    out = []
    for rep in reports:
        age = age_minutes(rep["ts"], now)
        base = scout_base_weight(rep)
        if in_window(age) and base > 0:
            out.append((rep, age, base))
    return out


def eligible_updates(updates: Iterable[dict], now: datetime) -> list[tuple[dict, float, float]]:
    """(update, age, w_src) for operator updates inside the window."""
    out = []
    for upd in updates:
        age = age_minutes(upd["ts"], now)
        if in_window(age):
            out.append((upd, age, P["w_operator"]))
    return out


def scout_pairs(reps: list, field: str, half_life: float) -> list[tuple[float, float]]:
    """(value, weight) pairs for a non-null scout field."""
    return [(r[field], base * decay(age, half_life)) for r, age, base in reps
            if r.get(field) is not None]


def thick(pairs: list[tuple[float, float]]) -> bool:
    """A field is stated only if its total weight ≥ min_field_weight."""
    return bool(pairs) and sum(w for _, w in pairs) >= P["min_field_weight"] - 1e-12


# ---------------------------------------------------------------- live state
def genre_vote(reps: list, upds: list) -> list[str] | None:
    """Weighted genre vote; each listed genre gets the input's full weight."""
    votes: dict[str, float] = {}
    total = 0.0
    for r, age, base in reps:
        if r.get("music_genre"):
            w = base * decay(age, P["H_scout_cover_genre_min"])
            votes[r["music_genre"]] = votes.get(r["music_genre"], 0.0) + w
            total += w
    for u, age, w_src in upds:
        genres = split_genres(u.get("genres"))
        if genres:
            w = w_src * decay(age, P["H_operator_min"])
            for g in genres:
                votes[g] = votes.get(g, 0.0) + w
            total += w
    if total < P["min_field_weight"] - 1e-12:
        return None
    keep = [(g, v / total) for g, v in votes.items() if v / total >= P["genre_share_min"]]
    return [g for g, _ in sorted(keep, key=lambda x: (-x[1], x[0]))]


def cover_estimate(reps: list, upds: list) -> float | None:
    """Weighted median of scout (H 60) and operator (H 120 · w_src) cover."""
    pairs = scout_pairs(reps, "cover_usd", P["H_scout_cover_genre_min"])
    pairs += [(u["cover_usd"], w * decay(age, P["H_operator_min"]))
              for u, age, w in upds if u.get("cover_usd") is not None]
    return wmedian(pairs) if thick(pairs) else None


def confidence_parts(reps: list, upds: list) -> dict:
    """W, support, sd_w, agree, diverse and raw confidence (SCORING §5)."""
    pairs = scout_pairs(reps, "crowd", P["H_crowd_min"])
    if not pairs:
        op_w = sum(w * decay(age, P["H_operator_min"]) for _, age, w in upds)
        conf = min(P["operator_conf_cap"], P["operator_conf_cap"] * op_w) if upds else 0.0
        return {"W": 0.0, "operator_W": op_w, "conf_raw": conf}
    W = sum(w for _, w in pairs)
    support = 1 - math.exp(-W / P["conf_k"])
    sd = wsd(pairs)
    agree = 1 - P["agree_penalty"] * min(1.0, sd / P["agree_sd_scale"])
    scouts = {r["scout_id"] for r, _, _ in reps if r.get("crowd") is not None}
    diverse = 1.0 if len(scouts) >= 2 else P["diverse_single_scout"]
    return {"W": W, "support": support, "sd_w": sd, "agree": agree, "diverse": diverse,
            "conf_raw": support * agree * diverse}


def vibe_raw(crowd: float | None, dancing: float | None, line: float | None) -> float | None:
    """100 · Σ a_k x_k / Σ a_k over available terms; crowd null → null."""
    if crowd is None:
        return None
    terms = [(P["vibe_w_crowd"], (crowd - 1) / 4)]
    if dancing is not None:
        terms.append((P["vibe_w_dance"], dancing / 2))
    if line is not None:
        terms.append((P["vibe_w_line"], min(line, P["line_cap_min"]) / P["line_cap_min"]))
    return 100 * sum(a * x for a, x in terms) / sum(a for a, _ in terms)


def trend(reps: list) -> str | None:
    """rising / steady / falling / null from recent vs prior crowd windows."""
    pairs_r, pairs_p = [], []
    for r, age, base in reps:
        if r.get("crowd") is None:
            continue
        pair = (r["crowd"], base * decay(age, P["H_crowd_min"]))
        if age <= P["trend_recent_min"]:
            pairs_r.append(pair)
        elif age <= P["trend_prior_min"]:
            pairs_p.append(pair)
    for pairs in (pairs_r, pairs_p):
        if sum(w for _, w in pairs) < P["trend_min_weight"]:
            return None
    delta = wmean(pairs_r) - wmean(pairs_p)
    if delta >= P["trend_delta"] - 1e-9:
        return "rising"
    if delta <= -P["trend_delta"] + 1e-9:
        return "falling"
    return "steady"


def display_band(vibe: int | None, conf: float) -> str:
    """show / low / none (SCORING §5 display rule)."""
    if vibe is None or conf < P["display_low_min"]:
        return "none"
    return "show" if conf >= P["display_show_min"] else "low"


def field_estimates(reps: list, upds: list) -> dict:
    """Unrounded crowd, dancing, line, cover and genres (null when thin)."""
    crowd = scout_pairs(reps, "crowd", P["H_crowd_min"])
    dance = scout_pairs(reps, "dancing", P["H_crowd_min"])
    line = scout_pairs(reps, "line_minutes", P["H_crowd_min"])
    return {"crowd": wmean(crowd) if thick(crowd) else None,
            "dancing": wmean(dance) if thick(dance) else None,
            "line_minutes": wmedian(line) if thick(line) else None,
            "cover_usd": cover_estimate(reps, upds),
            "music_genres": genre_vote(reps, upds)}


def compute_state(venue_id: str, reports: list[dict], updates: list[dict],
                  now: str | datetime, debug: bool = False) -> dict:
    """Live Venue State for one venue (inputs already filtered to the venue)."""
    now = parse_ts(now)
    reps = eligible_reports([r for r in reports if r["venue_id"] == venue_id], now)
    upds = eligible_updates([u for u in updates if u["venue_id"] == venue_id], now)
    est = field_estimates(reps, upds)
    parts = confidence_parts(reps, upds)
    v_raw = vibe_raw(est["crowd"], est["dancing"], est["line_minutes"])
    vibe = None if v_raw is None else int(round_half_up(v_raw))
    conf = round_half_up(parts["conf_raw"], 2)
    ages = [a for _, a, _ in reps] + [a for _, a, _ in upds]
    state = {
        "venue_id": venue_id,
        "crowd": None if est["crowd"] is None else round_half_up(est["crowd"], 1),
        "dancing": None if est["dancing"] is None else round_half_up(est["dancing"], 1),
        "line_minutes": None if est["line_minutes"] is None else int(est["line_minutes"]),
        "cover_usd": None if est["cover_usd"] is None else int(est["cover_usd"]),
        "music_genres": est["music_genres"],
        "vibe_score": vibe, "confidence": conf,
        "freshness_minutes": int(math.floor(max(0.0, min(ages)))) if ages else None,
        "n_reports": len(reps),
        "trend": trend(reps),
        "sources": (["scout"] if reps else []) + (["venue_update"] if upds else []),
        "display": display_band(vibe, conf),
        "is_synthetic": any(x[0].get("is_synthetic", 0) == 1 for x in reps + upds),
    }
    if debug:
        state["_debug"] = {**parts, "vibe_raw": v_raw, **{f"{k}_raw": v for k, v in est.items()
                                                         if k != "music_genres"}}
    return state


def compute_all(reports: list[dict], updates: list[dict], now: str | datetime,
                venue_ids: Iterable[str] | None = None) -> list[dict]:
    """States for every venue seen in inputs (or in venue_ids), sorted by venue_id."""
    ids = set(venue_ids or []) | {r["venue_id"] for r in reports} | {u["venue_id"] for u in updates}
    return [compute_state(v, reports, updates, now) for v in sorted(ids)]


def ui_labels(state: dict) -> dict:
    """Frontend-derived labels: vibe band and stale tag (Contracts §J)."""
    vibe, fresh = state["vibe_score"], state["freshness_minutes"]
    if vibe is None:
        band = None
    elif vibe >= P["vibe_band_packed_min"]:
        band = "Packed"
    elif vibe >= P["vibe_band_lively_min"]:
        band = "Lively"
    else:
        band = "Chill"
    return {"vibe_label": band, "stale": fresh is not None and fresh > P["stale_tag_min"]}


# ---------------------------------------------------------------- match
def genre_label(slug: str) -> str:
    """Display label for a genre slug."""
    return GENRE_LABELS.get(slug, slug[:1].upper() + slug[1:])


def comp_genre(prefs: dict, state: dict, venue: dict) -> tuple[float | None, str | None, str | None]:
    """Genre component → (score or None if weight 0, reason, missing)."""
    want = prefs.get("genres") or []
    if not want:
        return 1.0, None, None
    live = state.get("music_genres") or []
    static = split_genres(venue.get("genres"))
    hit = [g for g in live if g in want]
    if hit:
        n, f = state["n_reports"], state["freshness_minutes"]
        ev = f"({n} reports, {f} min ago)" if n else "(posted by venue)"
        return 1.0, f"{genre_label(hit[0])} playing {ev}", None
    s_hit = [g for g in static if g in want]
    if s_hit:
        return P["static_genre_score"], f"Usually plays {genre_label(s_hit[0])}", None
    if live or static:
        return 0.0, None, None
    return P["unknown_component"], None, "music unknown"


def comp_dancing(prefs: dict, state: dict) -> tuple[float | None, str | None, str | None]:
    """Dancing component; want_dancing null → weight 0 (None)."""
    want, d = prefs.get("want_dancing"), state.get("dancing")
    if want is None:
        return None, None, None
    if d is None:
        return P["unknown_component"], None, "no dancing reports"
    if want:
        return d / 2, f"Dancing reported ({state['n_reports']} reports)", None
    return 1 - d / 2, "Low-key, little dancing", None


def comp_crowd(prefs: dict, state: dict) -> tuple[float | None, str | None, str | None]:
    """Crowd component: 1 − |crowd − crowd_pref| / 4."""
    pref, c = prefs.get("crowd_pref"), state.get("crowd")
    if pref is None:
        return None, None, None
    if c is None:
        return P["unknown_component"], None, "no fresh reports — scores are low confidence"
    return 1 - abs(c - pref) / 4, f"Crowd {c:g} of 5, close to your {pref}", None


def comp_limit(value: float | None, limit: float | None, what: str, unit_fmt: str):
    """Line/cover component: 1 − 0.5·value/limit (limit null → weight 0)."""
    if limit is None:
        return None, None, None
    if value is None:
        return P["unknown_component"], None, f"{what} not reported tonight"
    if what == "cover" and value == 0:
        return 1.0, "No cover", None
    s = max(0.0, 1 - 0.5 * value / limit) if limit > 0 else 0.0
    return s, unit_fmt.format(v=value, m=limit), None


def comp_distance(prefs: dict, dist: float | None):
    """Distance component: 1 − distance / max_distance."""
    limit = prefs.get("max_distance_km")
    if limit is None:
        return None, None, None
    if dist is None:
        return P["unknown_component"], None, "your location unknown"
    text = "Under 0.1 km away" if dist < 0.1 else f"{dist:.1f} km away"
    return max(0.0, 1 - dist / limit), text, None


def comp_group(prefs: dict, venue: dict):
    """Group component: min(1, capacity / (10 · group_size))."""
    g, cap = prefs.get("group_size"), venue.get("capacity")
    if not g:
        return None, None, None
    if cap is None:
        return P["unknown_component"], None, "capacity unknown"
    return min(1.0, cap / (P["group_capacity_per_person"] * g)), f"Room for your group of {g}", None


def venue_distance(prefs: dict, venue: dict) -> float | None:
    """Haversine km from prefs lat/lon to venue lat/lon, or None if unknown."""
    if None in (prefs.get("lat"), prefs.get("lon"), venue.get("lat"), venue.get("lon")):
        return None
    return haversine_km(prefs["lat"], prefs["lon"], venue["lat"], venue["lon"])


def exclusion(prefs: dict, state: dict, venue: dict, dist: float | None) -> str | None:
    """First broken hard limit on a KNOWN value, as excluded_reason; else None."""
    if venue.get("is_open_now") is False:
        return "closed now"
    if prefs.get("launch_only") and venue.get("is_launch") is False:
        return "outside launch area"
    lim = prefs.get("max_distance_km")
    if lim is not None and dist is not None and dist > lim:
        return f"{dist:.1f} km away, over your {lim:g} km"
    lim, cov = prefs.get("max_cover_usd"), state.get("cover_usd")
    if lim is not None and cov is not None and cov > lim:
        return f"cover ${cov} over your ${lim}"
    lim, line = prefs.get("max_line_minutes"), state.get("line_minutes")
    if lim is not None and line is not None and line > lim:
        return f"line ~{line} min over your {lim}"
    return None


def components(prefs: dict, state: dict, venue: dict, dist: float | None) -> dict:
    """All seven (score, reason, missing) tuples keyed by component name."""
    return {
        "genre": comp_genre(prefs, state, venue),
        "dancing": comp_dancing(prefs, state),
        "crowd": comp_crowd(prefs, state),
        "line": comp_limit(state.get("line_minutes"), prefs.get("max_line_minutes"), "line",
                           "Line ~{v} min, under your {m}"),
        "cover": comp_limit(state.get("cover_usd"), prefs.get("max_cover_usd"), "cover",
                            "Cover ${v}, under your ${m}"),
        "distance": comp_distance(prefs, dist),
        "group": comp_group(prefs, venue),
    }


def match_one(prefs: dict, state: dict, venue: dict) -> dict:
    """Recommendation result for one venue (before ranking)."""
    dist = venue_distance(prefs, venue)
    comps = components(prefs, state, venue, dist)
    used = {k: (P[f"match_w_{k}"], c) for k, c in comps.items() if c[0] is not None}
    raw = 100 * sum(w * c[0] for w, c in used.values()) / sum(w for w, _ in used.values())
    cands = [(w * c[0], COMPONENTS.index(k), c[1]) for k, (w, c) in used.items()
             if c[1] and c[0] >= P["reason_min_component"]]
    reasons = [r for _, _, r in sorted(cands, key=lambda x: (-x[0], x[1]))][: int(P["max_reasons"])]
    match = int(round_half_up(raw))
    conf = state.get("confidence") or 0.0
    why = exclusion(prefs, state, venue, dist)
    return {
        "venue_id": venue["venue_id"], "name": venue.get("name"),
        "match_score": match, "vibe_score": state.get("vibe_score"), "confidence": conf,
        "distance_km": None if dist is None else round_half_up(dist, 2),
        "reasons": reasons, "missing": [c[2] for c in comps.values() if c[2]],
        "excluded": why is not None, "excluded_reason": why,
        "rank_score": round_half_up(match * (P["rank_conf_base"] + P["rank_conf_slope"] * conf), 1),
        "is_synthetic": bool(state.get("is_synthetic")),
        "_match_raw": raw,
    }


def empty_state(venue_id: str) -> dict:
    """State used when a venue has no inputs at all."""
    return compute_state(venue_id, [], [], "2000-01-01T00:00:00-05:00")


def recommend(prefs: dict, states: list[dict], venues: list[dict], now: str | datetime,
              debug: bool = False) -> list[dict]:
    """Sorted Recommendation results: non-excluded by rank_score desc, then distance."""
    by_id = {s["venue_id"]: s for s in states}
    skip = set(prefs.get("exclude_venue_ids") or [])
    recs = [match_one(prefs, by_id.get(v["venue_id"]) or empty_state(v["venue_id"]), v)
            for v in venues if v["venue_id"] not in skip]
    recs.sort(key=lambda r: (r["excluded"], -r["rank_score"],
                             r["distance_km"] if r["distance_km"] is not None else 1e9,
                             r["venue_id"]))
    for i, rec in enumerate(recs, start=1):
        rec["rank"] = i
        if not debug:
            rec.pop("_match_raw")
    return recs
