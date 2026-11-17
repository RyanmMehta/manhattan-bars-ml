# PRD — ml-recs (the `recs/` package)

Workstream: **ml-recs** · Branch: `nightlife/ml-recs` · Owner folder: `recs/`
Status: planning (no code yet) · Rev 3, 2026-11-11 (aligned to CONTRACTS v2.2, commit acf7821)
Push deadline: **Fri 2026-11-13 18:00 ET** (CONTRACTS §I) · Integration demo: **2026-11-17**

Source of truth for every formula and constant: CONTRACTS v2 §A and
`docs/prd/specs/PRD.md` §5 (moves to `docs/specs/SCORING.md` / `PARAMETERS.md`).
This PRD restates them only to make acceptance criteria testable. If they
disagree, specs wins.

## 1. Problem

A group standing on Ludlow St at 11:30 pm wants to know where to go *now*.
Public data (SLA licenses, DOHMH, 311, OSM) tells us where bars are and how
often neighbours complain, but nothing about tonight: how full it is, whether
people are dancing, how long the line is, what is playing. Scouts will send
10-second vibe checks and operators will post updates, but raw reports are
sparse, noisy, of mixed age and credibility. Something has to turn them into
three honest numbers per venue: **vibe** (current energy), **match** (fit to
this group) and **confidence** (how much fresh, credible support there is).
Then it has to turn those into a ranked list and a multi-stop night plan with
plain-language reasons.

`recs/` does that. It is a pure-Python library the backend imports. It also
carries the course ML deliverables (baseline + first model, clustering,
optimization, model chaining).

## 2. Goals

1. G1: `live_state.compute / compute_all` produce Live Venue State per CONTRACTS
   (+ v2 §F optional keys), implementing specs §5.1–5.7 exactly.
2. G2: `scoring.recommend` returns Recommendation results per specs §5.9–5.11:
   hard-limit exclusions, weighted match, `rank_score`, reasons, missing.
3. G3: Crowd model: gradient boosting predicts crowd (1–5) by venue × hour and
   beats a venue-hour-average baseline under **temporal** validation
   (train Aug 27 → Nov 12, 34 nights; hold out Nov 13–14).
4. G4: k-means venue-style clustering on `venue_features` (real public data),
   with labelled, interpretable clusters.
5. G5: `routing.plan_night` ("Run My Night") per specs §5.12: greedy plus local
   search, checked against exhaustive search on small inputs.
6. G6: Model chaining: clusters → crowd-model features; crowd model →
   `predicted_crowd` + routing arrival-time forecasts; live state → scoring → routing.
7. G7: Show the existing complaint-risk model's output only as the field
   `complaint_risk`, labelled **"311 noise-complaint risk"**, never as a quality or vibe signal.
8. G8: Everything that touches synthetic data is marked and swappable.

## 3. Non-goals

- No HTTP layer, DB schema, auth or deployment (backend).
- No data generation for the app's live tables (live-sim owns `syn_*` tables in
  `data/live_sim.db`). ml-recs only builds tiny test fixtures, plus an interim
  stub if live-sim is late.
- No UI (frontend), no Tableau work (tableau), no coursework models (coursework).
- Not choosing formula constants. specs owns them; ml-recs implements them in
  `recs/config.py` and reports problems back.
- No collaborative filtering or learned ranking yet (no real feedback). Later.
- No changes to `src/`, `data/manhattan_bars.db` or `data/live_sim.db` (read-only).

## 4. Users

| User | What they get from `recs/` (through backend/frontend) |
|---|---|
| Consumer / group | ranked list with match/vibe/confidence, reasons, what's unknown; a 2–4 stop night plan |
| Scout | their report moves a venue's state immediately; reputation affects weight by a transparent rule |
| Venue operator | official updates (cover, DJ, genres) feed live state; predicted crowd by hour for the dashboard's `demand_by_hour` |
| Backend developer | stable, pure functions taking lists of dicts or DataFrames; no DB or network calls inside |
| Course grader / team | reproducible model evaluation reports (baseline vs model, clustering, routing optimality gap, chaining ablation) |

## 5. User stories and acceptance criteria

Golden vectors **G1–G8** (`docs/specs/golden_synthetic/`, from specs) are the
shared unit tests: reproduce each within ±1 vibe/match point and ±0.01 confidence.

**US1 Live state from reports.** As a group, I want each venue's current crowd,
dancing, line and cover estimated from recent reports so I can trust what I see.
- AC1.1 Output keys/types match the CONTRACTS Live Venue State plus v2 §F optional
  keys (`display`, `predicted_crowd`, `predicted_source`). No other keys.
- AC1.2 Per-report weight `w = w_time · w_rep · w_ver · w_status` with
  `w_time = 0.5^(age / H_field)` (H = 30 min crowd/dancing/line, 60 min scout
  cover/genre, 120 min operator cover/genres/dj), `w_rep = 0.25 + 0.75·r`
  (r = `reputation`, default 0.5), `w_ver = 1.0` if verified else 0.6,
  `w_status` = 1 accepted/pending, 0.5 disputed, 0 flagged/removed (missing
  `status` → accepted). Operator updates: `w = w_time · 0.8`.
- AC1.3 Inputs with `age > 180 min` or `ts > now + 2 min` are ignored.
- AC1.4 Field estimates: crowd and dancing are weighted means (1 dp), line is a
  weighted median (int), cover is a weighted median over scout and operator values (int),
  and genres come from a weighted vote with share ≥ 0.30. A field with total weight < 0.30 is `null`.
- AC1.5 Operators never supply crowd, dancing or line. With operator-only inputs:
  `vibe_score = null`, `confidence = min(0.25, 0.25·Σw)`.
- AC1.6 `vibe = round(100·Σ a_k x_k / Σ a_k)` with a = crowd 0.50, dance 0.35,
  line 0.15 over available terms; `crowd` null → `vibe_score` null.
- AC1.7 `confidence = round(support · agree · diverse, 2)` (support `1 − e^(−W/1.5)`,
  agree `1 − 0.5·min(1, sd_w/1.5)`, diverse 1.0 if ≥ 2 distinct scouts else 0.6).
  It is computed independently of vibe.
- AC1.8 `display` = `show` (conf ≥ 0.40), `low` (0.20–0.39), `none` (< 0.20 or vibe null).
- AC1.9 `trend`: weighted crowd `[now−30, now]` vs `[now−90, now−30)`; either
  window W < 0.5 → `null`; Δ ≥ +0.4 `rising`, ≤ −0.4 `falling`, else `steady`.
- AC1.10 Zero usable inputs: all observed fields `null`, `n_reports = 0`,
  `freshness_minutes = null`, `confidence = 0.0`, `display = "none"`, `trend = null`.
- AC1.11 Reproduces G1 (vibe 65, confidence 0.67), G2, G3, G4, G7, G8.

**US2 Ranked recommendations.** As a group, I want venues ranked by fit with reasons.
- AC2.1 Hard limits exclude on **known** values only: cover > max_cover_usd, line >
  max_line_minutes, distance > max_distance_km, OSM `opening_hours` parses and
  says closed, venue in `exclude_venue_ids`. Unknown values never exclude; they go in `missing`.
- AC2.2 Excluded venues are returned after all included ones with `excluded: true`,
  `excluded_reason` set, and that reason also as the first `reasons` entry
  (`"Excluded: cover $25 over your $20"`).
- AC2.3 Match components and weights: genre 0.25, dancing 0.20, crowd 0.15,
  line 0.10, cover 0.10, distance 0.15, group 0.05. Unknown → 0.4 + `missing`
  entry. A component with weight 0 (e.g. `want_dancing` null) is renormalised away.
  `match_score = round(100·Σ w s / Σ w)`.
- AC2.4 `rank_score = match_score · (0.75 + 0.25·confidence)`. Sort included by
  rank_score desc, then distance asc, then venue_id. `rank` is 1-based.
- AC2.5 Up to 3 `reasons`, each one of the top positive weighted components, written from a template with
  evidence (`"Hip-hop playing (2 reports, 12 min ago)"`, `"Line ~10 min, under your 15"`).
- AC2.6 Reproduces G5 (match 83, rank_score 76) and G6.
- AC2.7 Deterministic: same inputs + `now` → same output; order of input rows irrelevant.

**US3 Crowd forecast.** As an operator or the planner, I want expected crowd by hour.
- AC3.1 `crowd_model.predict(venue_ids, times)` returns crowd 1–5 (or `None` for
  unknown venues) per pair; used for `predicted_crowd` and routing.
- AC3.2 Temporal evaluation: train on nights Aug 27 → Nov 12 (34), test on Nov 13–14
  (the 2 held-out nights), plus 3-fold rolling origin. Report MAE, RMSE and Spearman
  for model vs venue-hour-average baseline vs global hour mean. Target: model
  MAE ≤ 0.9 × baseline MAE (placeholder).
- AC3.3 Report scores against two references: (a) held-out *reported*
  crowd and (b) `syn_true_state.crowd_true` (evaluation only, never a feature).
  It also states that results measure the simulator's structure, not real nightlife.
- AC3.4 Training and evaluation weight reports with reputation **as of the report date**
  (`syn_scout_reputation_history`), never the final `syn_scouts.reputation`, which leaks the future. The live app uses current reputation.

**US4 Venue styles.** As a user browsing, I want "places like this" groupings.
- AC4.1 k-means on standardized `venue_features` of `v_bars` (1,727 venues);
  k chosen in 3–8 by silhouette and interpretability; seed 42.
- AC4.2 Each cluster has a generated label and a profile table (means/modes).
- AC4.3 All 35 launch venues get a `cluster_id` and `cluster_label`.

**US5 Run My Night.** As a group, I want a 3-stop plan from where I am.
- AC5.1 `plan_night` returns ≤ `n_stops` (default 3) distinct stops shaped
  `{order, venue_id, name, lat, lon, arrive_at, leave_at, walk_minutes_from_prev,
  distance_km, expected_vibe, match_score, confidence, reasons[]}`.
- AC5.2 Walking 4.5 km/h, dwell `dwell_minutes` (60); each stop must pass the hard
  limits at its arrival time; total walk ≤ `max_total_walk_minutes` (30); no repeats;
  `exclude_venue_ids` honoured; start = `start_time` or `now`.
- AC5.3 Objective `Σ rank_score(t_arrive) − 10 · walk_km`. Greedy + 2-opt/swap is
  within 5% of the exhaustive optimum on ≥ 90% of 200 random small cases (report the gap).
- AC5.4 If fewer than `n_stops` stops are feasible, return fewer; never pad.

**US6 Complaint risk shown honestly.** As a user, I want to know if a venue has
lots of 311 noise complaints without thinking it measures fun.
- AC6.1 `complaint_risk` (0–1, or null) labelled "311 noise-complaint risk".
- AC6.2 Never used in `match_score`, `rank_score`, `vibe_score`, reasons or routing.
- AC6.3 Docstrings and reports never call it quality, popularity or vibe.

## 6. Scope

| MVP (push by Nov 13 18:00) | Later |
|---|---|
| `live_state` compute/compute_all (specs §5.1–5.7) | Bayesian hierarchical state, richer gaming detection |
| `scoring.recommend` (specs §5.9–5.11) | learned ranker from `syn_feedback` → real feedback; per-member compatibility |
| crowd model + baseline + temporal eval report | quantile/interval forecasts; real-data retrain |
| k-means clustering + labels | genre-aware clustering once real attributes exist |
| `routing.plan_night` greedy + local search + exhaustive check | time-window orienteering with line-wait forecasts, transit |
| chaining with ablation | heatmap forecast surfaces (`/api/heatmap?by=hour`) |
| `complaint_risk` for launch venues | — |

## 7. Requirements

Functional
- F1 Public API exactly as CONTRACTS `## Python interface`. Extra modules
  (`crowd_model`, `clustering`, `complaint_risk`, `chain`) only add to it.
- F2 `now` / `start_time` accepted as tz-aware `datetime` or ISO string; normalized
  to America/New_York. Demo time `DEMO_NOW = 2026-11-14T23:30:00-05:00`.
- F3 Reports, updates, states and venues may be lists of dicts **or** DataFrames (v2 §F).
- F4 All constants in `recs/config.py`, each pointing at its specs section; values
  match CONTRACTS v2 §A.
- F5 Output `is_synthetic = true` whenever any contributing input row is synthetic
  or a model trained on synthetic data contributed.
- F6 CLI: `python -m recs {train-crowd,cluster,complaint-risk,eval,demo,plan}`.
- F7 Venue static attributes: `data/venue_attributes_manual.csv` rows override
  `syn_venue_attributes` rows when present (v2 §D); expect `has_dance_floor` to be sparse.

Non-functional
- N1 `recommend` over 35 venues < 50 ms; `compute_all` for 35 venues × 500 reports
  < 200 ms; `plan_night` < 300 ms (placeholder budgets, laptop).
- N2 Pure functions: no network, no DB writes, no global mutable state except a lazy artifact cache.
- N3 Importable with only `requirements.txt` deps. If an artifact is missing,
  functions degrade (no `predicted_crowd`, routing uses current state) instead of crashing.
- N4 Deterministic given seed 42.

## 8. Dependencies on other workstreams

| Workstream | We need from them | They need from us |
|---|---|---|
| **specs** | `SCORING.md`, `PARAMETERS.md`, golden vectors G1–G8, `tools/reference_scoring.py` oracle, `EVALUATION.md` protocol | confirmation formulas are implementable; issues found while matching golden vectors |
| **research** | interview evidence on which preferences matter and which reasons users trust (input to specs' weights) | — |
| **tableau** | — | crowd-by-hour forecasts, cluster profiles, model eval tables (they write extracts into `analytics/tableau/`); snapshot values via live-sim's `demo_night_snapshots.csv` |
| **live-sim** | `data/live_sim.db` (built at build time): 36 Thu–Sat nights Aug 27–Nov 14, seed 42, `syn_scout_reports` (+status, distance_m), `syn_scouts`, `syn_scout_reputation_history`, `syn_venue_attributes`, `syn_venue_updates`, eval-only `syn_true_state`; 17-slug genre list `simulator/config/genres.json` | `chain.snapshots` so their `demo_night_snapshots.csv` uses our `live_state`; feedback on whether the crowd model can learn their hour/style patterns |
| **ml-recs** | (self) | — |
| **backend** | calls our functions; joins `reputation` onto reports; passes `now`; maps our fields to API shapes; `demand_by_hour` from our forecasts | stable `recs` API, latency budget, stub-compatible degradation |
| **frontend** | shows reasons/missing/display state/"demo data" badge, vibe bands (Chill 0–34 / Lively 35–64 / Packed 65–100), "stale" tag when freshness > 60 min, complaint-risk label wording | exact field semantics and reason copy |
| **coursework** | — (separate exercises) | none |
| **integration** | merge order (… live-sim → **ml-recs** → backend …), `tests/contract/`, deploy env | passing tests by Nov 13 18:00, `docs/workstreams/ml-recs.md`, `docs/synthetic/ml-recs.md` |

## 9. Success metrics

- G1–G8 reproduced; contract-shape tests pass; backend smoke test calls all 3 public functions.
- Differential test: `recs` equals specs' `reference_scoring.py` on 500 random synthetic venue-states.
- Crowd model MAE ≤ 0.9 × baseline MAE on Nov 13–14 (synthetic; placeholder target).
- Clustering silhouette ≥ 0.15 (placeholder) and every cluster nameable in one phrase.
- Routing gap ≤ 5% on ≥ 90% of 200 random small cases.
- Zero "favourable default" violations (property test: removing a report or field
  never increases `match_score` of that venue).
- Demo end-to-end at DEMO_NOW in < 5 s.
- Later (real pilot): top-3 click-through, visited rate, share of post-visit ratings ≥ 4.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Course deliverables (Oct 20/27/Nov 3) past due; push deadline Nov 13 18:00 (≈ 2 days) | grade/time | build in OUTLINE order; live_state + scoring first; models can land as reports after the API |
| Crowd model learns the simulator's own formula | inflated metrics | say so; also score vs `syn_true_state`; temporal split; simple baselines |
| `syn_true_state` / `syn_scout_truth` leak into features or the app | invalid evaluation | only `crowd_model.evaluate` may read them; test that library code never references them |
| Final reputation joined to past reports | future leakage, inflated crowd-model metrics | as-of join on `syn_scout_reputation_history`; test that editing future history rows doesn't change the training table |
| Snapshot file built before ml-recs merges (merge order live-sim → ml-recs) | `demo_night_snapshots.csv` not from our `live_state` | live-sim depends on `recs` on the ml-recs branch or regenerates after merge (open question 6) |
| live-sim late or schema drift | blocked eval | interim stub generator in `recs/synthetic/`, schema checks at load |
| specs constants change | rework | all constants in `config.py`; golden vectors + differential test catch drift |
| Complaint risk misread as quality | misleading product | naming rule, excluded from all scores; copy agreed with frontend |
| Sparse reports → many `display = none` at DEMO_NOW | weak demo | `predicted_crowd` from crowd model shown separately; never raises confidence |
| `has_dance_floor` sparse | dancing component often unknown (0.4) | expected per v2 §D; surfaced in `missing` |
| pandas 3 (copy-on-write, string dtype) | bugs | explicit dtypes, tests on pinned versions |

## 11. Contract change requests

CCRs 1–7 from rev 1 were all accepted in CONTRACTS v2 §F (reputation on report
rows; `venues` keys; list-or-DataFrame inputs; optional Live State keys;
Recommendation `rank_score/rank/excluded_reason/cluster_label/complaint_risk/is_synthetic`;
Preferences `start_time/dwell_minutes/max_total_walk_minutes/exclude_venue_ids`;
`plan_night` stop shape; trend values). New, minor:

1. **`match_score`/`rank_score` on excluded venues.** Proposal: still computed
   (for debugging), but `rank = null`. Frontend shows only the count.
2. **Rounding.** Internal computation uses unrounded crowd/dancing (G5 needs crowd 3.76,
   not 3.8). Only outputs are rounded. Ask specs to state this in `SCORING.md`.

## 12. Open questions

1. With no scout inputs, is `confidence` `0.0` (specs formula) or `null` (v2 §F allows null)? Plan: `0.0`, with `display = "none"`.
2. Complaint risk: v2 §F/§G put `complaint_risk` on recommendations and venue cards,
   while specs §5.11 says "profile only, as a 311 count". Plan: follow CONTRACTS v2 (field present, labelled); frontend decides placement.
3. Group component when `capacity` is unknown: unknown → 0.4 (plan), confirm with specs.
4. Closed-now rule depends on `opening_hours` parsing (OSM syntax). Plan: support the
   simple `Mo-Su HH:MM-HH:MM` forms and treat everything else as unknown (never excludes).
5. Does live-sim's report density at DEMO_NOW give ≥ 10 of 35 venues `display = show`? If not, ask live-sim to tune the arrival rate.
6. `demo_night_snapshots.csv` must be computed with our `live_state`, but live-sim merges before ml-recs. Plan: ml-recs pushes `live_state` + `chain.snapshots` early (Thu Nov 12), and integration regenerates the file after merging ml-recs (`make data`).
