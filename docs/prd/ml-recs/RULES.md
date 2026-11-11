# RULES — ml-recs build session

Rules for the session that builds `recs/`. Read this, `docs/CONTRACTS.md`
(**including the v2 amendments, which override the top**), `docs/specs/SCORING.md` +
`PARAMETERS.md` (or `docs/prd/specs/PRD.md` §5 until they exist),
`docs/prd/ml-recs/PRD.md` and `OUTLINE.md` before writing code. Rev 3, 2026-11-11 (CONTRACTS v2.2).

## Stack and versions
- Python **3.13** (container: 3.13.x). No other language.
- Runtime deps: only what `requirements.txt` already lists — pandas ≥ 3.0,
  numpy ≥ 2.0, scipy ≥ 1.14, scikit-learn ≥ 1.6 (joblib comes with it). Do not
  add xgboost, lightgbm, torch, ortools, networkx, geopandas.
- Test deps: `pytest` (and `hypothesis` only if already installed; otherwise
  hand-rolled property loops). Put test deps in `recs/requirements-dev.txt`, not
  the root file.
- Models: `sklearn.ensemble.HistGradientBoostingRegressor` (crowd),
  `HistGradientBoostingClassifier` (complaint risk, same setup as `src/evaluate.py`),
  `sklearn.cluster.KMeans(n_init=10, random_state=SEED)`.
- Distances: haversine in `recs/geo.py`; walking speed 4.5 km/h (specs §5.12), routing walk cost 10 per km.

## Folder ownership
- You own **`recs/`** only, plus `docs/workstreams/ml-recs.md` and
  `docs/synthetic/ml-recs.md`, and `docs/prd/ml-recs/`.
- Read-only: `data/manhattan_bars.db`, `data/live_sim.db` (live-sim; separate DB, CONTRACTS v2 §D),
  `data/launch_venues.csv` (header `license_id`, alias `AS venue_id`), `data/launch_venues_full.csv`,
  `data/venue_attributes_manual.csv`, `docs/specs/` (specs), `simulator/config/genres.json`, `data/synthetic_live/` (live-sim), `src/`.
- Never touch: `src/`, `backend/`, `frontend/`, `simulator/`, `analytics/`,
  `research/`, `coursework/`, `tests/`, `scripts/`, `.github/`, `Makefile` (integration),
  `docs/CONTRACTS.md`, other workstreams' docs, `main`.
- Do not import `simulator` or `backend` at runtime; copy the 17 genre slugs into `config.GENRES` with a source comment.
- Open DB connections read-only: `sqlite3.connect("file:...?mode=ro", uri=True)`.

## Coding conventions
- Public API exactly per CONTRACTS `## Python interface`. Signatures don't change
  without a contract change request.
- Pure functions: no network, no DB writes, no prints in library code (use
  `logging.getLogger("recs")`), no global mutable state except a lazy artifact cache.
- Inputs: dicts / DataFrames with CONTRACTS column names. Outputs: plain
  JSON-serializable dicts (no numpy scalars, no NaN — use `None`). Round:
  scores int, crowd/dancing 1 dp, confidence 2 dp.
- `now` and timestamps: tz-aware, America/New_York (`zoneinfo`). Accept ISO strings.
- Every constant in `recs/config.py` with a comment `# spec: docs/specs/<file>#<section>`.
  Values must equal CONTRACTS v2 §A (half-life 30/60/120 min, cutoff 180 min / now+2 min,
  `w_rep = 0.25 + 0.75·r`, unverified 0.6, k 1.5, display 0.40/0.20, unknown component 0.4,
  `rank_score = match · (0.75 + 0.25·conf)`, trend Δ ±0.4). Never tune them locally; raise them with specs.
- Compute on unrounded values; round only when building output dicts (golden G5 depends on it).
- Inputs may be lists of dicts or DataFrames; normalise once in `recs/io.py`.
- Missing data → `None`, listed in `missing`; unknown match components score 0.4. **Never fill with a favourable default.**
- `predicted_crowd` never overwrites observed fields and never raises `confidence`.
- Evaluation-only tables `syn_true_state` and `syn_scout_truth` may be read **only** in
  `crowd_model.evaluate` (and reports). Never as features, never in `live_state`/`scoring`/`routing`.
- Training/evaluation joins reputation **as of the report date** from `syn_scout_reputation_history`; never join the
  final `syn_scouts.reputation` to past reports. The live path uses the `reputation` the backend passes in.
- `complaint_risk` is always labelled "311 noise-complaint risk"; never feeds
  `match_score`/`rank_score`/`vibe_score`/reasons/routing; never described as quality.
- Type hints on public functions; docstrings state inputs, outputs, units.
- Formatting: PEP 8, line ≤ 110, `ruff` if available (not required).
- Seeds: `config.SEED = 42`; every random op takes a seed.
- Model artifacts: `joblib` files under `recs/artifacts/synthetic/` (trained on
  synthetic) or `recs/artifacts/` (trained on real public data only), each with a
  sibling `.json` metadata (trained_at, data source, rows, metrics, `is_synthetic`).
  Artifacts ≤ 5 MB each; if git-ignored, document regeneration command.

## Synthetic-data marking (mandatory, from CONTRACTS)
1. Every synthetic CSV/table has `is_synthetic` (1). Outputs computed from
   synthetic inputs carry `is_synthetic: true`.
2. Synthetic files live under a path containing `synthetic`
   (`recs/tests/fixtures/synthetic/`, `recs/artifacts/synthetic/`, `recs/synthetic/`);
   any DB table we would create is prefixed `syn_` (we don't plan to create any). Synthetic IDs
   we create (fixtures, stub) start with `syn-` (e.g. `syn-r-000123`).
3. Mark every code spot that uses synthetic data:
   `# SYNTHETIC: <real source that replaces this>`.
4. Register every synthetic dataset/artifact in `docs/synthetic/ml-recs.md`:
   file/table, what it imitates, how generated, real replacement, swap steps.
5. Reports (`recs/reports/*.md`) that use synthetic data start with a
   "Demo data — synthetic" banner.

## Testing requirements
- `pytest recs/tests -q` passes with zero failures before every push.
- Golden vectors G1–G8 (specs) reproduced within ±1 point / ±0.01 confidence.
- Differential test against specs' `docs/specs/tools/reference_scoring.py` when present.
- Contract-shape tests for `live_state.compute`, `scoring.recommend`,
  `routing.plan_night` (keys, types, ranges, JSON-serializable, list vs DataFrame inputs equal).
- A test that fails if library modules reference `syn_true_state` / `syn_scout_truth`, and one proving the training table
  is unchanged when future reputation-history rows change.
- Property tests: removing a report never raises confidence; adding an older
  duplicate report changes state less than a fresh one; unknown values never cause
  exclusion; removing information never increases `match_score`; output stable under input order shuffle.
- Edge cases: zero reports, all reports stale, future-dated report, one venue,
  empty venues list, NaN fields, `n_stops` > feasible.
- Model tests: crowd model beats baseline on the fixture split; clustering
  deterministic with seed; routing greedy within gap vs exhaustive on fixtures.
- Tests must run without `data/manhattan_bars.db` except those marked
  `@pytest.mark.db` (skip if missing). Total runtime < 60 s.

## Git
- Branch `nightlife/ml-recs` only; `git push -u origin nightlife/ml-recs`.
- No PRs, no pushes to `main`, no force-push of others' history.
- Push deadline: **Fri Nov 13 18:00 ET** (CONTRACTS v2 §I).
- Small commits with clear messages.

## Definition of done
- [ ] Public functions match CONTRACTS shapes; approved optional keys only.
- [ ] All tests pass; latency budgets in PRD N1 met (measured in a test or report).
- [ ] `recs/reports/crowd_model.md`, `clustering.md`, `routing.md`, `chaining.md` generated by the CLI.
- [ ] Golden G1–G8 pass.
- [ ] `python -m recs demo --now 2026-11-14T23:30:00-05:00` (DEMO_NOW) prints recs + plan.
- [ ] `docs/workstreams/ml-recs.md` (what/how to run/open issues/contract change requests).
- [ ] `docs/synthetic/ml-recs.md` lists every synthetic item.
- [ ] grep check: every file reading synthetic data has a `# SYNTHETIC:` comment.
- [ ] Backend smoke: `from recs import live_state, scoring, routing` works in a clean venv with `requirements.txt`.
