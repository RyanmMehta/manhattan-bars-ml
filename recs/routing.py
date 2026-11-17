"""Run My Night: multi-stop plan (specs PRD §5.12, CONTRACTS v2 §F stop shape).

Public:
    plan_night(prefs, states, venues, start_time, n_stops=3, *, predictor=None) -> list[dict]

Objective: Σ rank_score(at arrival) − 10·walk_km, walking 4.5 km/h, dwell prefs.dwell_minutes (60),
total walk ≤ prefs.max_total_walk_minutes (30), no repeats, each stop passes hard limits at its arrival time.
Solver: greedy best-marginal insertion, then swap-in / reorder local search; `exhaustive` is the oracle.
Forecast state at arrival: observed state decays (half-life 30 min) towards the crowd model's prediction
if a predictor is given, else stays at the observed values with decaying confidence. Forecasts never raise
confidence. Returns fewer than n_stops when fewer are feasible; never pads.
"""
from __future__ import annotations

import itertools
from datetime import timedelta

from . import config as C
from . import live_state, scoring
from .geo import haversine_km, walk_minutes
from .inputs import by_key, num, rows, round_half_up
from .timeutil import iso, to_dt


class _Ctx:
    def __init__(self, prefs, states, venues, start, predictor):
        self.prefs = prefs
        self.start = start
        self.st = by_key(rows(states))
        self.venues = by_key(rows(venues))
        self.predictor = predictor
        self.dwell = num(prefs.get("dwell_minutes")) or C.DEFAULT_DWELL_MIN
        mw = num(prefs.get("max_total_walk_minutes"))
        self.max_walk = C.DEFAULT_MAX_TOTAL_WALK_MIN if mw is None else mw
        self.origin = (num(prefs.get("lat")), num(prefs.get("lon")))
        self._cache: dict = {}
        self._pred: dict = {}

    def state(self, vid):
        return self.st.get(vid) or live_state.empty_state(vid)

    def predicted(self, vid, t):
        key = (vid, t.replace(second=0, microsecond=0, minute=(t.minute // 15) * 15))
        if key not in self._pred:
            val = None
            if self.predictor is not None:
                try:
                    val = self.predictor([vid], [key[1]])[0]
                except Exception:  # noqa: BLE001 - degrade (PRD N3)
                    val = None
            self._pred[key] = val
        return self._pred[key]

    def forecast(self, vid, t) -> dict:
        st = dict(self.state(vid))
        elapsed = max(0.0, (t - self.start).total_seconds() / 60.0)
        keep = 0.5 ** (elapsed / C.HALF_LIFE_FAST)
        pred = self.predicted(vid, t) if elapsed > 0 else None
        crowd = num(st.get("crowd"))
        if pred is not None:
            crowd = pred if crowd is None else keep * crowd + (1 - keep) * pred
        st["crowd"] = crowd
        st["confidence"] = (num(st.get("confidence")) or 0.0) * keep
        if crowd is not None:
            terms = [(C.VIBE_WEIGHTS["crowd"], (crowd - 1) / 4)]
            if num(st.get("dancing")) is not None:
                terms.append((C.VIBE_WEIGHTS["dance"], num(st["dancing"]) / 2))
            if num(st.get("line_minutes")) is not None:
                terms.append((C.VIBE_WEIGHTS["line"], min(num(st["line_minutes"]), C.LINE_CAP_MINUTES) / C.LINE_CAP_MINUTES))
            st["vibe_score"] = int(round_half_up(100 * sum(a * x for a, x in terms) / sum(a for a, _ in terms)))
        else:
            st["vibe_score"] = None
        return st

    def value(self, vid, t):
        """(rank_score, rec, forecast_state) at arrival time t; rec['excluded'] -> infeasible."""
        key = (vid, int(t.timestamp() // 60))
        if key not in self._cache:
            fst = self.forecast(vid, t)
            rec = scoring.score_one(self.prefs, fst, self.venues[vid], t)
            self._cache[key] = (rec["_rs"], rec, fst)
        return self._cache[key]

    def point(self, vid):
        v = self.venues[vid]
        return num(v.get("lat")), num(v.get("lon"))

    def leg_km(self, a, b):
        pa = self.origin if a is None else self.point(a)
        pb = self.point(b)
        d = haversine_km(pa[0], pa[1], pb[0], pb[1])
        return 0.0 if d is None else d

    def evaluate(self, seq):
        """Objective for a sequence, or None if infeasible."""
        t = self.start
        prev = None
        total_walk = 0.0
        obj = 0.0
        for vid in seq:
            km = self.leg_km(prev, vid)
            wm = walk_minutes(km)
            total_walk += wm
            if total_walk > self.max_walk + 1e-9:
                return None
            t = t + timedelta(minutes=wm)
            rs, rec, _ = self.value(vid, t)
            if rec["excluded"]:
                return None
            obj += rs - C.WALK_COST_PER_KM * km
            t = t + timedelta(minutes=self.dwell)
            prev = vid
        return obj


def _candidates(ctx: _Ctx, limit=C.ROUTING_CANDIDATES):
    excl = set(ctx.prefs.get("exclude_venue_ids") or [])
    recs = scoring.recommend(ctx.prefs, list(ctx.st.values()), list(ctx.venues.values()), ctx.start)
    return [r["venue_id"] for r in recs if not r["excluded"] and r["venue_id"] not in excl][:limit]


def greedy(ctx: _Ctx, cands, n_stops):
    seq: list = []
    while len(seq) < n_stops:
        best, best_obj = None, None
        for c in cands:
            if c in seq:
                continue
            o = ctx.evaluate(seq + [c])
            if o is not None and (best_obj is None or o > best_obj + 1e-9):
                best, best_obj = c, o
        if best is None:
            break
        seq.append(best)
    return seq


def local_search(ctx: _Ctx, seq, cands, n_stops):
    cur = ctx.evaluate(seq) if seq else 0.0
    improved = True
    while improved:
        improved = False
        neigh = []
        for i, j in itertools.combinations(range(len(seq)), 2):  # reorder (2-opt on a path = segment reversal)
            s = seq[:i] + list(reversed(seq[i:j + 1])) + seq[j + 1:]
            neigh.append(s)
        for i in range(len(seq)):  # swap-in an unused candidate
            for c in cands:
                if c not in seq:
                    neigh.append(seq[:i] + [c] + seq[i + 1:])
        if len(seq) < n_stops:  # insertion
            for c in cands:
                if c not in seq:
                    for i in range(len(seq) + 1):
                        neigh.append(seq[:i] + [c] + seq[i:])
        best, best_obj = None, cur
        for s in neigh:
            o = ctx.evaluate(s)
            if o is None:
                continue
            better = o > best_obj + 1e-9 or (len(s) > len(seq) and o >= best_obj - 1e-9)
            if better:
                best, best_obj = s, o
        if best is not None:
            seq, cur, improved = best, best_obj, True
    return seq, cur


def exhaustive(ctx: _Ctx, cands, n_stops):
    """Oracle: best feasible sequence over all permutations (longest feasible length first)."""
    for k in range(n_stops, 0, -1):
        best, best_obj = None, None
        for s in itertools.permutations(cands, k):
            o = ctx.evaluate(list(s))
            if o is not None and (best_obj is None or o > best_obj):
                best, best_obj = list(s), o
        if best is not None:
            return best, best_obj
    return [], 0.0


def _stops(ctx: _Ctx, seq):
    out = []
    t = ctx.start
    prev = None
    for k, vid in enumerate(seq, 1):
        km = ctx.leg_km(prev, vid)
        wm = walk_minutes(km)
        t = t + timedelta(minutes=wm)
        _, rec, fst = ctx.value(vid, t)
        leave = t + timedelta(minutes=ctx.dwell)
        lat, lon = ctx.point(vid)
        out.append({
            "order": k, "venue_id": vid, "name": rec["name"], "lat": lat, "lon": lon,
            "arrive_at": iso(t), "leave_at": iso(leave),
            "walk_minutes_from_prev": round_half_up(wm, 1), "distance_km": round_half_up(km, 2),
            "expected_vibe": fst.get("vibe_score"), "match_score": rec["match_score"],
            "confidence": round_half_up(fst.get("confidence") or 0.0, 2), "reasons": rec["reasons"],
            "is_synthetic": bool(rec["is_synthetic"]),
        })
        t = leave
        prev = vid
    return out


def build_ctx(prefs, states, venues, start_time, predictor=None):
    prefs = dict(prefs or {})
    start = to_dt(start_time or prefs.get("start_time"))
    if start is None:
        raise ValueError("plan_night needs start_time (or prefs.start_time)")
    if predictor == "auto":
        predictor = live_state._resolve_predictor("auto")
    return _Ctx(prefs, states, venues, start, predictor)


def plan_night(prefs, states, venues, start_time, n_stops: int = 3, *, predictor=None, solver="local") -> list[dict]:
    """Ordered stops (≤ n_stops), CONTRACTS v2 §F shape. solver: 'greedy' | 'local' (default) | 'exhaustive'."""
    ctx = build_ctx(prefs, states, venues, start_time, predictor)
    n_stops = max(0, int(n_stops))
    cands = _candidates(ctx)
    if not cands or n_stops == 0:
        return []
    if solver == "exhaustive":
        seq, _ = exhaustive(ctx, cands, n_stops)
    else:
        seq = greedy(ctx, cands, n_stops)
        if solver == "local":
            seq, _ = local_search(ctx, seq, cands, n_stops)
    return _stops(ctx, seq)


def objective(prefs, states, venues, start_time, stops) -> float | None:
    ctx = build_ctx(prefs, states, venues, start_time)
    return ctx.evaluate([s["venue_id"] for s in stops])


