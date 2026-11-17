# ml-recs: as-built notes (`recs/`)

Branch `nightlife/ml-recs` · owner Ryan Mehta · built Tue Nov 17 2026 (demo day).
Plan: `docs/prd/ml-recs/{PRD,RULES,OUTLINE}.md`. Contracts: `docs/CONTRACTS.md` v2.2 (b46d75f).
Formulas: specs `docs/specs/SCORING.md` / `PARAMETERS.md` / `tools/reference_scoring.py` (origin/nightlife/specs).

## What was built

| Module | What it does | Status |
|---|---|---|
| `recs.live_state` | `compute`, `compute_all` → Live Venue State (+ `display`, `predicted_crowd`, `predicted_source`) | done |
| `recs.scoring` | `recommend` → Recommendation results (+ `rank_score`, `rank`, `excluded_reason`, `cluster_label`, `complaint_risk`, `is_synthetic`) | done |
| `recs.routing` | `plan_night` (greedy + local search; exhaustive oracle), CONTRACTS v2 §F stop shape (+ `is_synthetic`) | done |
| `recs.crowd_model` | HGB crowd forecast by venue × hour vs venue-hour baseline; temporal holdout Nov 13–14 + 3 rolling folds; `predict(venue_ids, times)` | done |
| `recs.clustering` | k-means (k=5) on real `venue_features` (v_bars), auto-labelled; `assignments()`, `label_for()` | done |
| `recs.complaint_risk` | out-of-fold "311 noise-complaint risk" (real data), shown only as a field | done |
| `recs.chain` | `snapshots()` (CONTRACTS §J), `run(now, prefs)`, `ablation()` | done |
| `recs.synthetic.stub_nights` | SYNTHETIC interim live-sim stand-in (used only when no `live_sim.db`) | done |
| CLI | `python -m recs {train-crowd,cluster,complaint-risk,eval,demo,plan,snapshots}` | done |
| Reports | `recs/reports/{crowd_model,clustering,routing,chaining}.md` (written by `python -m recs eval`) | done |

## How to run

```bash
pip install -r requirements.txt -r recs/requirements-dev.txt
python -m pytest recs/tests -q                    # 69 pass, 1 skip (genres.json not on this branch), ~8 s
python -m recs demo                               # DEMO_NOW 2026-11-14T23:30 ET: top 5 + Run My Night
python -m recs demo --now 2026-11-14T21:00:00-05:00
python -m recs plan                               # plan + greedy / local / exhaustive objective
python -m recs eval                               # retrain all artifacts, rewrite all reports (~20 s)
python -m recs snapshots --out data/synthetic_live/demo_night_snapshots.csv   # for live-sim/integration
```
Data: `data/live_sim.db`, or `LIVE_SIM_DB=/path/live_sim.db` (env name reserved in CONTRACTS §H). With neither,
recs falls back to its own stub (`--source stub` forces it). Committed artifacts/reports were produced from
live-sim's simulator at origin/nightlife/live-sim `beaa382` (`python -m simulator --seed 42`).

Backend usage (pure functions, lists of dicts or DataFrames):
```python
from recs import live_state, scoring, routing
states = live_state.compute_all(reports, updates, now, venue_ids=ids, predictor="auto")  # predictor optional
recs   = scoring.recommend(prefs, states, venues, now)
stops  = routing.plan_night(prefs, states, venues, start_time, n_stops=3, predictor="auto")
from recs import crowd_model; crowd_model.predict(venue_ids, times)   # demand_by_hour
```
`venues` rows: `venue_id, name, lat, lon` + optional `genres, capacity, opening_hours | is_open_now, is_launch,
cluster_label, complaint_risk`. Missing `cluster_label` / `complaint_risk` are filled from committed artifacts.

## Results (synthetic; they measure the simulator's structure, not real nightlife)

- **Golden vectors:** specs' G1–G8 all reproduced exactly (`recs/tests/test_specs_golden.py`). G1 vibe 65 / conf 0.67, G5 match 83 / rank_score 76.2.
- **Differential test:** `recs` matches specs' `reference_scoring.py` on 500 random venue-state/prefs cases.
- **Crowd model (holdout Nov 13–14, live-sim data):** MAE 0.695 vs baseline 0.724 vs global slot mean 1.068
  (ratio 0.96; misses the 0.9 placeholder target). Against `crowd_true`: 0.568 vs 0.603. Beats the baseline on all
  3 rolling folds too.
- **Clustering:** k=5, silhouette 0.188 (≥ 0.15 target); all 35 launch venues assigned.
- **Complaint risk:** out-of-fold ROC AUC 0.73 (5,704 venues, base rate 17%).
- **Routing:** greedy + local search within 5% of the exhaustive optimum on 100% of 200 random cases (mean gap
  0.06%; greedy alone 93%); 1.6 ms per solve.
- **Chaining ablation:** cluster feature ≈ no effect on synthetic crowd (expected: live-sim doesn't use public data
  for crowds). Crowd forecast in routing raises the true-crowd fit of planned stops from 0.61 to 0.70 on holdout nights.
- **Latency (test):** compute_all 35 venues × 500 reports < 200 ms, recommend < 50 ms, plan_night < 300 ms; `chain.run` < 5 s.

## Assumptions and decisions (made autonomously on demo day)

1. **specs wins on every formula.** After specs pushed `reference_scoring.py` I aligned to it, even where my PRD said
   otherwise: exclusion order is closed → launch_only → distance → cover → line; excluded venues keep a `rank`
   (numbered after the included ones) instead of `rank = null` (my CCR 1 is withdrawn); `exclude_venue_ids` drops venues
   from `recommend`'s output; there's no `"Excluded: …"` prefix in `reasons`; the reason threshold is 0.6; the copy is
   specs' ("Crowd 3.8 of 5, close to your 4", "Hip-hop playing (posted by venue)").
2. Operator updates count towards `sources`/`freshness` even without cover/genres (oracle behaviour). With no crowd
   reports, confidence = min(0.25, 0.25·Σw_operator).
3. `confidence = 0.0` (not null) with no inputs, `display = "none"` (PRD open Q1).
4. A missing preference (e.g. `want_dancing: null`, no `max_cover_usd`) gives that component weight 0 and applies no
   limit. specs' defaults (`default_max_cover_usd` etc. in PARAMETERS.md) are left to the backend to apply to requests.
5. Recommendation `is_synthetic` is also true when the venue row is synthetic (synthetic attributes), per PRD F5. The
   oracle uses state only; the differential test allows ours ≥ theirs.
6. Closed-now: a caller-supplied `is_open_now` wins; otherwise recs parses simple OSM `opening_hours` (day ranges,
   lists, `off`, overnight spans, comma-separated rule groups, `24/7`). Anything else is unknown and never excludes.
7. Crowd model: `week` dropped as a feature (it extrapolated badly into holdout weeks: 0.81 → 0.70 MAE without it).
   Venue / venue×slot / venue×weekday target encodings use train nights only. The app artifact is trained on nights before the
   holdout, so the reported holdout numbers stay honest.
8. The crowd model only knows Thu–Sat; other weekdays are predicted as Thursday.
9. Routing forecast: observed state decays towards `predicted_crowd` (half-life 30 min); confidence only decays.
   Distance-to-venue limits are measured from the group's start point.
10. The interim stub generator was written because live-sim had nothing on origin when I started; it now only runs
    when no `live_sim.db` exists (e.g. CI without `make data`).
11. `recs/inputs.py` replaces the planned `recs/io.py` so the module can never shadow the stdlib `io`.
12. Specs' golden vectors and oracle are copied to `recs/tests/specs_copy/` so tests run on this branch. After
    integration the tests use `docs/specs/` automatically.

## Fixes after live testing (Nov 17)

- **Brick ranked #1 with vibe 0 for a crowd-4 / dancing group.** Not a data bug: live-sim's 5 fresh reports really
  say crowd 1, dancing 0, R&B, no line, no cover. Cause: in the spec formula, genre + line + cover + distance + group
  carry 65% of the match weight, and an empty bar scores 1.0 on "no line" and "no cover", so match stayed 65. Then its
  high confidence (0.75) lifted rank_score (60.9) above livelier but less certain venues. Fix (recs addition,
  CCR-D): `rank_score` is multiplied by an energy penalty when the **known** crowd/dancing contradict the request
  (fit = mean of known crowd/dancing component scores < 0.5 → × (0.5 + fit); adopted by specs as SCORING §9 / G9). `match_score` is unchanged and still equals
  specs' oracle. Unknown values never trigger it. Brick drops to ~37 and out of the top 5. Regression test:
  `recs/tests/test_regressions.py`.
- **cluster_label is now a short human label** ("Late-night restaurant bar", "Drinks-first bar", "Low-key local bar",
  "Restaurant bar with outdoor seating", "Bar & kitchen"). The raw feature description moved to a new
  `cluster_description` field on recommendations and in `clusters.csv`.

## Open issues / notes for integration

- **demo_night_snapshots.csv:** live-sim's `simulator/snapshots.py` uses `recs.live_state` when importable, else its
  own mirror. The file currently on live-sim's branch came from the mirror and differs from recs (confidence is null
  instead of 0.0 when there are no reports; crowd matches on 97% of rows). After merging ml-recs, run `make data` with `recs` importable,
  or `python -m recs snapshots --out data/synthetic_live/demo_night_snapshots.csv`.
- live-sim's documented build command `python -I -m simulator …` fails unless the package is pip-installed (`-I`
  drops the CWD from `sys.path`). `pip install -e simulator/` first, or run it without `-I`. (live-sim/integration)
- At DEMO_NOW on live-sim data the top pick (Brick) has vibe 0 ("Chill"): it's near, plays R&B and has no line, and
  vibe isn't part of match. That's correct per spec, but consider a vibe component or a `crowd_pref` closer to the persona.
- Crowd model misses the 0.9×baseline placeholder target (0.96). The baseline is strong because the simulator's
  crowd is mostly venue × hour. Retrain on real reports before reading anything into it.
- Property found while testing: removing a *dissenting* report can raise confidence (agreement term). This is intended
  by the formula; RULES' "removing a report never raises confidence" holds only for agreeing reports. (specs FYI)

## Contract change requests

- CCR-A (to specs/frontend): rank semantics for excluded venues now follow `reference_scoring.py` (ranked after
  included). Frontend should show only included venues' ranks and an "N hidden by your limits" count.
- CCR-B (to specs): state in SCORING.md that rounding happens only at output and that `match` uses the rounded state
  fields from `live_state` (G5 is identical either way).
- CCR-C (to specs): recommendation `is_synthetic` should include venue-attribute provenance (PRD F5).
- CCR-D (to specs): adopt the energy penalty on `rank_score` (`config.ENERGY_FIT_MIN = 0.5`,
  `ENERGY_PENALTY_FLOOR = 0.5`). **Accepted** (Contracts c3fd169, specs 008a064, golden G9); recs uses specs'
  unweighted-mean fit and matches `reference_scoring.py` exactly again.
- CCR-E (to backend/frontend): new Recommendation key `cluster_description` (raw); `cluster_label` is short and user-facing.
