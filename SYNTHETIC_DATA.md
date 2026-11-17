# Synthetic data in this repo

> **Generated** by `scripts/integration/consolidate_synthetic.py` (`make synthetic-docs`) from
> every `docs/synthetic/<workstream>.md`. Edit those files, not this one.

Nightlife Autopilot has **no real live data yet**. Everything about "tonight" (scout reports,
venue updates, crowds, users, points, bounties, owner analytics, interview data) is
**synthetic**, generated deterministically (seed 42) for the Nov 17 class demo. The only real
data is the public-data pipeline: NY SLA licences, NYC DOHMH inspections, NYC 311 noise
complaints and OpenStreetMap (`data/manhattan_bars.db`, `data/launch_venues*.csv`).

How to spot it (CONTRACTS.md "Synthetic data rule"):
1. every synthetic table/CSV has `is_synthetic = 1`;
2. synthetic files live under a path containing `synthetic`; synthetic DB tables start with `syn_`;
   synthetic primary keys start with `syn-`;
3. code that reads synthetic data is marked `# SYNTHETIC: <real source>` / `// SYNTHETIC:`;
4. the UI shows a **demo data** badge wherever synthetic data is shown.

## The global swap switch (step 1 of every swap)

Every app table has a real twin without the `syn_` prefix (`scout_reports`, `venue_updates`,
`venue_events`, `feedback`, `bounties`, `disputes`, `points_ledger`), created empty by the
backend from day one. The backend reads `syn_x UNION ALL x`.

1. Start writing real rows into the un-prefixed twin (the app's POST endpoints already do).
2. When the real table has enough data, set `INCLUDE_SYNTHETIC=0` on the backend (Render env).
   `/api/health` then reports `"data": "real"` and lists return `X-Data: real`.
3. Stop running `python -m simulator --seed 42 --out data/live_sim.db` in the build and unset
   `DEMO_NOW` / `VITE_DEMO_NOW` so the app uses the wall clock.
4. Remove the dataset's `SYNTHETIC:` code paths listed below and its row in the owner's registry.

Checked by `tests/contract/test_isolation.py::test_include_synthetic_off`.

## Evaluation-only tables (never swapped into the app)

`syn_true_state` and `syn_scout_truth` are the simulator's hidden ground truth. They are read
only by evaluation/test code, never by `backend/`, `recs/` runtime or model features
(checked by `tests/contract/test_isolation.py`). With real data they simply disappear;
evaluation then uses post-visit feedback and audits instead.

## Master index

| owner | dataset (file/table) | imitates | real replacement | swap steps |
|---|---|---|---|---|
| backend | `backend/tests/fixtures/synthetic/fixture_live_sim.db` (all `syn_` tables, `is_synthetic=1`, IDs `syn-…`) | a one-night `live_sim.db`: 35 venue attributes, 20 scouts, 5 users, 200 reports Sat Nov 14 20:00–03:00, 15 updates, 5 bounties, 400 events, ledger, feedback, 1 dispute | live-sim's `data/live_sim.db`, then real tables | tests/dev only (`ALLOW_FIXTURE_SIM=1`); `0` on Render, so prod never silently uses it |
| backend | `sim.syn_venue_attributes` | venue genres/style/dance floor/cover/capacity/price/claimed/hours | `data/venue_attributes_manual.csv` (overrides per venue), later owner edits in `venue_attributes` | fill the CSV; no code change |
| backend | `sim.syn_scouts` | scout profiles + current reputation | `scouts` (demo-login) | `INCLUDE_SYNTHETIC=0` |
| backend | `sim.syn_users` | group members | `users` | same |
| backend | `sim.syn_scout_reports` | vibe checks | `scout_reports` (`POST /api/reports`) | same; columns identical |
| backend | `sim.syn_venue_updates` | operator posts / offers | `venue_updates` (`POST /api/owner/{id}/updates`) | same |
| backend | `sim.syn_venue_events` | views/taps/saves/impressions | `venue_events` logged by the API | same |
| backend | `sim.syn_points_ledger` | points history | `points_ledger` written by `POST /api/reports` | same |
| backend | `sim.syn_bounties` | open bounties | `bounties` (creation job, later) | same |
| backend | `sim.syn_feedback` | post-visit outcomes | `feedback` (`POST /api/feedback`) | same |
| backend | `sim.syn_disputes` | report disputes | `disputes` (later) | registered only; no endpoint reads it |
| integration | `DEMO_NOW` / `VITE_DEMO_NOW` pinned clock (`2026-11-14T23:30:00-05:00`) | "right now" on a busy Saturday | the wall clock | unset `DEMO_NOW` on Render and `VITE_DEMO_NOW` on Vercel; redeploy |
| integration | G1/G5 report fixtures inline in `tests/contract/test_recs_interface.py` | four scout reports at one venue | not replaced (unit-test fixture) | none; keep as regression tests |
| research | `research/synthetic/syn_interviews.csv` (15 rows: 8 consumer, 3 scout, 4 operator) | Coded notes from semi-structured interviews | `research/interviews/interviews.csv`, filled from `research/interview_guide/note_template.md` (IDs `int-r-###`, `is_synthetic=0`) | 1. Log real rows with the same columns. 2. `python -I research/validate.py --real`. 3. `python -I research/analysis.py --source real`. 4. Re-tag `research/summary.md` findings as `[REAL n=…]`. 5. Keep the synthetic CSV for demos or delete it; there's no DB to clean. |
| research | `research/synthetic/syn_interview_quotes.csv` (4–6 per interview; 75 rows) | Tagged, anonymized verbatim quotes | `research/interviews/quotes.csv` (IDs `q-r-####`), transcribed from notes with no PII | Same as above. Remove the `[SYNTHETIC] ` prefix rule only for real rows (the validator checks it only for synthetic ones). |
| research | `research/synthetic/syn_survey_responses.csv` (300 rows) | Online survey export (Google Forms) mapped to the codebook | `research/survey/responses.csv`: the real export renamed and recoded per `research/survey/codebook.csv` (IDs `srv-r-####`, `is_synthetic=0`) | 1. Export the CSV. 2. Rename and recode columns per the codebook (see `research/survey/questions.md`, "Export → codebook mapping"). 3. `python -I research/validate.py --real`. 4. `python -I research/analysis.py --source real`. 5. Point the tableau extract at `research/survey/summary_tables.csv`. |
| research | `research/synthetic/summary_tables.csv` (145 rows: `metric, segment, value, n, is_synthetic`) | Aggregated findings for the voice-of-customer dashboard | Same script with `--source real` → `research/survey/summary_tables.csv` | Re-run with `--source real`. Charts must drop the "demo data" title only once `is_synthetic = 0`. |
| specs | `docs/specs/golden_synthetic/G1_normal_four_scouts.json` … `G8_trend_rising_falling.json` (files: G1_normal_four_scouts.json, G2_stale_reports.json, G3_single_scout.json, G4_operator_only.json, G5_match_contract_prefs.json, G6_exclusion_known_vs_unknown.json, G7_disputed_and_flagged.json, G8_trend_rising_falling.json) | small slices of a night's scout reports, operator updates, scouts and venue attributes at real launch venues | **not replaced** — test fixtures. Optionally add a vector from a real anonymised pilot night | keep; after a parameter change run `python -I docs/specs/tools/check_golden.py --regen`, review diff, commit, tell ml-recs/backend |
| specs | `docs/specs/golden_vectors.json` | bundle of the same G1–G8 vectors + parameters + tolerances | not replaced (test fixture) | regenerated with the files above. Lives outside a `synthetic` path because the build brief fixed this path; file and every row carry `is_synthetic: 1` |
| specs | `docs/specs/golden_synthetic/personas_synthetic.json` | 5 group personas' Preferences (dancer group, cocktail pair, budget crew, group of 8, no prefs) | research interview results | replace values, keep ids, set `is_synthetic: 0`, update this row |
| specs | Venue `capacity`/`genres` inside golden vectors | `syn_venue_attributes` | `data/venue_attributes_manual.csv` | update `VENUES` in `build_golden.py`, regen |
| specs | Parameter values in `docs/specs/PARAMETERS.md` | tuned constants | tuning on live-sim training nights, then pilot data | edit table + JSON block, regen goldens, notify master |
| specs | Targets in `docs/specs/pilot-metrics.md` §1 | pilot goals | real pilot baseline / course feedback | edit table |
| tableau | `analytics/tableau/extracts/synthetic/syn_tonight_reports.csv` | Scout vibe checks (`syn_scout_reports` v2 columns) at the 35 launch venues, Sat Nov 14 2026 20:00-03:00 ET | 1) live-sim `data/live_sim.db` `syn_scout_reports`; 2) real `scout_reports` via backend (`INCLUDE_SYNTHETIC=0`) | Generate `python -I -m simulator --seed 42 --out data/live_sim.db` (or set `LIVE_SIM_DB`), rerun the exporter, check `tonight_source = live-sim`, Tableau Data → Refresh, republish, rerun `render_standin.py` |
| tableau | `analytics/tableau/extracts/synthetic/syn_tonight_heatmap.csv` | Hourly Live Venue State per launch venue (35 × 7 = 245 rows; cell HH = HH:30 snapshot, v2.2 §J) | `GET /api/heatmap?now=2026-11-14T23:30:00-05:00&by=hour` from backend over real reports | Same as SYN-T1; for real data, fetch the API into the same columns (exporter `--tonight-source api` is a later item, see workstream doc) |

### Pre-existing public-pipeline synthetic data

`data/synthetic/*` and the `synthetic_{independent,copula,cart}_10000` tables in `data/manhattan_bars.db` are synthetic *training* rows from `src/simulate.py` (see README §3). They imitate `venue_features` and are not used by the app.

## Per-workstream registries

### backend  (`docs/synthetic/backend.md`)

### Synthetic data registry: backend

The backend generates only one synthetic dataset (the test fixture). Everything else it reads
is generated by live-sim into `data/live_sim.db` (see `docs/synthetic/live-sim.md`).
`INCLUDE_SYNTHETIC=0` hides every row below (switch lives in `backend/app/repo/sources.py`).

| File / table | Imitates | Generated by | Real replacement | Swap steps |
|---|---|---|---|---|
| `backend/tests/fixtures/synthetic/fixture_live_sim.db` (all `syn_` tables, `is_synthetic=1`, IDs `syn-…`) | a one-night `live_sim.db`: 35 venue attributes, 20 scouts, 5 users, 200 reports Sat Nov 14 20:00–03:00, 15 updates, 5 bounties, 400 events, ledger, feedback, 1 dispute | `backend/app/fixture_sim.py` (seed 42), built at test time / dev boot; gitignored | live-sim's `data/live_sim.db`, then real tables | tests/dev only (`ALLOW_FIXTURE_SIM=1`); `0` on Render, so prod never silently uses it |
| `sim.syn_venue_attributes` | venue genres/style/dance floor/cover/capacity/price/claimed/hours | live-sim | `data/venue_attributes_manual.csv` (overrides per venue), later owner edits in `venue_attributes` | fill the CSV; no code change |
| `sim.syn_scouts` | scout profiles + current reputation | live-sim | `scouts` (demo-login) | `INCLUDE_SYNTHETIC=0` |
| `sim.syn_users` | group members | live-sim | `users` | same |
| `sim.syn_scout_reports` | vibe checks | live-sim | `scout_reports` (`POST /api/reports`) | same; columns identical |
| `sim.syn_venue_updates` | operator posts / offers | live-sim | `venue_updates` (`POST /api/owner/{id}/updates`) | same |
| `sim.syn_venue_events` | views/taps/saves/impressions | live-sim | `venue_events` logged by the API | same |
| `sim.syn_points_ledger` | points history | live-sim | `points_ledger` written by `POST /api/reports` | same |
| `sim.syn_bounties` | open bounties | live-sim | `bounties` (creation job, later) | same |
| `sim.syn_feedback` | post-visit outcomes | live-sim | `feedback` (`POST /api/feedback`) | same |
| `sim.syn_disputes` | report disputes | live-sim | `disputes` (later) | registered only; no endpoint reads it |

Never read by the API: the evaluation-only truth tables and the reputation-history table
(a test greps `backend/app/` for their names). Every read site carries a `# SYNTHETIC:` comment.

### integration  (`docs/synthetic/integration.md`)

### Synthetic data registry — integration

| Dataset (file/table) | Imitates | How generated | Real replacement | Swap steps |
|---|---|---|---|---|
| `DEMO_NOW` / `VITE_DEMO_NOW` pinned clock (`2026-11-14T23:30:00-05:00`) | "right now" on a busy Saturday | config constant (CONTRACTS v2 §B) | the wall clock | unset `DEMO_NOW` on Render and `VITE_DEMO_NOW` on Vercel; redeploy |
| G1/G5 report fixtures inline in `tests/contract/test_recs_interface.py` | four scout reports at one venue | hand-copied from specs golden vector G1 | not replaced (unit-test fixture) | none; keep as regression tests |

No `data/synthetic_demo/` overrides or `tests/fixtures/synthetic/` fixture were needed so far
(updated at each merge; see `docs/workstreams/integration.md`).

### research  (`docs/synthetic/research.md`)

### Synthetic data registry: research workstream

All research synthetic data are CSV files in `research/synthetic/`. **No database
tables** (CONTRACTS v2 §E): nothing is loaded into `manhattan_bars.db` or
`live_sim.db`. Every row has `is_synthetic = 1`, every ID starts with `syn-`, and
every quote's text starts with `[SYNTHETIC] `. Generator:
`python -I research/gen_synthetic.py --seed 42` (deterministic, < 1 s, no network).
Every prior is in `PRIORS` at the top of the script, and each carries a
`# SYNTHETIC:` comment naming the real question that replaces it.
Validator: `python -I research/validate.py`. Tests: `python -I -m pytest research/tests -q`.

`research/competitors.csv` is **real** desk research, not synthetic, and is not listed here.

| File / table | What it imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `research/synthetic/syn_interviews.csv` (15 rows: 8 consumer, 3 scout, 4 operator) | Coded notes from semi-structured interviews | `gen_synthetic.make_interviews`, seed 42. Latent engagement z ~ N(0,1) (+1 for Scouts) drives nights out, bad pick, would_scout and concept reaction. Factors are drawn from the importance prior. `venue_mentions` are random launch `license_id`s. Operator WTP is drawn from `{0, 0, 25, 49, 49, 99, 150}` | `research/interviews/interviews.csv`, filled from `research/interview_guide/note_template.md` (IDs `int-r-###`, `is_synthetic=0`) | 1. Log real rows with the same columns. 2. `python -I research/validate.py --real`. 3. `python -I research/analysis.py --source real`. 4. Re-tag `research/summary.md` findings as `[REAL n=…]`. 5. Keep the synthetic CSV for demos or delete it; there's no DB to clean. |
| `research/synthetic/syn_interview_quotes.csv` (4–6 per interview; 75 rows) | Tagged, anonymized verbatim quotes | `gen_synthetic.make_quotes`: template sentences per theme × hypothesis × sentiment (`QUOTE_TEMPLATES`), filled with sampled numbers. No real venue or person named | `research/interviews/quotes.csv` (IDs `q-r-####`), transcribed from notes with no PII | Same as above. Remove the `[SYNTHETIC] ` prefix rule only for real rows (the validator checks it only for synthetic ones). |
| `research/synthetic/syn_survey_responses.csv` (300 rows) | Online survey export (Google Forms) mapped to the codebook | `gen_synthetic.make_survey`. z ~ N(0,1) drives nights out (Poisson), bad pick, would_use_weekly (logistic), would_scout (ordinal cuts) and NPS. Importance Likerts come from a Dirichlet over 8 factors. Tools are Bernoulli per tool. `submitted_at` is uniform over Oct 26 to Nov 12, 2026, ET | `research/survey/responses.csv`: the real export renamed and recoded per `research/survey/codebook.csv` (IDs `srv-r-####`, `is_synthetic=0`) | 1. Export the CSV. 2. Rename and recode columns per the codebook (see `research/survey/questions.md`, "Export → codebook mapping"). 3. `python -I research/validate.py --real`. 4. `python -I research/analysis.py --source real`. 5. Point the tableau extract at `research/survey/summary_tables.csv`. |
| `research/synthetic/summary_tables.csv` (145 rows: `metric, segment, value, n, is_synthetic`) | Aggregated findings for the voice-of-customer dashboard | `python -I research/analysis.py --source synthetic` over the three CSVs above | Same script with `--source real` → `research/survey/summary_tables.csv` | Re-run with `--source real`. Charts must drop the "demo data" title only once `is_synthetic = 0`. |

Downstream placeholders that come from this data (other workstreams should mark them `# SYNTHETIC: research survey …`):
- ml-recs default match-weight order ← `rank_importance_*` (survey Q9).
- specs freshness half-life / stale tag sanity check ← `median_freshness_tolerance_min` (Q11).
- live-sim Scout supply ← `pct_scout_ge1_report_per_night`, `pct_points_value_pref_*` (Q15–17).
- coursework label ← `would_use_weekly` (Q13).

### specs  (`docs/synthetic/specs.md`)

### Synthetic data registry — specs

Purpose: every synthetic/placeholder dataset the specs workstream created (Contracts synthetic-data rule 4).
Status: agreed.
Last updated: 2026-11-17

| File / table | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `docs/specs/golden_synthetic/G1_normal_four_scouts.json` … `G8_trend_rising_falling.json` (files: G1_normal_four_scouts.json, G2_stale_reports.json, G3_single_scout.json, G4_operator_only.json, G5_match_contract_prefs.json, G6_exclusion_known_vs_unknown.json, G7_disputed_and_flagged.json, G8_trend_rising_falling.json) | small slices of a night's scout reports, operator updates, scouts and venue attributes at real launch venues | inputs hand-written in `docs/specs/tools/build_golden.py`; `expected` computed by `reference_scoring.py`; G1 and G5 hand-checked (PRD §5.8, §5.10) | **not replaced** — test fixtures. Optionally add a vector from a real anonymised pilot night | keep; after a parameter change run `python -I docs/specs/tools/check_golden.py --regen`, review diff, commit, tell ml-recs/backend |
| `docs/specs/golden_vectors.json` | bundle of the same G1–G8 vectors + parameters + tolerances | written by `build_golden.py` | not replaced (test fixture) | regenerated with the files above. Lives outside a `synthetic` path because the build brief fixed this path; file and every row carry `is_synthetic: 1` |
| `docs/specs/golden_synthetic/personas_synthetic.json` | 5 group personas' Preferences (dancer group, cocktail pair, budget crew, group of 8, no prefs) | hand-written from PRD §3, lat/lon near Delancey/Essex | research interview results | replace values, keep ids, set `is_synthetic: 0`, update this row |
| Venue `capacity`/`genres` inside golden vectors | `syn_venue_attributes` | hand-written | `data/venue_attributes_manual.csv` | update `VENUES` in `build_golden.py`, regen |
| Parameter values in `docs/specs/PARAMETERS.md` | tuned constants | first guesses (PRD §5, §7) | tuning on live-sim training nights, then pilot data | edit table + JSON block, regen goldens, notify master |
| Targets in `docs/specs/pilot-metrics.md` §1 | pilot goals | first guesses | real pilot baseline / course feedback | edit table |

### tableau  (`docs/synthetic/tableau.md`)

### Synthetic data registry: tableau

Every synthetic file this workstream creates. All have `is_synthetic = 1` on every row, live
under `analytics/tableau/extracts/synthetic/`, and start with `syn_`. Code spots are marked
`# SYNTHETIC:` (`grep -rn "SYNTHETIC:" analytics/tableau`).

| ID | File | Imitates | How it was generated | Real replacement | Swap steps |
|---|---|---|---|---|---|
| SYN-T1 | `analytics/tableau/extracts/synthetic/syn_tonight_reports.csv` | Scout vibe checks (`syn_scout_reports` v2 columns) at the 35 launch venues, Sat Nov 14 2026 20:00-03:00 ET | `python -I analytics/tableau/export_extracts.py` (or `--placeholder`), `make_placeholder_reports`, seed 42: per venue peak hour from {22,23,0,1}, popularity ~U(0.6,1.4), Poisson reports/hour mean 4 × bell(σ 1.5 h) × popularity, crowd ~ clip(round(N(1+4·curve,0.7)),1,5), dancing 1-2 only at crowd ≥ 4 for 20% of venues, line ~ Gamma(2,4) at crowd ≥ 4 else 0, cover/genre null, 80% verified, status accepted, 60 scouts `syn-s-T1-0001…`, ids `syn-r-T1-000001…`, reputation 0.5 (new-scout default). 523 rows. Only written when no live-sim source exists; when live-sim's `data/live_sim.db` exists it holds the live-sim rows instead (header only if just the snapshot CSV exists) | 1) live-sim `data/live_sim.db` `syn_scout_reports`; 2) real `scout_reports` via backend (`INCLUDE_SYNTHETIC=0`) | Generate `python -I -m simulator --seed 42 --out data/live_sim.db` (or set `LIVE_SIM_DB`), rerun the exporter, check `tonight_source = live-sim`, Tableau Data → Refresh, republish, rerun `render_standin.py` |
| SYN-T2 | `analytics/tableau/extracts/synthetic/syn_tonight_heatmap.csv` | Hourly Live Venue State per launch venue (35 × 7 = 245 rows; cell HH = HH:30 snapshot, v2.2 §J) | Precedence: (1) live-sim `data/synthetic_live/demo_night_snapshots.csv` HH:30 rows; (2) `recs.live_state.compute_all` over live-sim reports if `recs` is importable; (3) local fallback scorer `fallback_state` = specs PRD §5.2-5.6 with v2 §A constants (passes golden vector G1: vibe 65 / conf 0.67) over SYN-T1 or live-sim reports. `display`/`vibe_band` derived per v2 §A / v2.2 §J. Column `source` = `placeholder` or `live-sim` | `GET /api/heatmap?now=2026-11-14T23:30:00-05:00&by=hour` from backend over real reports | Same as SYN-T1; for real data, fetch the API into the same columns (exporter `--tonight-source api` is a later item, see workstream doc) |

Not synthetic (public data, `is_synthetic = 0`): `bars.csv`, `venue_features_slim.csv`,
`launch_venues.csv`, `neighborhood_summary.csv`, `grade_by_neighborhood.csv`.
Evaluation-only tables `syn_true_state` / `syn_scout_truth` are never read.

## `SYNTHETIC:` code markers

| folder | count |
|---|---|
| `analytics/` | 8 |
| `backend/` | 14 |
| `docs/` | 4 |
| `research/` | 25 |
| `scripts/` | 1 |
| `tests/` | 1 |
| **total** | **53** |

_Generated from 5 registries at commit `d26a6b4`._
