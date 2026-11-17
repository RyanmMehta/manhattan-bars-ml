# OUTLINE — ml-recs build plan

Rev 3, 2026-11-11, aligned to CONTRACTS v2.2 (commit acf7821) and specs PRD §5.
Sizes: S ≤ 1 h, M 1–3 h, L 3–6 h. Total ≈ 28 h.
Push deadline **Fri Nov 13 18:00 ET**; integration merges ml-recs after live-sim.
The course deliverables dated Oct 20 (baseline + first model), Oct 27 (clustering) and
Nov 3 (optimization), plus chaining, are past due. The order below ships the
backend-critical path first, then each deliverable as its own report.

## 1. Ordered tasks

Phase 0: skeleton (Wed Nov 11–Thu Nov 12 am)
- [ ] 0.1 `recs/` package; `__init__.py` exports `live_state, scoring, routing`; `config.py` with CONTRACTS v2 §A / specs §5 values (S)
- [ ] 0.2 `geo.py` (haversine, walk minutes at 4.5 km/h), `timeutil.py` (parse `now`, NY tz, "night" = 18:00–05:59 belongs to start date), `io.py` (list-of-dicts ⇄ DataFrame normalisation) (S)
- [ ] 0.3 `data.py`: launch venues (`license_id AS venue_id`), names/hours from `venues`/OSM or `data/launch_venues_full.csv`, `venue_features` (read-only), `data/live_sim.db` tables with schema checks, manual-attributes override (M)
- [ ] 0.4 Copy specs golden vectors G1–G8 into `recs/tests/golden/` (synthetic, referenced to source) and write the loader test (S)
- [ ] 0.5 Fixtures: hand-built synthetic CSVs (5 venues, 3 scouts, 40 reports, 4 updates) in `recs/tests/fixtures/synthetic/` (S)
- [ ] 0.6 `recs/synthetic/stub_nights.py` interim generator, **only** if `data/live_sim.db` is not available by Thu noon (M)

Phase 1: live state + baseline scoring (Thu Nov 12) → unblocks backend
- [ ] 1.1 `live_state.compute` per specs §5.1–5.7 (weights, field estimates, vibe, confidence, display, trend, freshness, sources, predicted_crowd hook, is_synthetic) (L)
- [ ] 1.2 `live_state.compute_all` (groupby venue, vectorised weights) (S)
- [ ] 1.3 `scoring.recommend` per specs §5.9–5.11 (exclusions incl. closed-now and `exclude_venue_ids`, components, match, rank_score, rank, reasons, missing) (L)
- [ ] 1.4 `reasons.py` templates; `hours.py` simple `opening_hours` parser (S)
- [ ] 1.5 Golden G1–G8, contract-shape, property and differential (vs `reference_scoring.py`) tests (M)
- [ ] 1.6 `chain.snapshots` helper for live-sim's `demo_night_snapshots.csv` (S)
- [ ] 1.7 Push; message master/backend/live-sim that the API is live (S)

Phase 2: crowd model, Oct 20 deliverable (Thu Nov 12 pm–Fri am)
- [ ] 2.1 Training table: venue × night × hour slot (20–02, 7 one-hour slots ending 03:00); target = weighted mean reported crowd (accepted/pending reports), weights using reputation **as of the report date** from `syn_scout_reputation_history` (M)
- [ ] 2.2 Baseline: venue × slot × weekday mean on train nights → fallback venue mean → global slot mean (S)
- [ ] 2.3 HGB regressor; train Aug 27 → Nov 12 (34 nights), test Nov 13–14; 3-fold rolling origin (M)
- [ ] 2.4 `predict(venue_ids, times)`; artifact + metadata; `reports/crowd_model.md` incl. score vs `syn_true_state` (M)

Phase 3: clustering, Oct 27 deliverable (Fri am)
- [ ] 3.1 Preprocess `venue_features` for `v_bars` (one-hot min_freq 20, scale; variant A without lat/lon, variant B with) (S)
- [ ] 3.2 k sweep 3–8 (inertia, silhouette), pick k, auto-label from top z-scored features (M)
- [ ] 3.3 Assign launch venues; `artifacts/clusters.csv`; `reports/clustering.md` (S)

Phase 4: routing, Nov 3 deliverable (Fri)
- [ ] 4.1 Candidates = top 15 non-excluded from `recommend` (minus `exclude_venue_ids`) (S)
- [ ] 4.2 Time-dependent value: re-score each candidate at its arrival time using the forecast state (M)
- [ ] 4.3 Greedy + 2-opt/swap-in; exhaustive oracle (15·14·13 = 2,730 sequences) (M)
- [ ] 4.4 `routing.plan_night`; `reports/routing.md` with gap on 200 random cases (M)

Phase 5: chaining + complaint risk (Fri pm)
- [ ] 5.1 `complaint_risk.py`: HGB classifier on real `venue_features` (`high_noise`), same setup as `src/evaluate.py`; scores for launch venues (S)
- [ ] 5.2 `chain.py`: cluster → crowd features → predicted_crowd → scoring → routing; ablation table in `reports/chaining.md` (M)
- [ ] 5.3 CLI `python -m recs …` incl. `demo` and `plan` (M)

Phase 6: hand-off (Fri Nov 13, before 18:00)
- [ ] 6.1 `docs/workstreams/ml-recs.md` (as-built, how to run, open issues, CCRs), `docs/synthetic/ml-recs.md` (S)
- [ ] 6.2 Latency check, full test run, push, message master (S)

Cut line if late: Phases 0–1 and 4 are required for the demo. 2, 3 and 5 can land
as reports with degraded chaining (no `predicted_crowd`) without blocking backend.

## 2. File tree to create

```
recs/
  __init__.py            # from . import live_state, scoring, routing
  __main__.py            # CLI
  config.py              # constants = CONTRACTS v2 §A / specs PARAMETERS.md
  geo.py  timeutil.py  io.py  hours.py  reasons.py
  data.py                # read-only loaders + schema checks
  live_state.py          # compute, compute_all
  scoring.py             # recommend
  routing.py             # plan_night, _exhaustive (oracle)
  crowd_model.py         # build_table, Baseline, train, predict, evaluate
  clustering.py          # fit, label, assignments
  complaint_risk.py      # train, scores
  chain.py               # end-to-end pipeline + ablation
  requirements-dev.txt   # pytest
  artifacts/
    clusters.csv  clusters.json                       # real public data
    complaint_risk.joblib  complaint_risk.json        # real public data
    synthetic/crowd_model.joblib  crowd_model.json    # SYNTHETIC
  synthetic/stub_nights.py   # only if live-sim late; SYNTHETIC
  examples/prefs_contract.json  prefs_hiphop_group.json
  reports/ crowd_model.md clustering.md routing.md chaining.md
  tests/
    conftest.py
    golden/G1…G8.json                                 # copies of specs vectors (synthetic)
    fixtures/synthetic/{venues,scouts,scout_reports,venue_updates}.csv
    test_golden.py test_live_state.py test_scoring.py test_routing.py
    test_crowd_model.py test_clustering.py test_complaint_risk.py
    test_contract_shapes.py test_differential.py test_no_truth_leak.py
docs/workstreams/ml-recs.md
docs/synthetic/ml-recs.md
```

## 3. Algorithms (constants from CONTRACTS v2 §A / specs §5; do not change here)

**live_state.compute(venue_id, reports, updates, now)**
- Eligible: `now − 180 min ≤ ts ≤ now + 2 min`; status weight 1 (accepted/pending/missing), 0.5 disputed, 0 flagged/removed.
- Scout `w = 0.5^(age/H_f) · (0.25 + 0.75·r) · (1.0 | 0.6 unverified) · w_status`,
  H_f = 30 (crowd/dancing/line), 60 (cover/genre). Operator `w = 0.5^(age/120) · 0.8`
  (cover/genres/dj only; offers valid until `offer_expires_at`).
- Fields: crowd, dancing = weighted mean; line = weighted median; cover = weighted
  median scout+operator; genres = vote share ≥ 0.30 sorted by share (`[]` if inputs but none clear, `null` if no inputs). Field W < 0.30 → `null`.
- vibe = round(100 · (0.50·(crowd−1)/4 + 0.35·dancing/2 + 0.15·min(line,30)/30) / Σa_available); crowd null → null.
- confidence = round((1 − e^(−W/1.5)) · (1 − 0.5·min(1, sd_w/1.5)) · (1.0 if ≥ 2 scouts else 0.6), 2);
  operator-only → min(0.25, 0.25·Σw) and vibe null.
- display: show ≥ 0.40, low 0.20–0.39, none < 0.20 or vibe null.
- trend: windows [now−30, now] vs [now−90, now−30), W < 0.5 → null, Δ ±0.4.
- freshness_minutes = floor(age of newest contributing input); n_reports = scout reports with w > 0.
- predicted_crowd / predicted_source from `crowd_model.predict` when an artifact exists; never overwrites observed fields; adds `"model"` to `sources` only via these keys.
- All arithmetic on unrounded values; round only on output (G5 needs crowd 3.76).

**scoring.recommend(prefs, states, venues, now)**
- Exclude on known values: cover, line, distance, closed-now (parsed hours), `exclude_venue_ids`. Reason first in `reasons`, also `excluded_reason`.
- Components (weight; score): genre 0.25 (1.0 live genre ∈ prefs; 0.6 static-only overlap; 0.0 known no overlap; 1.0 if prefs empty),
  dancing 0.20 (want → d/2; not want → 1 − d/2; null pref → weight 0), crowd 0.15 (1 − |c − pref|/4),
  line 0.10 (1 − 0.5·line/max), cover 0.10 (1 − 0.5·cover/max; 1.0 if 0), distance 0.15 (1 − d/max),
  group 0.05 (min(1, capacity/(10·group_size))). Unknown → 0.4 + `missing`.
- match = round(100·Σws/Σw); rank_score = match · (0.75 + 0.25·conf); sort rank_score desc, distance asc, venue_id.
- reasons ≤ 3 from top positive w·s components; missing per null field the prefs care about.
- Adds `cluster_label`, `complaint_risk` (lookups; never scored), `is_synthetic`.

**crowd model**
- Rows: venue × night × hour slot with ≥ 1 eligible report. Target: weighted mean crowd, where report weights use as-of reputation
  (join `syn_scout_reputation_history` on scout_id, latest `as_of_date ≤ report date`). Joining final `syn_scouts.reputation` leaks the future (CONTRACTS v2.1 §E).
- Features: slot, weekday (Thu/Fri/Sat), week index, venue static (`style`, `has_dance_floor`, `capacity`,
  `price_level`, `typical_cover_usd`), public (`density_100m`, `osm_closes_late`, `years_licensed`, `liquor_tier`),
  `cluster_id`, venue target-encoding computed on train nights only. **Never** `syn_true_state` / `syn_scout_truth`.
- HGB(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=42), native categorical.
- Split: train Aug 27 → Nov 12 (34 nights), test **Nov 13–14** (2 nights, CONTRACTS §B). Rolling origin: 3 folds of 2 nights each before Nov 13.
- Metrics: MAE, RMSE, Spearman vs reported crowd and vs `crowd_true`; tables for model / baseline / global slot mean.

**clustering**: `venue_features` minus targets (variant A also minus lat/lon); OneHot(min_frequency=20) + StandardScaler;
KMeans(k ∈ 3..8, n_init=10, random_state=42); choose max silhouette unless a cluster < 3% of venues; label by top z-scored features.

**routing.plan_night(prefs, states, venues, start_time, n_stops=3)**
- Candidates: top 15 included recs. Leg minutes = haversine km / 4.5 km/h · 60.
  arrive_k = leave_{k−1} + walk; leave = arrive + dwell (60).
- Value of a stop = rank_score recomputed with the forecast state at arrival
  (predicted crowd if available, else current state with decay); a stop failing hard limits at arrival is infeasible.
- Objective Σ value − 10·Σ walk_km; total walk ≤ 30 min; no repeats.
- Greedy best-marginal, then 2-opt + swap-in until no gain. Exhaustive oracle for tests/report.

## 4. Interfaces

Consumed
- CONTRACTS v2: schemas §E, Preferences (+ §F optional keys), Live State, Recommendation, `plan_night` stop shape.
- `data/launch_venues.csv` (alias `license_id AS venue_id`) / `data/launch_venues_full.csv` (integration), `venues`, `venue_features`, `v_bars` in `data/manhattan_bars.db`.
- `data/live_sim.db` (live-sim): `syn_scout_reports`, `syn_scouts`, `syn_venue_attributes`, `syn_venue_updates`; eval-only `syn_true_state`.
- `data/venue_attributes_manual.csv` (team, optional) overrides synthetic attributes.
- specs: `docs/specs/SCORING.md`, `PARAMETERS.md`, `golden_synthetic/G1–G8`, `tools/reference_scoring.py`, `EVALUATION.md`.
- live-sim `simulator/config/genres.json` (17 slugs): copied into `config.GENRES` with a source comment (no runtime import of `simulator`); a test checks the copy matches when the file exists.
- `syn_scout_reputation_history` (live-sim): as-of reputation for training/evaluation only. The live path uses the current `reputation` the backend joins.

Provided
- `live_state.compute`, `live_state.compute_all`, `scoring.recommend`, `routing.plan_night` (CONTRACTS + v2 §F).
- `crowd_model.predict(venue_ids, times) -> list[float|None]` (backend `demand_by_hour`, tableau, heatmap later).
- `chain.snapshots(reports, updates, start, end, step_minutes=30) -> DataFrame` with the CONTRACTS v2.2 §J columns
  (venue_id, snapshot_ts, crowd, dancing, line_minutes, vibe_score, confidence, n_reports, is_synthetic), so live-sim writes
  `demo_night_snapshots.csv` with exactly our `live_state` (tableau's hour HH = the HH:30 snapshot).
- `clustering.assignments() -> DataFrame[venue_id, cluster_id, cluster_label]`.
- `complaint_risk.scores() -> dict[venue_id, float]`.
- Reports in `recs/reports/` for the course submissions.

## 5. Synthetic datasets needed

| Dataset | Imitates | How generated | Real replacement | Swap steps |
|---|---|---|---|---|
| `data/live_sim.db: syn_scout_reports` (live-sim) | Scout vibe checks, 36 nights Aug 27–Nov 14 | live-sim, seed 42 | `scout_reports` (backend) | backend passes real rows (`INCLUDE_SYNTHETIC=0`); `data.load_reports(source="app")`; retrain crowd model |
| `syn_scouts` (live-sim) | current reputation | live-sim | `scouts` + reputation job | same switch |
| `syn_scout_reputation_history` (live-sim) | reputation over time (as-of joins) | live-sim | `scout_reputation_history` written by the reputation job | same switch; keep as-of join |
| `data/synthetic_live/demo_night_snapshots.csv` (live-sim writes, **our** `live_state` computes) | Live State every 30 min, Sat Nov 14 20:00–03:00 | `recs.chain.snapshots(reports, updates, start, end, step=30)` | not needed with real data (backend computes live) | regenerate after any `live_state` change |
| `syn_venue_attributes` (live-sim) | genres/style/capacity/price/hours | live-sim (+ OSM hours) | `data/venue_attributes_manual.csv` / claimed profiles | add manual rows (override automatically); re-run clustering variant + crowd model |
| `syn_venue_updates` (live-sim) | operator posts | live-sim | `venue_updates` | same switch |
| `syn_true_state` (live-sim, eval only) | ground truth crowd | live-sim | none in production (would be field audits) | drop truth metrics from report |
| `recs/tests/golden/G1–G8.json` (copy of specs) | worked examples | specs, hand-computed | stays synthetic (tests) | re-copy when specs changes |
| `recs/tests/fixtures/synthetic/*.csv` (ours) | a tiny night | hand-written | stays synthetic (tests) | none |
| `recs/synthetic/stub_nights.py` output (ours, only if needed) | Thu–Sat nights × 35 venues | Poisson arrivals by hour × style curve; crowd = f(slot, style) + N(0, 0.6); 10% sloppy scouts; seed 42 | `data/live_sim.db` then real reports | delete stub, `config.REPORTS_SOURCE = "live_sim"` |
| `recs/artifacts/synthetic/crowd_model.joblib` | demand model | trained on synthetic reports | retrain on ≥ 4 weeks of real reports | `python -m recs train-crowd --source app`; move out of `synthetic/`; `is_synthetic=false` in metadata |

Every row above gets an entry in `docs/synthetic/ml-recs.md`.

## 6. Test plan

| Area | Tests |
|---|---|
| Golden | G1–G8 within ±1 point / ±0.01 confidence |
| Differential | `recs` == specs `reference_scoring.py` on 500 random states/prefs (skipped if the oracle file is absent) |
| Contract shapes | keys/types/ranges/JSON for all outputs; `None` never NaN; only approved optional keys; list and DataFrame inputs give the same result |
| live_state | 0 inputs; all stale; ts > now+2; status weights; unverified 0.6; operator-only; W_f < 0.30 → null; trend cases; order-invariance |
| scoring | each exclusion rule incl. closed-now; unknown never excludes; unknown → 0.4 + missing; removing info never raises match; rank_score ordering; determinism |
| crowd model | build_table shape; no leakage (test nights absent from encodings); beats baseline on stub/fixture; unknown venue → None |
| no truth leak | grep test: only `crowd_model.evaluate` references `syn_true_state` / `syn_scout_truth`; training never joins final `syn_scouts.reputation` (test: changing future reputation rows doesn't change the training table) |
| snapshots | `chain.snapshots` columns = CONTRACTS §J; 15 rows per venue (20:00…03:00 every 30 min); values equal `compute_all` at each ts |
| clustering | deterministic; all 35 launch venues assigned; labels non-empty |
| complaint risk | probabilities in [0,1]; not referenced by scoring/routing |
| routing | distinct stops; constraints; fewer when infeasible; increasing times; greedy within gap vs oracle |
| integration | `chain.run(DEMO_NOW)` end-to-end < 5 s; `@pytest.mark.db` tests on the real DBs |

## 7. Demo script (≈ 3 min, DEMO_NOW = Sat 2026-11-14 23:30 ET, synthetic banner)

1. `python -m recs demo --now 2026-11-14T23:30:00-05:00 --prefs recs/examples/prefs_hiphop_group.json`
2. Top 5: match/vibe (with band: Chill 0–34 / Lively 35–64 / Packed 65–100)/confidence/display, reasons ("Hip-hop playing (2 reports, 12 min ago)"),
   missing ("cover not reported tonight"); "3 hidden by your limits" with one `excluded_reason`.
3. Re-run at `--now 2026-11-14T21:00:00-05:00`: thinner reports, more `low`/`none`, `predicted_crowd` from the model.
4. `python -m recs plan --n-stops 3`: 3 stops, arrive times, walk minutes; greedy vs optimal objective.
5. Open `recs/reports/crowd_model.md` (held-out Nov 13–14: model vs baseline), `clustering.md`, `routing.md`, `chaining.md` (ablation).
6. Point at `complaint_risk`: "311 noise-complaint risk, not a quality score".
