# PRD — ml-recs (the `recs/` package)

Workstream: **ml-recs** · Branch: `nightlife/ml-recs` · Owner folder: `recs/`
Status: planning (no code yet) · Written 2026-11-11 · Integration deadline: **2026-11-17**

## 1. Problem

A group standing on Ludlow St at 11:30 pm wants to know where to go *now*.
Public data (SLA licenses, DOHMH, 311, OSM) tells us where bars are and how
often neighbours complain, but nothing about tonight: how full it is, whether
people are dancing, how long the line is, what is playing. Scouts will send
10-second vibe checks and operators will post updates, but raw reports are
sparse, noisy, of mixed age and credibility. Something has to turn them into
three honest numbers per venue — **vibe** (current energy), **match** (fit to
this group), **confidence** (how much fresh, credible support there is) — and
then into a ranked list and a multi-stop night plan with plain-language reasons.

`recs/` is that something: a pure-Python library the backend imports. It also
carries the course ML deliverables (baseline + first model, clustering,
optimization, model chaining).

## 2. Goals

1. G1 — `live_state.compute / compute_all` produce Live Venue State exactly per
   `docs/CONTRACTS.md` (decay, reputation weighting, `null` for missing, separate
   confidence, trend).
2. G2 — `scoring.recommend` returns Recommendation results: weighted-scoring
   baseline, hard-limit exclusions, human-readable `reasons`, explicit `missing`.
3. G3 — Crowd model: gradient boosting predicts crowd (1–5) by venue × hour and
   beats a venue-hour-average baseline under **temporal** validation on synthetic nights.
4. G4 — k-means venue-style clustering on `venue_features` (real public data),
   with labelled, interpretable clusters.
5. G5 — `routing.plan_night` ("Run My Night"): greedy / orienteering planner for
   `n_stops` stops, checked against exhaustive search on small inputs.
6. G6 — Model chaining: clusters → crowd model features; crowd model → live-state
   prior + routing arrival-time forecasts; live state → scoring → routing.
7. G7 — Show the existing complaint-risk model's output as **"311 noise-complaint
   risk"**, never as a quality or vibe signal.
8. G8 — Everything that touches synthetic data is marked and swappable.

## 3. Non-goals

- No HTTP layer, DB schema, auth or deployment (backend).
- No data generation for the app's live tables (live-sim owns `syn_*` tables and
  `data/synthetic_live/`). ml-recs only builds tiny test fixtures and an
  interim stub if live-sim is late.
- No UI (frontend), no Tableau work (tableau), no coursework models (coursework).
- Not deciding the final formula constants — specs owns them in `docs/specs/`;
  ml-recs implements them as config with placeholders until specs lands.
- No collaborative filtering / learned ranking yet (no real feedback). Later.
- No changes to `src/` or `data/manhattan_bars.db` (read-only).

## 4. Users

| User | What they get from `recs/` (through backend/frontend) |
|---|---|
| Consumer / group | ranked list with match/vibe/confidence, reasons, what's unknown; a 2–4 stop night plan |
| Scout | their report moves a venue's state immediately; reputation affects weight (fairness: transparent rule) |
| Venue operator | official updates (cover, DJ, genres) feed live state; demand forecasts (predicted crowd by hour) for the dashboard |
| Backend developer | stable, pure functions with typed dict I/O; no DB or network calls inside |
| Course grader / team | reproducible model evaluation reports (baseline vs model, clustering, routing optimality gap) |

## 5. User stories and acceptance criteria

**US1 Live state from reports.** As a group, I want each venue's current crowd,
dancing, line and cover estimated from recent reports so I can trust what I see.
- AC1.1 Output keys and types match the CONTRACTS Live Venue State exactly (plus
  only approved optional keys, §11).
- AC1.2 A report's weight = reputation × 0.5^(age / half_life); `half_life`
  read from config (placeholder **45 min**, final value from `docs/specs/`).
- AC1.3 Reports older than `max_age` (placeholder **180 min**) or with `ts > now` are ignored.
- AC1.4 With zero usable reports, `crowd/dancing/line_minutes/cover_usd/vibe_score`
  are `null`, `confidence = 0.0`, `n_reports = 0`, `trend = null`. Never a default number.
- AC1.5 A fresh official venue update sets `cover_usd`/`music_genres` and adds
  `"venue_update"` to `sources`; it does not set crowd.
- AC1.6 Confidence rises with effective weight and agreement, is in [0, 1], and
  is computed independently of vibe.
- AC1.7 `trend` ∈ {`rising`, `steady`, `falling`, `null`} from recent-vs-earlier windows.

**US2 Ranked recommendations.** As a group, I want venues ranked by fit with reasons.
- AC2.1 Hard limits exclude: distance > `max_distance_km`; *known* line >
  `max_line_minutes`; *known* cover > `max_cover_usd`. Unknown values never
  exclude; they go in `missing`.
- AC2.2 Excluded venues are returned (after included ones) with `excluded: true`
  and a reason naming the limit, so the UI can show "why not".
- AC2.3 `match_score` is an integer 0–100; components and weights live in config.
- AC2.4 Each included result has 1–4 `reasons`, each citing evidence (count +
  freshness, e.g. "Hip-hop playing (2 reports, 12 min ago)").
- AC2.5 Results whose confidence < display threshold (placeholder **0.35**) carry
  a `missing` note "not enough fresh reports" and their vibe is not used for the match crowd component.
- AC2.6 Deterministic: same inputs + `now` → same output order.

**US3 Crowd forecast.** As an operator / the planner, I want expected crowd by hour.
- AC3.1 `crowd_model.predict(venue_ids, times)` returns crowd 1–5 per pair.
- AC3.2 Evaluation report shows model vs venue-hour-average baseline on
  held-out *later* nights (MAE, RMSE, Spearman); model MAE ≤ 0.9 × baseline MAE
  is the target (placeholder).
- AC3.3 Report states that targets are synthetic and the result measures the
  simulator's structure, not real nightlife.

**US4 Venue styles.** As a user browsing, I want "places like this" groupings.
- AC4.1 k-means on standardized `venue_features` of `v_bars` (1,727 venues);
  k chosen in 3–8 by silhouette + interpretability; seed fixed.
- AC4.2 Each cluster has a generated label and a profile table (means/modes).
- AC4.3 All 35 launch venues get a `cluster_id` and `cluster_label`.

**US5 Run My Night.** As a group, I want a 3-stop plan from where I am.
- AC5.1 `plan_night` returns `n_stops` (default 3) distinct non-excluded venues
  with arrival/leave times, walk minutes per leg, expected vibe at arrival, reasons.
- AC5.2 Constraints: per-leg walk ≤ `max_leg_km` (placeholder 1.0 km); total
  walk ≤ 30 min (placeholder); stops after `start_time`, no stop arrives after 03:30.
- AC5.3 On ≤ 15 candidates, greedy+2-opt objective is within 5% of exhaustive
  optimum on ≥ 90% of test cases (report the gap).
- AC5.4 If fewer than `n_stops` feasible venues, return fewer with a reason; never pad.

**US6 Complaint risk shown honestly.** As a user, I want to know if a venue has
lots of 311 noise complaints without thinking it measures fun.
- AC6.1 Field named `complaint_risk` (0–1) with label "311 noise-complaint risk".
- AC6.2 Not included in `match_score` or `vibe_score` by default.
- AC6.3 Docstring + reasons text never call it quality, popularity or vibe.

## 6. Scope

| MVP (by Nov 17) | Later |
|---|---|
| `live_state` compute/compute_all | Bayesian hierarchical state, outlier/gaming detection beyond simple agreement |
| `scoring.recommend` weighted baseline + exclusions + reasons + missing | learned ranker from `syn_feedback` → real feedback; compatibility score per member of group |
| crowd model (HistGradientBoosting) + baseline + temporal eval report | quantile / interval forecasts; real-data retrain |
| k-means clustering + labels | embeddings / genre-aware clustering once real attributes exist |
| `routing.plan_night` greedy + 2-opt + exhaustive check | time-window orienteering with line-wait forecasts, transit, group splitting |
| chaining (cluster → crowd → state prior → scoring → routing) | heatmap forecast surfaces |
| `complaint_risk` scores for launch venues | "avoid noisy blocks" preference |

## 7. Requirements

Functional
- F1 Public API exactly as CONTRACTS `## Python interface`; extra modules
  (`crowd_model`, `clustering`, `complaint_risk`, `chain`) are additive.
- F2 Accept `now` as tz-aware `datetime` or ISO string; normalize to America/New_York.
- F3 Accept reports/updates as list[dict] (`compute`) or pandas DataFrame (`compute_all`).
- F4 All tunable constants in `recs/config.py`, each with a comment pointing to the
  `docs/specs/` section that defines it (or `PLACEHOLDER`).
- F5 Output `is_synthetic = true` whenever any input row is synthetic or a model
  trained on synthetic data contributed.
- F6 CLI: `python -m recs {train-crowd,cluster,complaint-risk,eval,demo}`.

Non-functional
- N1 `recommend` over 35 venues < 50 ms; `compute_all` for 35 venues × 500 reports < 200 ms; `plan_night` < 300 ms (laptop, placeholder budgets).
- N2 Pure functions: no network, no DB writes, no global mutable state; model
  artifacts loaded lazily once.
- N3 Importable with only `requirements.txt` deps (+pytest for tests). If an
  artifact is missing, functions degrade (no prior / no forecast) instead of crashing.
- N4 Deterministic given seeds.

## 8. Dependencies on other workstreams

| Workstream | We need from them | They need from us |
|---|---|---|
| **specs** | half-life, reputation weighting, vibe formula, confidence + display threshold, match weights, exclusion rules, missing-data rule, trend rule (`docs/specs/`) | feedback on feasibility; our placeholders as a starting draft |
| **research** | interview evidence on which preferences matter (to set match weights), what reasons users trust | — |
| **tableau** | — | functions/CSVs for crowd-by-hour forecasts, cluster profiles, model eval tables (they write extracts into `analytics/tableau/`) |
| **live-sim** | `data/synthetic_live/*.csv` + `syn_*` tables: reports over ≥ 8 Thu–Sat nights, scouts with reputation, venue attributes, updates, feedback; replay `now` | the realism signals the crowd model should be able to learn; validation that state/recs behave sensibly on their output |
| **ml-recs** | (self) | — |
| **backend** | calls our functions; passes reports joined with scout reputation; `now` from query param | stable `recs` API, stub-compatible behaviour, latency budget |
| **frontend** | displays reasons/missing/confidence/"demo data" badge, complaint-risk label wording | exact field semantics and copy for reason strings |
| **coursework** | — (separate exercises) | none; we don't share code |
| **integration** | merge order, final contract decisions, deploy env | passing tests, `docs/workstreams/ml-recs.md`, `docs/synthetic/ml-recs.md` |

## 9. Success metrics

- All contract-shape tests pass; backend integration smoke test calls all 3 public functions.
- Crowd model MAE ≤ 0.9 × baseline MAE on held-out nights (synthetic; placeholder target).
- Clustering silhouette ≥ 0.15 (placeholder) and every cluster nameable in one phrase.
- Routing optimality gap ≤ 5% on ≥ 90% of 200 random small cases.
- Zero "favourable default" violations (property test: removing a report never increases a venue's match).
- Demo run end-to-end in < 5 s on a replayed Saturday night.
- Later (real pilot): click-through on top-3, visited rate (`feedback.visited`), post-visit rating ≥ 4 share.

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Course deliverable dates (Oct 20/27/Nov 3) already passed; 6 days to integration | grade/time | build in priority order (OUTLINE §1); ship baseline first |
| Crowd model learns the simulator's own formula (circular) | inflated metrics | say so in report; also report on a "noisy" sim seed; temporal split; compare to simple baselines |
| live-sim data late or schema drift | blocked eval | interim stub generator under `recs/synthetic/` + schema validation at load |
| specs constants change late | rework | all constants in `config.py`; tests assert properties, not magic numbers |
| Complaint risk misread as quality | misleading product | naming rule, excluded from scores, copy reviewed with frontend |
| Sparse reports → confidence always low in demo | weak demo | crowd-model prior flagged `source: "model"` raises coverage without faking confidence |
| 35 launch venues too few for k-means | unstable clusters | fit on 1,727 `v_bars`, assign launch venues |
| Python 3.13 / pandas 3 API changes (copy-on-write, string dtype) | bugs | pin tested versions, CI-like local test run |

## 11. Contract change requests

(Per CONTRACTS.md, to be copied into `docs/workstreams/ml-recs.md` at build
time. Not applied to CONTRACTS.md.)

1. **Reporter reputation input.** `compute` needs reputation per report. Proposal:
   report rows passed to `recs` carry `reputation` (joined by backend from
   `syn_scouts`); if absent, use `config.DEFAULT_REPUTATION` (placeholder 0.5,
   neutral, not favourable).
2. **Optional Live State keys:** `predicted_crowd` (float|null),
   `predicted_source` (`"crowd_model"`|null). `sources` may contain `"model"`.
   Observed fields (`crowd`, etc.) stay report-only; the prediction never
   overwrites them.
3. **Optional Recommendation keys:** `rank` (int), `cluster_label` (str|null),
   `complaint_risk` (float|null), `is_synthetic` (bool).
4. **`plan_night` return schema** (not yet in CONTRACTS):
   `[{order, venue_id, name, arrive_at, leave_at, walk_minutes, distance_km,
   expected_vibe, match_score, confidence, reasons}]`.
5. **`venues` argument** minimal keys: `venue_id, name, lat, lon` + optional
   `syn_venue_attributes` fields. Backend merges them.
6. **Preferences optional keys for routing:** `start_time` (ISO), `dwell_minutes`
   (default 60), `max_total_walk_minutes` (default 30).
7. **Trend value set** `rising|steady|falling|null` (contract example shows only `rising`).

## 12. Open questions

1. Final half-life, confidence formula and display threshold — specs. (Placeholders: 45 min, k = 1.5, 0.35.)
2. Neutral score for an unknown match component: 0.5 (neutral) or 0 (pessimistic)? Default planned: 0.5 scaled by 0.5 of its weight. Needs specs sign-off that this isn't "favourable".
3. Should a model prior ever appear in `vibe_score`? Current plan: no — only in `predicted_crowd` and routing forecasts.
4. Does live-sim produce enough nights (≥ 8 placeholder, ideally 12 Thu–Sat) for a 2-night held-out test?
5. Should `want_dancing=true` with confidently zero dancing be a hard exclusion or a heavy penalty? Plan: penalty.
6. Group size vs capacity: use `capacity` to penalize small venues for large groups? Plan: soft penalty if `group_size > 0.05 × capacity`.
7. Is complaint risk shown on all cards or only the venue profile? (frontend/specs)
