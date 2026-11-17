"""Stub engine: same signatures as `recs` (CONTRACTS Python interface), formulas from specs
PRD §5 with the v2 §A constants. Used when `recs` is missing or raises."""

import math
from datetime import datetime, timedelta
from typing import Any

from .. import config as C
from ..timeutil import parse_ts, to_ny_iso
from .geo import haversine_km

ELIGIBLE_STATUS_WEIGHT = {"accepted": 1.0, "pending": 1.0, "disputed": C.DISPUTED_WEIGHT}


def _rows(data: Any) -> list[dict]:
    if data is None:
        return []
    if hasattr(data, "to_dict"):
        return data.to_dict("records")
    return list(data)


def _isnull(v: Any) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _age_min(ts: Any, now: datetime) -> float | None:
    """Minutes old, or None when outside [now - cutoff, now + skew]."""
    age = (now - parse_ts(ts)).total_seconds() / 60.0
    if age < -C.FUTURE_SKEW_MIN or age > C.INPUT_CUTOFF_MIN:
        return None
    return max(age, 0.0)


def _decay(age: float, half_life: float) -> float:
    return 0.5 ** (age / half_life)


def _wmean(pairs: list[tuple[float, float]]) -> float | None:
    tot = sum(w for _, w in pairs)
    return sum(x * w for x, w in pairs) / tot if tot > 0 else None


def _wmedian(pairs: list[tuple[float, float]]) -> float | None:
    pairs = sorted(p for p in pairs if p[1] > 0)
    tot = sum(w for _, w in pairs)
    if tot <= 0:
        return None
    acc = 0.0
    for x, w in pairs:
        acc += w
        if acc >= tot / 2:
            return x
    return pairs[-1][0]


def _thin(pairs: list[tuple[Any, float]]) -> bool:
    return sum(w for _, w in pairs) < C.MIN_FIELD_WEIGHT


class StubEngine:
    name = "stub"

    # ---------------- live state ----------------
    def compute(self, venue_id: str, reports: Any, updates: Any, now: datetime) -> dict:
        crowd, dance, line, cover, genre = [], [], [], [], {}
        genre_total = 0.0
        crowd_scouts: set[str] = set()
        recent, prior = [], []
        ages: list[float] = []
        n_reports = 0
        sources: set[str] = set()
        synthetic = False

        for r in _rows(reports):
            if r.get("venue_id", venue_id) != venue_id:
                continue
            w_status = ELIGIBLE_STATUS_WEIGHT.get(r.get("status") or "accepted", 0.0)
            age = _age_min(r["ts"], now)
            if age is None or w_status == 0:
                continue
            rep = r.get("reputation")
            rep = C.NEW_SCOUT_REPUTATION if _isnull(rep) else float(rep)
            w_rep = 0.25 + 0.75 * rep
            w_ver = 1.0 if int(r.get("verified_presence") or 0) == 1 else C.UNVERIFIED_WEIGHT
            base = w_rep * w_ver * w_status
            w_e = base * _decay(age, C.HALF_LIFE_ENERGY_MIN)
            w_s = base * _decay(age, C.HALF_LIFE_SCOUT_COVER_GENRE_MIN)
            n_reports += 1
            ages.append(age)
            sources.add("scout")
            synthetic = synthetic or bool(r.get("is_synthetic"))
            if not _isnull(r.get("crowd")):
                crowd.append((float(r["crowd"]), w_e))
                crowd_scouts.add(str(r.get("scout_id")))
                if age <= 30:
                    recent.append((float(r["crowd"]), w_e))
                elif age <= 90:
                    prior.append((float(r["crowd"]), w_e))
            if not _isnull(r.get("dancing")):
                dance.append((float(r["dancing"]), w_e))
            if not _isnull(r.get("line_minutes")):
                line.append((float(r["line_minutes"]), w_e))
            if not _isnull(r.get("cover_usd")):
                cover.append((float(r["cover_usd"]), w_s))
            if r.get("music_genre"):
                genre[r["music_genre"]] = genre.get(r["music_genre"], 0.0) + w_s
                genre_total += w_s

        op_weight = 0.0
        for u in _rows(updates):
            if u.get("venue_id", venue_id) != venue_id:
                continue
            age = _age_min(u["ts"], now)
            if age is None:
                continue
            w = C.OPERATOR_SOURCE_WEIGHT * _decay(age, C.HALF_LIFE_OPERATOR_MIN)
            used = False
            if not _isnull(u.get("cover_usd")):
                cover.append((float(u["cover_usd"]), w))
                used = True
            gs = [g for g in str(u.get("genres") or "").split("|") if g]
            for g in gs:
                genre[g] = genre.get(g, 0.0) + w / len(gs)
            if gs:
                genre_total += w
                used = True
            if used or u.get("dj") or u.get("offer") or u.get("event"):
                op_weight += w
                ages.append(age)
                sources.add("venue_update")
                synthetic = synthetic or bool(u.get("is_synthetic"))

        crowd_v = None if _thin(crowd) else _wmean(crowd)
        dance_v = None if _thin(dance) else _wmean(dance)
        line_v = None if _thin(line) else _wmedian(line)
        cover_v = None if _thin(cover) else _wmedian(cover)
        if genre_total < C.MIN_FIELD_WEIGHT:
            genres_v = None
        else:
            shares = sorted(
                ((g, w / genre_total) for g, w in genre.items()), key=lambda x: (-x[1], x[0])
            )
            genres_v = [g for g, s in shares if s >= C.GENRE_SHARE_MIN]

        vibe = None
        if crowd_v is not None:
            terms = [(C.VIBE_WEIGHTS["crowd"], (crowd_v - 1) / 4)]
            if dance_v is not None:
                terms.append((C.VIBE_WEIGHTS["dance"], dance_v / 2))
            if line_v is not None:
                terms.append((C.VIBE_WEIGHTS["line"], min(line_v, 30) / 30))
            vibe = round(100 * sum(a * x for a, x in terms) / sum(a for a, _ in terms))

        conf: float | None
        if crowd:
            W = sum(w for _, w in crowd)
            support = 1 - math.exp(-W / C.CONFIDENCE_K)
            mu = _wmean(crowd) or 0.0
            sd = math.sqrt(sum(w * (x - mu) ** 2 for x, w in crowd) / W)
            agree = 1 - 0.5 * min(1.0, sd / 1.5)
            diverse = 1.0 if len(crowd_scouts) >= 2 else 0.6
            conf = round(support * agree * diverse, 2)
        elif op_weight > 0:
            conf = round(min(0.25, 0.25 * op_weight), 2)
        else:
            conf = None

        trend = None
        wr, wp = sum(w for _, w in recent), sum(w for _, w in prior)
        if wr >= C.TREND_MIN_WEIGHT and wp >= C.TREND_MIN_WEIGHT:
            delta = (_wmean(recent) or 0) - (_wmean(prior) or 0)
            trend = (
                "rising"
                if delta >= C.TREND_DELTA
                else "falling"
                if delta <= -C.TREND_DELTA
                else "steady"
            )

        if vibe is None or conf is None or conf < C.DISPLAY_LOW:
            display = "none"
        elif conf < C.DISPLAY_SHOW:
            display = "low"
        else:
            display = "show"

        return {
            "venue_id": venue_id,
            "crowd": None if crowd_v is None else round(crowd_v, 1),
            "dancing": None if dance_v is None else round(dance_v, 1),
            "line_minutes": None if line_v is None else int(round(line_v)),
            "cover_usd": None if cover_v is None else int(round(cover_v)),
            "music_genres": genres_v,
            "vibe_score": vibe,
            "confidence": conf,
            "freshness_minutes": int(min(ages)) if ages else None,
            "n_reports": n_reports,
            "trend": trend,
            "sources": sorted(sources),
            "display": display,
            "predicted_crowd": None,
            "predicted_source": None,
            "is_synthetic": synthetic,
        }

    def compute_all(self, reports_df: Any, updates_df: Any, now: datetime) -> list[dict]:
        reports, updates = _rows(reports_df), _rows(updates_df)
        by_r: dict[str, list] = {}
        by_u: dict[str, list] = {}
        for r in reports:
            by_r.setdefault(r["venue_id"], []).append(r)
        for u in updates:
            by_u.setdefault(u["venue_id"], []).append(u)
        ids = sorted(set(by_r) | set(by_u))
        return [self.compute(v, by_r.get(v, []), by_u.get(v, []), now) for v in ids]

    # ---------------- recommend ----------------
    def recommend(self, prefs: dict, states: Any, venues: Any, now: datetime) -> list[dict]:
        state_by = {s["venue_id"]: s for s in _rows(states)}
        out = []
        for v in _rows(venues):
            s = state_by.get(v["venue_id"]) or self.compute(v["venue_id"], [], [], now)
            out.append(self._score(prefs, s, v))
        ok = sorted(
            (r for r in out if not r["excluded"]),
            key=lambda r: (-r["rank_score"], r["distance_km"] if r["distance_km"] is not None else 1e9),
        )
        bad = sorted(
            (r for r in out if r["excluded"]),
            key=lambda r: (-r["rank_score"], r["distance_km"] if r["distance_km"] is not None else 1e9),
        )
        ranked = ok + bad
        for i, r in enumerate(ranked, 1):
            r["rank"] = i
        return ranked

    def _score(self, prefs: dict, s: dict, v: dict) -> dict:
        W = C.MATCH_WEIGHTS
        comps: dict[str, tuple[float, float]] = {}  # k -> (weight, score)
        missing: list[str] = []
        reasons_by: dict[str, str] = {}
        excluded_reason = None

        def unknown(k: str, msg: str) -> None:
            comps[k] = (W[k], C.UNKNOWN_COMPONENT)
            if msg not in missing:
                missing.append(msg)

        # distance
        dist = None
        if prefs.get("lat") is not None and prefs.get("lon") is not None:
            dist = round(haversine_km(prefs["lat"], prefs["lon"], v["lat"], v["lon"]), 2)
        max_d = prefs.get("max_distance_km")
        if max_d:
            if dist is None:
                unknown("distance", "your location unknown")
            else:
                comps["distance"] = (W["distance"], max(0.0, 1 - dist / max_d))
                reasons_by["distance"] = f"{dist:.1f} km away"
                if dist > max_d:
                    excluded_reason = f"{dist:.1f} km away, over your {max_d:g} km"

        # genre
        pref_g = set(prefs.get("genres") or [])
        live_g = s.get("music_genres")
        static_g = {g for g in str(v.get("genres") or "").split("|") if g}
        if not pref_g:
            comps["genre"] = (W["genre"], 1.0)
        elif live_g and pref_g & set(live_g):
            comps["genre"] = (W["genre"], 1.0)
            g = sorted(pref_g & set(live_g))[0]
            reasons_by["genre"] = f"{g.capitalize()} playing ({_ev(s)})"
        elif static_g & pref_g:
            comps["genre"] = (W["genre"], 0.6)
            reasons_by["genre"] = f"Usually plays {sorted(static_g & pref_g)[0]}"
        elif live_g or static_g:
            comps["genre"] = (W["genre"], 0.0)
        else:
            unknown("genre", "music unknown")

        # dancing
        want = prefs.get("want_dancing")
        if want is not None:
            d = s.get("dancing")
            if d is None:
                unknown("dancing", "no dancing reports")
            else:
                comps["dancing"] = (W["dancing"], d / 2 if want else 1 - d / 2)
                if want and d >= 1:
                    reasons_by["dancing"] = f"Dancing reported ({s.get('n_reports', 0)} reports)"
                elif not want and d < 1:
                    reasons_by["dancing"] = "Little dancing, good for talking"

        # crowd
        cp = prefs.get("crowd_pref")
        if cp is not None:
            c = s.get("crowd")
            if c is None:
                unknown("crowd", "crowd not reported tonight")
            else:
                comps["crowd"] = (W["crowd"], max(0.0, 1 - abs(c - cp) / 4))
                reasons_by["crowd"] = f"Crowd {c:.1f}/5, near your {cp}"

        # line
        ml = prefs.get("max_line_minutes")
        if ml is not None:
            ln = s.get("line_minutes")
            if ln is None:
                unknown("line", "line not reported tonight")
            elif ln > ml:
                comps["line"] = (W["line"], 0.0)
                excluded_reason = excluded_reason or f"line ~{ln} min over your {ml}"
            else:
                comps["line"] = (W["line"], 1 - 0.5 * ln / ml if ml else 1.0)
                reasons_by["line"] = f"Line ~{ln} min, under your {ml}"

        # cover
        mc = prefs.get("max_cover_usd")
        if mc is not None:
            cv = s.get("cover_usd")
            if cv is None:
                unknown("cover", "cover not reported tonight")
            elif cv > mc:
                comps["cover"] = (W["cover"], 0.0)
                excluded_reason = excluded_reason or f"cover ${cv} over your ${mc:g}"
            else:
                comps["cover"] = (W["cover"], 1.0 if cv == 0 or not mc else 1 - 0.5 * cv / mc)
                reasons_by["cover"] = "No cover" if cv == 0 else f"Cover ${cv}, under your ${mc:g}"

        # group
        gsz = prefs.get("group_size")
        if gsz:
            cap = v.get("capacity")
            if _isnull(cap):
                unknown("group", "capacity unknown")
            else:
                comps["group"] = (W["group"], min(1.0, float(cap) / (10 * gsz)))

        if s.get("vibe_score") is None:
            missing.append("no fresh reports — scores are low confidence")

        wsum = sum(w for w, _ in comps.values())
        match = round(100 * sum(w * x for w, x in comps.values()) / wsum) if wsum else 0
        conf = s.get("confidence") or 0.0
        rank_score = round(match * (0.75 + 0.25 * conf), 1)
        top = sorted(
            (k for k in reasons_by if comps.get(k, (0, 0))[1] >= 0.6),
            key=lambda k: -comps[k][0] * comps[k][1],
        )
        return {
            "venue_id": v["venue_id"],
            "name": v.get("display_name") or v.get("name"),
            "match_score": match,
            "vibe_score": s.get("vibe_score"),
            "confidence": s.get("confidence"),
            "distance_km": dist,
            "reasons": [reasons_by[k] for k in top[:3]],
            "missing": missing,
            "excluded": excluded_reason is not None,
            "excluded_reason": excluded_reason,
            "rank_score": rank_score,
            "rank": 0,
            "cluster_label": None,
            "is_synthetic": bool(s.get("is_synthetic") or v.get("is_synthetic")),
        }

    # ---------------- plan night ----------------
    def plan_night(
        self, prefs: dict, states: Any, venues: Any, start_time: datetime, n_stops: int = 3
    ) -> list[dict]:
        venues = _rows(venues)
        vby = {v["venue_id"]: v for v in venues}
        skip = set(prefs.get("exclude_venue_ids") or [])
        recs = [
            r
            for r in self.recommend(prefs, states, venues, start_time)
            if not r["excluded"] and r["venue_id"] not in skip
        ][:8]
        dwell = int(prefs.get("dwell_minutes") or 60)
        budget = float(prefs.get("max_total_walk_minutes") or 30)
        pos = (prefs.get("lat"), prefs.get("lon"))
        t = start_time
        walked = 0.0
        stops: list[dict] = []
        while recs and len(stops) < n_stops:
            best, best_obj, best_km = None, -1e9, 0.0
            for r in recs:
                v = vby[r["venue_id"]]
                km = 0.0 if pos[0] is None else haversine_km(pos[0], pos[1], v["lat"], v["lon"])
                if stops and walked + km / C.WALK_KMH * 60 > budget:
                    continue
                obj = r["rank_score"] - 10 * km
                if obj > best_obj:
                    best, best_obj, best_km = r, obj, km
            if best is None:
                break
            v = vby[best["venue_id"]]
            walk_min = round(best_km / C.WALK_KMH * 60) if stops or pos[0] is not None else 0
            walked += walk_min if stops else 0
            arrive = t + timedelta(minutes=walk_min)
            leave = arrive + timedelta(minutes=dwell)
            stops.append(
                {
                    "order": len(stops) + 1,
                    "venue_id": best["venue_id"],
                    "name": best["name"],
                    "lat": v["lat"],
                    "lon": v["lon"],
                    "arrive_at": to_ny_iso(arrive),
                    "leave_at": to_ny_iso(leave),
                    "walk_minutes_from_prev": walk_min,
                    "distance_km": round(best_km, 2),
                    "expected_vibe": best["vibe_score"],
                    "match_score": best["match_score"],
                    "confidence": best["confidence"],
                    "reasons": best["reasons"],
                    "is_synthetic": best["is_synthetic"],
                }
            )
            recs.remove(best)
            pos, t = (v["lat"], v["lon"]), leave
        return stops


def _ev(s: dict) -> str:
    n, f = s.get("n_reports") or 0, s.get("freshness_minutes")
    return f"{n} reports, {f} min ago" if f is not None else f"{n} reports"
