"""CLI: python -m recs {train-crowd,cluster,complaint-risk,eval,demo,plan,snapshots}

All commands read data read-only. `eval` (re)writes every artifact and recs/reports/*.md.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
import warnings
from pathlib import Path

from . import config as C

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
BANNER = "> **Demo data — synthetic.** Trained/evaluated on {src} synthetic nights (seed 42). Numbers describe the " \
         "generator's structure, not real nightlife.\n"


def _prefs(path):
    p = Path(path) if path else HERE / "examples" / "prefs_hiphop_group.json"
    return json.loads(p.read_text())


def _fmt(x, nd=3):
    return "—" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


# ------------------------------------------------------------------------------------------- reports
def report_crowd(meta: dict) -> str:
    ev = meta["_eval"]
    src = meta["data_source"]
    L = [f"# Crowd model — baseline vs gradient boosting\n", BANNER.format(src=src),
         f"Rows: venue × night × hour slot with ≥ 1 eligible report ({ev['summary']['rows']} rows, "
         f"{ev['summary']['nights']} Thu–Sat nights). Target: reputation-weighted mean reported crowd (1–5); "
         "report weights use reputation **as of the report night** (`syn_scout_reputation_history`).\n",
         "Model: `HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=42)`; "
         f"features: {', '.join(meta['features'])}. `venue_te` is a train-nights-only venue mean. "
         "`syn_true_state` / `syn_scout_truth` are never features.\n",
         "Split: train Aug 27 → Nov 12, **hold out Nov 13–14** (CONTRACTS §B) + 3 rolling-origin folds of 2 nights.\n",
         "## Results (MAE / RMSE / Spearman)\n",
         "| fold | train nights | reference | model | venue-hour baseline | global slot mean |",
         "|---|---|---|---|---|---|"]
    for name, row in ev.items():
        if name == "summary":
            continue
        for ref in ("vs_reported", "vs_true"):
            if ref not in row:
                continue
            m = row[ref]
            cell = lambda k: f"{m[k]['mae']:.3f} / {m[k]['rmse']:.3f} / {m[k]['spearman']:.2f}"  # noqa: E731
            L.append(f"| {name} | {row['train_nights']} | {ref.replace('vs_', '')} | {cell('model')} | {cell('baseline')} "
                     f"| {cell('slot_mean')} |")
    s = ev["summary"]
    verdict = "meets" if s["ratio"] <= s["target_ratio"] else "does **not** meet"
    L += ["", f"Holdout MAE ratio model / baseline = **{s['ratio']:.3f}** (target ≤ {s['target_ratio']}, placeholder): "
          f"the model {verdict} the target. The baseline is strong because the generator's crowd is mostly venue × hour; "
          "the model's edge comes from weekday/week effects and pooling across similar venues for thin venue-slots.",
          "", "Against `crowd_true` (evaluation only) errors are lower than against reports, because reports add "
          "scout noise the model cannot predict.", "",
          "Artifact: `recs/artifacts/synthetic/crowd_model.joblib` (+ `.json`), trained on all nights before the holdout. "
          "Regenerate: `python -m recs train-crowd`."]
    return "\n".join(L) + "\n"


def report_clustering(meta: dict) -> str:
    from . import data
    df = meta["_df"]
    launch = set(data.launch_venues()["venue_id"])
    L = ["# Venue-style clustering (k-means, real public data)\n",
         f"Data: `venue_features` ⋈ `v_bars` ({meta['rows']} venues, real public data — not synthetic). Complaint "
         "targets (`noise_complaints`, `high_noise`) and lat/lon are excluded. Numeric: median-impute + standardise; "
         "categorical: one-hot (min_frequency 20). `KMeans(n_init=10, random_state=42)`.\n",
         "## k sweep\n", "| k | inertia | silhouette | smallest cluster share |", "|---|---|---|---|"]
    for s in meta["sweep"]:
        L.append(f"| {s['k']} | {s['inertia']:.0f} | {s['silhouette']:.3f} | {s['min_share']:.1%} |")
    L += ["", f"Chosen **k = {meta['k']}**: highest silhouette among k with every cluster ≥ 3% of venues. "
          "Silhouettes around 0.17–0.19 mean the clusters overlap: they're useful as coarse groups, not crisp types.\n",
          "## Clusters\n", "| id | label | venues | launch venues |", "|---|---|---|---|"]
    for k, lab in meta["labels"].items():
        m = df["cluster_id"] == int(k)
        L.append(f"| {k} | {lab} | {int(m.sum())} | {int(df.loc[m, 'license_id'].isin(launch).sum())} |")
    L += ["", "Labels come from each cluster's top z-scored features and most over-represented category. They "
          "describe the public-data profile (licence, inspections, OSM, density), not quality or vibe.", "",
          "Artifacts: `recs/artifacts/clusters.csv` (venue_id, cluster_id, cluster_label), `clusters.json` "
          "(profiles). Used as `cluster_label` on recommendations and as a crowd-model feature."]
    return "\n".join(L) + "\n"


def report_routing(n_cases=200, n_venues=10) -> str:
    from . import live_state, routing
    rng = random.Random(C.SEED)
    gaps_g, gaps_l, times = [], [], []
    for case in range(n_cases):
        venues, states = [], []
        for i in range(n_venues):
            vid = f"r{case}-{i}"
            venues.append({"venue_id": vid, "name": vid, "lat": 40.72 + rng.uniform(-0.005, 0.005),
                           "lon": -73.988 + rng.uniform(-0.005, 0.005), "capacity": rng.choice([60, 120, 200]),
                           "genres": rng.choice(["hip-hop", "rock", "house", "r&b"]), "is_synthetic": 1})
            st = live_state.empty_state(vid)
            st.update(crowd=rng.uniform(1, 5), dancing=rng.uniform(0, 2), line_minutes=rng.choice([0, 5, 10, 20]),
                      cover_usd=rng.choice([0, 10, 20, 30, None]), confidence=rng.uniform(0, 1), vibe_score=50)
            states.append(st)
        prefs = {"genres": ["hip-hop", "r&b"], "want_dancing": True, "crowd_pref": 4, "max_cover_usd": 20,
                 "max_line_minutes": 15, "max_distance_km": 1.5, "lat": 40.72, "lon": -73.988, "group_size": 4}
        ctx = routing.build_ctx(prefs, states, venues, C.DEMO_NOW)
        cands = routing._candidates(ctx)
        t0 = time.perf_counter()
        g = routing.greedy(ctx, cands, 3)
        og = ctx.evaluate(g) if g else 0.0
        seq, ol = routing.local_search(ctx, g, cands, 3)
        times.append(time.perf_counter() - t0)
        _, opt = routing.exhaustive(ctx, cands, 3)
        gaps_g.append(0.0 if opt <= 0 else (opt - og) / opt)
        gaps_l.append(0.0 if opt <= 0 else (opt - ol) / opt)

    def summ(gs):
        within = sum(x <= 0.05 for x in gs) / len(gs)
        return f"{within:.0%}", f"{sum(gs) / len(gs):.2%}", f"{max(gs):.2%}", f"{sum(x <= 1e-9 for x in gs) / len(gs):.0%}"
    L = ["# Run My Night — routing optimality\n",
         BANNER.format(src="randomly generated").replace("nights", "venue states"),
         "Objective (specs §5.12): Σ rank_score at arrival − 10 · walk_km; 4.5 km/h, 60-min dwell, total walk ≤ 30 min, "
         "no repeats, each stop must pass hard limits at its arrival time (closing hours, cover, line, distance).\n",
         "Solver: greedy best-marginal insertion, then local search (segment reversal, swap-in of unused candidates, "
         "insertion) until no gain. Oracle: exhaustive search over all ordered 1–3-stop sequences of the candidates.\n",
         f"## {n_cases} random cases ({n_venues} venues each, 3 stops)\n",
         "| solver | within 5% of optimum | mean gap | worst gap | exactly optimal |", "|---|---|---|---|---|"]
    L.append("| greedy | " + " | ".join(summ(gaps_g)) + " |")
    L.append("| greedy + local search (shipped) | " + " | ".join(summ(gaps_l)) + " |")
    L += ["", f"Mean solve time (greedy + local search): {1000 * sum(times) / len(times):.1f} ms. "
          "Target: within 5% on ≥ 90% of cases (PRD AC5.3).", "",
          "Forecast at arrival: the observed state decays towards the crowd model's prediction (half-life 30 min); "
          "confidence only decays, so later stops lean less on stale reports. Without a model artifact the planner "
          "uses the current state with decaying confidence."]
    return "\n".join(L) + "\n"


def report_chaining(ab: dict, src: str) -> str:
    cm = ab["crowd_model"]
    L = ["# Model chaining — ablation\n", BANNER.format(src=src),
         "Chain: **clusters** (real public data) → crowd-model feature `cluster_id` → **crowd model** → "
         "`predicted_crowd` on live state + arrival-time forecasts in routing → **scoring** → **routing**.\n",
         "## 1. Does the cluster feature help the crowd model? (holdout Nov 13–14, MAE vs reported crowd)\n",
         "| variant | MAE |", "|---|---|",
         f"| crowd model with cluster_id | {cm['with_clusters']:.3f} |",
         f"| crowd model without cluster_id | {cm['without_clusters']:.3f} |",
         f"| venue-hour baseline | {cm['baseline']:.3f} |", "",
         "Clusters come from public licence/inspection data, which the synthetic generator doesn't use to make crowds, "
         "so a near-zero effect is expected here; the link is in place for real data, where venue type should matter.\n"]
    if ab.get("routing"):
        L += ["## 2. Does the crowd forecast improve Run My Night? (holdout nights, plans re-scored on `crowd_true`)\n",
              "| variant | mean realised objective | mean true-crowd fit of stops |", "|---|---|---|"]
        for r in ab["routing"]["mean"]:
            L.append(f"| {r['variant']} | {r['realised_objective']:.1f} | {r['true_crowd_fit']:.3f} |")
        L += ["", "| night | start | variant | stops | realised objective | true-crowd fit |", "|---|---|---|---|---|---|"]
        for r in ab["routing"]["rows"]:
            L.append(f"| {r['night']} | {r['start']} | {r['variant']} | {r['stops']} | {r['realised_objective']} | "
                     f"{r['true_crowd_fit']} |")
        L += ["", "Realised objective = each planned stop re-scored with the true crowd at its arrival time (evaluation "
              "only; `syn_true_state` never reaches the app). The forecast helps most for early starts, when later "
              "stops are hours away and current reports say little about them."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------------------------------- commands
def cmd_train_crowd(a):
    from . import crowd_model, data
    m = crowd_model.train(data.live_tables(a.source))
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "crowd_model.md").write_text(report_crowd(m))
    print(json.dumps(m["metrics"]["summary"], indent=1))
    return m


def cmd_cluster(a):
    from . import clustering
    m = clustering.fit()
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "clustering.md").write_text(report_clustering(m))
    print(f"k={m['k']}", json.dumps(m["labels"], indent=1))


def cmd_complaint_risk(a):
    from . import complaint_risk
    print(json.dumps(complaint_risk.train(), indent=1))


def cmd_eval(a):
    from . import chain, data
    cmd_cluster(a)
    cmd_complaint_risk(a)
    cmd_train_crowd(a)
    (REPORTS / "routing.md").write_text(report_routing())
    t = data.live_tables(a.source)
    (REPORTS / "chaining.md").write_text(report_chaining(chain.ablation(t, _prefs(a.prefs)), t["_source"]))
    print("reports written to", REPORTS)


def _print_recs(res, top=5):
    from .live_state import vibe_band
    st = {s["venue_id"]: s for s in res["states"]}
    print(f"[demo data — synthetic: {res['source']}]  now = {res['now']}")
    inc = [r for r in res["recommendations"] if not r["excluded"]]
    exc = [r for r in res["recommendations"] if r["excluded"]]
    for r in inc[:top]:
        s = st[r["venue_id"]]
        band = vibe_band(r["vibe_score"]) or "no label"
        pc = f", predicted crowd {s['predicted_crowd']}" if s.get("predicted_crowd") is not None else ""
        print(f"{r['rank']:>2}. {r['name']:<28} match {r['match_score']:>3}  vibe {_fmt(r['vibe_score'])} ({band})  "
              f"conf {r['confidence']:.2f} [{s['display']}]{pc}")
        for x in r["reasons"]:
            print(f"      + {x}")
        for x in r["missing"]:
            print(f"      ? {x}")
        if r["complaint_risk"] is not None:
            print(f"      311 noise-complaint risk: {r['complaint_risk']:.2f} (not a quality score)")
    if exc:
        print(f"\n{len(exc)} hidden by your limits, e.g. {exc[0]['name']}: {exc[0]['excluded_reason']}")


def _print_plan(plan):
    print("\nRun My Night:")
    for s in plan:
        print(f"  {s['order']}. {s['name']:<28} arrive {s['arrive_at'][11:16]}  leave {s['leave_at'][11:16]}  "
              f"walk {s['walk_minutes_from_prev']:.0f} min  expected vibe {_fmt(s['expected_vibe'])}  match {s['match_score']}")


def cmd_demo(a):
    from . import chain
    res = chain.run(a.now, _prefs(a.prefs), a.source, n_stops=a.n_stops)
    _print_recs(res)
    _print_plan(res["plan"])
    if a.json:
        print(json.dumps(res, indent=1, default=str))


def cmd_plan(a):
    from . import chain, data, live_state, routing
    res = chain.run(a.now, _prefs(a.prefs), a.source, n_stops=a.n_stops)
    _print_plan(res["plan"])
    venues = data.venues_for_scoring(a.source)
    for solver in ("greedy", "local", "exhaustive"):
        p = routing.plan_night(_prefs(a.prefs), res["states"], venues, a.now, n_stops=a.n_stops, solver=solver,
                               predictor="auto")
        ctx = routing.build_ctx(_prefs(a.prefs), res["states"], venues, a.now, predictor="auto")
        print(f"  {solver:<10} objective {ctx.evaluate([s['venue_id'] for s in p]) or 0:.1f}  "
              f"stops {[s['name'] for s in p]}")
    _ = live_state


def cmd_snapshots(a):
    from . import chain, data
    t = data.live_tables(a.source)
    df = chain.snapshots(data.reports_with_reputation(a.source), t["syn_venue_updates"], a.start, a.end,
                         venue_ids=list(data.launch_venues()["venue_id"]))
    df.to_csv(a.out, index=False)
    print(f"wrote {len(df)} rows to {a.out}")


def main(argv=None):
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(prog="python -m recs")
    ap.add_argument("--source", default="auto", choices=["auto", "live_sim", "stub"])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("train-crowd", "cluster", "complaint-risk", "eval"):
        p = sub.add_parser(name)
        p.add_argument("--prefs")
    for name in ("demo", "plan"):
        p = sub.add_parser(name)
        p.add_argument("--now", default=C.DEMO_NOW)
        p.add_argument("--prefs")
        p.add_argument("--n-stops", type=int, default=3)
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("snapshots", help="demo-night snapshots (CONTRACTS §J) for live-sim")
    p.add_argument("--start", default="2026-11-14T20:00:00-05:00")
    p.add_argument("--end", default="2026-11-15T03:00:00-05:00")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    {"train-crowd": cmd_train_crowd, "cluster": cmd_cluster, "complaint-risk": cmd_complaint_risk, "eval": cmd_eval,
     "demo": cmd_demo, "plan": cmd_plan, "snapshots": cmd_snapshots}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
