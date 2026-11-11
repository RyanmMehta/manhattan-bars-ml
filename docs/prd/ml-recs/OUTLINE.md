# OUTLINE — ml-recs build plan

Sizes: S ≤ 1 h, M 1–3 h, L 3–6 h. Total ≈ 30 h. Today 2026-11-11; integration
2026-11-17. Course deliverables dated Oct 20 (baseline + first model), Oct 27
(clustering), Nov 3 (optimization), chaining are past due — order below ships
the backend-critical path first, then each deliverable as a standalone report.

## 1. Ordered tasks

Phase 0 — skeleton (day 1)
- [ ] 0.1 `recs/` package, `__init__.py` exporting `live_state, scoring, routing`; `config.py` with all placeholders (S)
- [ ] 0.2 `geo.py` (haversine, walk minutes), `timeutil.py` (parse `now`, NY tz, "night" = 18:00–05:59 belongs to start date) (S)
- [ ] 0.3 `data.py` loaders: launch venues (+name/lat/lon from `venues`), `venue_features` (read-only DB), live-sim CSVs with schema validation (M)
- [ ] 0.4 Test fixtures: hand-built synthetic CSVs (5 venues, 3 scouts, 40 reports, 4 updates) in `recs/tests/fixtures/synthetic/` (S)
- [ ] 0.5 `recs/synthetic/stub_nights.py`: interim generator (only if live-sim not ready by day 2) — 35 venues × 12 Thu–Sat nights (M)

Phase 1 — live state + baseline scoring (day 1–2) → unblocks backend
- [ ] 1.1 `live_state.compute`: decay × reputation × verified boost, weighted mean crowd/dancing, weighted median line, cover/genres from updates-first, vibe, confidence, freshness, trend, sources, is_synthetic (L)
- [ ] 1.2 `live_state.compute_all` (groupby venue, vectorized weights) (S)
- [ ] 1.3 `scoring.recommend`: exclusions, components, weights, rank, reasons, missing (L)
- [ ] 1.4 `reasons.py`: templated reason/missing strings (S)
- [ ] 1.5 Contract + property tests for 1.1–1.3 (M)
- [ ] 1.6 Push; tell backend the API is live (S)

Phase 2 — crowd model (Oct 20 deliverable) (day 2–3)
- [ ] 2.1 Build training table: venue × night × hour (20:00–03:00) target = mean reported crowd; features below (M)
- [ ] 2.2 Baseline: venue × hour-of-night × weekday-type mean from train nights, fallback venue mean → global hour mean (S)
- [ ] 2.3 HistGradientBoostingRegressor; temporal split (train first N−2 nights, test last 2) + rolling-origin (3 folds) (M)
- [ ] 2.4 `predict(venue_ids, times)`; artifact + metadata; `reports/crowd_model.md` (M)

Phase 3 — clustering (Oct 27 deliverable) (day 3)
- [ ] 3.1 Preprocess `venue_features` for `v_bars` (one-hot cats min_freq 20, scale nums, drop targets + lat/lon variant A; with lat/lon variant B) (S)
- [ ] 3.2 k sweep 3–8: inertia, silhouette; pick k; label clusters from profile (M)
- [ ] 3.3 Assign launch venues; `artifacts/clusters.csv` (real data → not synthetic); `reports/clustering.md` (S)

Phase 4 — routing (Nov 3 deliverable) (day 3–4)
- [ ] 4.1 Candidates = top-K (K=15) non-excluded from `recommend` (S)
- [ ] 4.2 Objective: Σ stop_value(t_arrive) − λ·walk_min; stop_value = match with crowd component recomputed from forecast at arrival (M)
- [ ] 4.3 Greedy + 2-opt / swap improvement; exhaustive for K ≤ 15, n ≤ 3 as oracle (M)
- [ ] 4.4 `routing.plan_night`; `reports/routing.md` with optimality gap on 200 random cases (M)

Phase 5 — chaining + complaint risk (day 4–5)
- [ ] 5.1 `complaint_risk.py`: train HGB classifier on real `venue_features` (`high_noise`), score launch venues, artifact (S)
- [ ] 5.2 `chain.py`: cluster → crowd features; crowd forecast → `predicted_crowd` in state; → scoring → routing; ablation table (with/without each link) in `reports/chaining.md` (M)
- [ ] 5.3 CLI `python -m recs …`, demo command (M)

Phase 6 — docs + hand-off (day 5)
- [ ] 6.1 `docs/workstreams/ml-recs.md`, `docs/synthetic/ml-recs.md`, contract change requests (S)
- [ ] 6.2 Latency check, final test run, push (S)

## 2. File tree to create

```
recs/
  __init__.py            # from . import live_state, scoring, routing
  __main__.py            # CLI entry
  config.py              # all constants (spec refs / PLACEHOLDER)
  geo.py  timeutil.py  reasons.py
  data.py                # loaders + schema checks (read-only DB)
  live_state.py          # compute, compute_all
  scoring.py             # recommend
  routing.py             # plan_night, _exhaustive (oracle)
  crowd_model.py         # build_table, Baseline, train, predict, evaluate
  clustering.py          # fit, label, assign
  complaint_risk.py      # train, score
  chain.py               # end-to-end pipeline + ablation
  requirements-dev.txt   # pytest
  artifacts/
    clusters.csv  clusters.json                 # real public data
    complaint_risk.joblib  complaint_risk.json  # real public data
    synthetic/crowd_model.joblib  crowd_model.json   # SYNTHETIC
  synthetic/stub_nights.py   # only if live-sim late; SYNTHETIC
  reports/ crowd_model.md clustering.md routing.md chaining.md
  tests/
    conftest.py
    fixtures/synthetic/{venues,scouts,scout_reports,venue_updates}.csv
    test_live_state.py test_scoring.py test_routing.py
    test_crowd_model.py test_clustering.py test_complaint_risk.py test_contract_shapes.py
docs/workstreams/ml-recs.md
docs/synthetic/ml-recs.md
```

## 3. Algorithms (placeholder constants; final values from docs/specs/)

**live_state.compute(venue_id, reports, updates, now)**
- usable = reports with `venue_id` match, `0 ≤ age ≤ MAX_AGE_MIN (180)`.
- `w_i = rep_i × 0.5^(age_i / HALF_LIFE_MIN (45)) × (1.25 if verified_presence else 1.0)`.
- crowd, dancing = Σw·x / Σw (1 dp); line_minutes = weighted median (int); each field
  uses only reports where it is non-null.
- cover_usd: latest update with non-null cover within 6 h wins; else weighted
  median of scout cover; else `None`. music_genres: update genres ∪ scout genres with weight share ≥ 0.25.
- vibe_score = round(100 × (0.55·(crowd−1)/4 + 0.35·dancing/2 + 0.10·min(line,30)/30));
  `None` if crowd is None (dancing None → renormalize remaining weights).
- confidence = (1 − exp(−Σw / K_CONF (1.5))) × agreement, agreement =
  1 − min(1, weighted_sd(crowd)/2); 0.0 with no reports.
- freshness_minutes = age of newest usable report/update; n_reports = len(usable).
- trend: weighted crowd in last 30 min vs 30–90 min; Δ ≥ +0.3 rising, ≤ −0.3
  falling, else steady; `None` if either window has total weight < 0.5.
- sources: `scout` if any report, `venue_update` if any update used, `model` if a prediction was attached.

**scoring.recommend(prefs, states, venues, now)**
- Exclude (with reason) if distance > max_distance_km, known line > max_line_minutes, known cover > max_cover_usd.
- Components s ∈ [0,1], weights: genre 0.30 (Jaccard-ish overlap of prefs.genres with
  live genres, else static `genres` at half credit), crowd 0.25 (1 − |crowd − crowd_pref|/4,
  only if confidence ≥ 0.35), dancing 0.15 (want_dancing → dancing/2; else 1 − dancing/2),
  distance 0.15 (1 − d/max_d), line 0.10 (1 − line/max_line), cover 0.05 (1 − cover/max_cover).
- Unknown component → s = 0.5 × weight credit 0.5 (open question in PRD); listed in `missing`.
- match_score = round(100 × Σ w·s / Σ w). Sort included by (−match, −confidence, distance, venue_id).
- reasons: top 3 components by w·s with evidence strings. Complaint risk never appears in reasons; it is a separate `complaint_risk` field only.

**crowd model**
- Rows: venue × night × hour slot (20–03 → 8 slots). Target: mean crowd of reports in slot (rows with ≥ 1 report).
- Features: hour_slot, weekday (Thu/Fri/Sat), venue static (`style`, `has_dance_floor`,
  `capacity`, `price_level`, `typical_cover_usd`), public (`density_100m`,
  `osm_closes_late`, `years_licensed`, `liquor_tier`), `cluster_id`, venue target-encoding (train nights only).
- Model: HGB(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=42), categorical support native.
- Validation: temporal hold-out last 2 nights + 3-fold rolling origin. Metrics: MAE, RMSE, Spearman; report vs baseline and vs global-hour mean.

**clustering** — features = `venue_features` minus targets (and minus lat/lon in variant A);
OneHot(min_frequency=20) + StandardScaler; KMeans k ∈ 3..8; choose max silhouette
unless a cluster < 3% of venues. Label by top distinguishing features (z-score of cluster mean).

**routing.plan_night(prefs, states, venues, start_time, n_stops=3)**
- Candidates: top 15 included recs. Leg time = walk_min(prev, next). Arrival
  t_k = leave_{k−1} + walk; leave = arrive + DWELL (60).
- stop_value = match_score recomputed with forecast crowd at arrival (crowd model,
  fallback current state); objective = Σ stop_value − λ(0.8)·Σ walk_min.
- Greedy: pick best marginal value; then 2-opt + swap-in from unused candidates until no gain.
- Oracle: exhaustive permutations (15·14·13 = 2,730) for tests/report.

## 4. Interfaces

Consumed
- `docs/CONTRACTS.md` schemas: `syn_scout_reports`, `syn_venue_updates`,
  `syn_scouts` (reputation), `syn_venue_attributes`, `syn_feedback` (later), Preferences.
- `data/launch_venues.csv` (35 venues; `venue_id` = `license_id`), `venues` (name), `venue_features`, `v_bars`.
- `data/synthetic_live/*.csv` from live-sim (training nights + replay).
- `docs/specs/` scoring/freshness/credibility constants.

Provided
- `live_state.compute`, `live_state.compute_all`, `scoring.recommend`,
  `routing.plan_night` (CONTRACTS shapes + change requests in PRD §11).
- `crowd_model.predict(venue_ids, times) -> list[float|None]` (backend owner
  dashboard demand; tableau extracts).
- `clustering.assignments() -> DataFrame[venue_id, cluster_id, cluster_label]`.
- `complaint_risk.scores() -> dict[venue_id, float]`.
- Reports in `recs/reports/` for coursework submissions.

## 5. Synthetic datasets needed

| Dataset | Imitates | How generated | Real replacement | Swap steps |
|---|---|---|---|---|
| `data/synthetic_live/syn_scout_reports.csv` (live-sim) | real Scout vibe checks | live-sim simulator | `scout_reports` table from backend (`POST /api/reports`) | point `data.load_reports()` at DB table; drop `is_synthetic` filter; retrain crowd model |
| `syn_scouts.csv` (live-sim) | scout reputation | live-sim | backend `scouts` table + reputation job | same loader switch |
| `syn_venue_attributes.csv` (live-sim) | genres/style/capacity/price | live-sim | operator-claimed profiles / manual curation | loader switch; re-run clustering variant with attributes |
| `syn_venue_updates.csv` (live-sim) | operator posts | live-sim | `venue_updates` table | loader switch |
| `recs/tests/fixtures/synthetic/*.csv` (ours) | tiny night for tests | hand-written, deterministic | stays synthetic (test only) | none |
| `recs/synthetic/stub_nights.py` output (ours, only if needed) | 12 Thu–Sat nights × 35 venues | Poisson arrivals by hour × style curve, crowd = f(hour, style) + N(0, 0.6), 10% bad scouts | live-sim output, then real reports | delete stub, set `config.REPORTS_SOURCE="live_sim"` |
| `recs/artifacts/synthetic/crowd_model.joblib` | demand model | trained on synthetic reports | retrain on ≥ 4 weeks of real reports | `python -m recs train-crowd --source db`; move out of `synthetic/`; set `is_synthetic=false` |

Every row above gets an entry in `docs/synthetic/ml-recs.md`.

## 6. Test plan

| Area | Tests |
|---|---|
| Contract shapes | keys/types/ranges/JSON for all public outputs; `null` never NaN |
| live_state | 0 reports; all stale; future ts; decay monotonic in age; reputation weighting; verified boost; update overrides cover; trend rising/falling/steady/None; order-invariance |
| scoring | each hard limit excludes with reason; unknown never excludes; removing info never increases match; low-confidence crowd ignored; determinism; reasons cite counts/minutes |
| crowd model | build_table shape; no leakage (test nights absent from target encoding); model < baseline MAE on fixture/stub; predict handles unknown venue → None |
| clustering | deterministic with seed; all 35 launch venues assigned; labels non-empty |
| complaint risk | probabilities in [0,1]; not referenced by scoring (grep/unit) |
| routing | n distinct stops; constraints respected; returns fewer when infeasible; greedy within 5% of oracle on fixture cases; times increasing |
| integration | `chain.run(now)` end-to-end on fixtures < 5 s; `@pytest.mark.db` tests on real DB |

## 7. Demo script (≈ 3 min)

1. `python -m recs demo --now 2026-11-14T23:30:00-05:00 --prefs examples/hiphop_group.json`
   (Saturday replay, synthetic — banner says "demo data").
2. Show top 5: match/vibe/confidence, reasons ("Hip-hop playing (2 reports, 12 min
   ago)"), missing ("cover not reported tonight"), one excluded venue with "line ~25 min, over your 15".
3. Re-run with `--now 2026-11-14T21:00` → fewer reports, lower confidence, `predicted_crowd` from model.
4. `python -m recs plan --n-stops 3` → 3 stops with arrive times and walk minutes; show greedy vs optimal objective.
5. Open `recs/reports/crowd_model.md` (model vs baseline MAE), `clustering.md`
   (cluster profiles + launch venue labels), `chaining.md` (ablation).
6. Point at complaint-risk column: "311 noise-complaint risk — not a quality score".
