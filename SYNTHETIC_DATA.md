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
| live-sim | `syn_venue_attributes` | style, genres, dance floor, cover, capacity, price, claimed, hours | `data/venue_attributes_manual.csv` (team-labelled, `is_synthetic=0`, overrides these rows in the simulation and in backend); operator profiles later |  |
| live-sim | `syn_scouts` | Scout accounts: reputation, points, level, counts, last active | backend `scouts` table (demo-login, then real auth) |  |
| live-sim | `syn_users` | app users with saved prefs (`prefs_json` = CONTRACTS Preferences) | onboarding answers |  |
| live-sim | `syn_scout_reports` | 10-second vibe checks with `status`, `distance_m` | `POST /api/reports` → `scout_reports` |  |
| live-sim | `syn_venue_updates` | operator posts: cover, DJ, genres, event, offer + expiry | `POST /api/owner/{id}/updates` → `venue_updates` |  |
| live-sim | `syn_feedback` | post-visit outcome (visited, rating) | `POST /api/feedback` → `feedback` |  |
| live-sim | `syn_bounties` | bounty board (specs §7.5) | backend bounty job on real confidence → `bounties` |  |
| live-sim | `syn_venue_events` | views / taps / saves / recommendation impressions (owner dashboard demand) | frontend/backend event logging → `venue_events` |  |
| live-sim | `syn_disputes` | owner disputes on reports and their resolution | dispute endpoint + moderator script → `disputes` |  |
| live-sim | `syn_points_ledger` | points awarded and clawed back (specs §7.2) | backend points service → `points_ledger` |  |
| live-sim | `syn_scout_reputation_history` | reputation/points/level per scout per active night (specs §5.3: join **as of report date**) | nightly snapshot job over real reputation |  |
| live-sim | `syn_true_state` | **EVALUATION ONLY**: the unobservable real crowd/dancing/line/cover/genre per 15-min slot | none; door counts / verified check-ins as proxies; drop when real |  |
| live-sim | `syn_scout_truth` | **EVALUATION ONLY**: archetype (honest/casual/sloppy/gamer/shill), accuracy, cohort, latent churn date | moderation outcomes, real last-active; drop when real |  |
| live-sim | `demo_night_snapshots.csv` (committed) | Live Venue State every 30 min, Sat Nov 14 20:00–03:00 (tableau, v2.2 §J) | same query over real reports at those times |  |
| live-sim | `extracts/hourly_by_style.csv` | hourly report volume / mean crowd by style × weekday × hour (tableau) | same query over real `scout_reports` |  |
| ml-recs | `data/live_sim.db` `syn_scout_reports`, `syn_scouts`, `syn_scout_reputation_history`, `syn_venue_updates`, `syn_venue_attributes` (live-sim, consumed) | scout vibe checks, reputation, operator posts, venue facts, 36 Thu–Sat nights | app tables `scout_reports`, `scouts`, `scout_reputation_history`, `venue_updates`; `data/venue_attributes_manual.csv` | backend passes real rows (`INCLUDE_SYNTHETIC=0`); recs code unchanged; `python -m recs eval` to retrain |
| ml-recs | `data/live_sim.db` `syn_true_state`, `syn_scout_truth` (live-sim, evaluation only) | ground truth | none in production (field audits) | read only by `crowd_model.evaluate` / `true_crowd_lookup` / `chain.ablation`; drop truth metrics from reports |
| ml-recs | `recs/synthetic/stub_nights.py` output (in memory) | the same syn_* tables, used only when no `live_sim.db` | `data/live_sim.db`, then real tables | build `live_sim.db` (`make data`) or set `LIVE_SIM_DB`; recs prefers it automatically; delete the stub when live data is permanent |
| ml-recs | `recs/artifacts/synthetic/crowd_model.joblib` + `.json` (`is_synthetic: true`) | demand model (crowd by venue × hour) | retrain on ≥ 4 weeks of real `scout_reports` | `python -m recs train-crowd` with real data; move out of `synthetic/`; set `is_synthetic: false` |
| ml-recs | `recs/reports/crowd_model.md`, `chaining.md`, `routing.md` | evaluation write-ups | re-run on real data | each starts with a "Demo data — synthetic" banner |
| ml-recs | `data/synthetic_live/demo_night_snapshots.csv` (live-sim writes; values come from `recs.chain.snapshots`) | Live State every 30 min, Sat Nov 14 20:00–03:00 | not needed with real data (backend computes live) | regenerate after any `live_state` change |
| ml-recs | `recs/tests/golden_recs_derived/G1–G8.json` | worked examples | stays synthetic (tests) | none |
| ml-recs | `recs/tests/specs_copy/` (copy of specs' `golden_synthetic/`, `PARAMETERS.md`, `tools/reference_scoring.py`) | specs' golden vectors + oracle | stays synthetic (tests) | re-copy when specs changes; tests use `docs/specs/` when present |
| ml-recs | `recs/tests/fixtures/synthetic/*.csv` (`syn-v-*`, `syn-s-*`, `syn-r-*`, `syn-u-*`) | a tiny night: 5 venues, 3 scouts, 40 reports, 4 updates | stays synthetic (tests) | none |
| ml-recs | `recs/examples/prefs_*.json` | a group's preferences | real user prefs from the request | none |
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

### live-sim  (`docs/synthetic/live-sim.md`)

### Synthetic data registry: live-sim

**Every row listed here is synthetic (`is_synthetic = 1`).** None of it describes what really happens at
these bars. The venues are real (SLA licences, public data), but their attributes, crowds, Scouts, users and
outcomes are invented. Show the "demo data" badge wherever any of it appears.

Built by `python -m simulator --seed 42 --out data/live_sim.db`, run from the repo root (CONTRACTS f5c95d2). Seed 42 gives byte-identical CSVs (sha256 in
`data/synthetic_live/manifest.json`). CSVs go to `data/synthetic_live/` (gitignored except the snapshots file);
the same tables are loaded into `data/live_sim.db` (never committed).

#### General swap path (all app tables)
1. Real rows go into the same table without the `syn_` prefix (`scout_reports`, `venue_updates`, ...), which
   backend creates empty from day one (CONTRACTS v2 §E, v2.2 §J).
2. Backend reads `syn_X UNION ALL X`; set `INCLUDE_SYNTHETIC=0` to hide synthetic rows.
3. Once real data is enough, stop running the build command and drop `data/live_sim.db`.

#### Tables

Rows are for seed 42, full 36-night run (Thu 2026-08-27 → Sat 2026-11-14, 20:00–03:00 ET).

| File / table | Rows | Imitates | How generated (module, config keys) | Real source that replaces it |
|---|---|---|---|---|
| `syn_venue_attributes` | 35 | style, genres, dance floor, cover, capacity, price, claimed, hours | `venues.py`; `venues.*` (style rules from name/OSM amenity + priors). `opening_hours` is **real** OSM text when present | `data/venue_attributes_manual.csv` (team-labelled, `is_synthetic=0`, overrides these rows in the simulation and in backend); operator profiles later |
| `syn_scouts` | 209 | Scout accounts: reputation, points, level, counts, last active | `scouts.py` (population) + `trust.py` (final stats); `scouts.*`, `specs.*` | backend `scouts` table (demo-login, then real auth) |
| `syn_users` | 300 | app users with saved prefs (`prefs_json` = CONTRACTS Preferences) | `users.py`; `users.personas`, `users.home_mix` | onboarding answers |
| `syn_scout_reports` | 8,147 | 10-second vibe checks with `status`, `distance_m` | `nightloop.py` (observations of true state with archetype noise, rate limits, presence) + `trust.py` (status); `scouts.obs`, `scouts.*_null_p`, `specs.*` | `POST /api/reports` → `scout_reports` |
| `syn_venue_updates` | 662 | operator posts: cover, DJ, genres, event, offer + expiry | `updates.py`; `updates.*` | `POST /api/owner/{id}/updates` → `venue_updates` |
| `syn_feedback` | 1,440 | post-visit outcome (visited, rating) | `feedback.py` placeholder chooser over **true** state; `feedback.*` | `POST /api/feedback` → `feedback` |
| `syn_bounties` | 2,409 | bounty board (specs §7.5) | `nightloop.py` (created every 15 min 21:00–02:00 when confidence < 0.30, max 8 open, 60-min expiry, claimed by first verified report) | backend bounty job on real confidence → `bounties` |
| `syn_venue_events` | 65,973 | views / taps / saves / recommendation impressions (owner dashboard demand) | `events.py` fallback: Poisson per venue-slot × busyness, then tap/save funnel; `events.*` | frontend/backend event logging → `venue_events` |
| `syn_disputes` | 250 | owner disputes on reports and their resolution | `trust.py`; `disputes.*` (3% base, ×3 on low-crowd reports, 30% upheld, 48 h auto-reject) | dispute endpoint + moderator script → `disputes` |
| `syn_points_ledger` | 17,702 | points awarded and clawed back (specs §7.2) | `trust.py`; `specs.points_*` | backend points service → `points_ledger` |
| `syn_scout_reputation_history` | 1,644 | reputation/points/level per scout per active night (specs §5.3: join **as of report date**) | `trust.py` time-ordered pass; `specs.rep_*` | nightly snapshot job over real reputation |
| `syn_true_state` | 35,420 | **EVALUATION ONLY**: the unobservable real crowd/dancing/line/cover/genre per 15-min slot | `truth.py`; `truth.*` | none; door counts / verified check-ins as proxies; drop when real |
| `syn_scout_truth` | 209 | **EVALUATION ONLY**: archetype (honest/casual/sloppy/gamer/shill), accuracy, cohort, latent churn date | `scouts.py` + `nightloop.py` (engagement process) | moderation outcomes, real last-active; drop when real |
| `demo_night_snapshots.csv` (committed) | 525 | Live Venue State every 30 min, Sat Nov 14 20:00–03:00 (tableau, v2.2 §J) | `snapshots.py` via `replay.visible` + `recs.live_state` if importable, else `_live_state.py` (specs §5 mirror). `manifest.json` → `snapshot_source` | same query over real reports at those times |
| `extracts/hourly_by_style.csv` | ~120 | hourly report volume / mean crowd by style × weekday × hour (tableau) | `extracts.py` over accepted/disputed reports | same query over real `scout_reports` |

The app and API must never read `syn_true_state` or `syn_scout_truth`; `replay.visible` never returns them.

#### Key placeholder numbers (all in `simulator/config/default.json`)
Style peaks dive 00:00, cocktail 22:00, club 01:00, lounge 23:00, pub 22:00, restaurant-bar 21:00; weekday
0.70/0.95/1.00; night/venue-night shocks σ 0.15/0.20; Labor Day Sat ×1.15, Halloween ×1.3; crowd bins
0.2/0.45/0.7/0.9 of capacity; line above 85% occupancy; archetype shares 55/25/10/6/4%; engagement
Beta(2.5, 3.5), weekly decay 0.85, churn below 0.25, 5% returns after ≥ 3 weeks; cover null ~60%, genre null
~40%; 300 users; funnel tap 25% / save 10%. Specs constants (`specs.*`) are copied from specs PRD §5–7 and
CONTRACTS v2 §A, not invented here.

#### Manual override
If `data/venue_attributes_manual.csv` exists (same columns as `syn_venue_attributes`, `is_synthetic=0`), its
non-empty values replace the generated attributes before the true state is simulated, so synthetic reports
agree with hand-labelled facts. The simulator never writes that file.

### ml-recs  (`docs/synthetic/ml-recs.md`)

### Synthetic data registry: ml-recs

Every synthetic dataset or artifact that `recs/` creates or consumes. Code spots carry `# SYNTHETIC:` comments.

| File / table | Imitates | How generated | Real replacement | Swap steps |
|---|---|---|---|---|
| `data/live_sim.db` `syn_scout_reports`, `syn_scouts`, `syn_scout_reputation_history`, `syn_venue_updates`, `syn_venue_attributes` (live-sim, consumed) | scout vibe checks, reputation, operator posts, venue facts, 36 Thu–Sat nights | live-sim, `python -m simulator --seed 42` | app tables `scout_reports`, `scouts`, `scout_reputation_history`, `venue_updates`; `data/venue_attributes_manual.csv` | backend passes real rows (`INCLUDE_SYNTHETIC=0`); recs code unchanged; `python -m recs eval` to retrain |
| `data/live_sim.db` `syn_true_state`, `syn_scout_truth` (live-sim, evaluation only) | ground truth | live-sim | none in production (field audits) | read only by `crowd_model.evaluate` / `true_crowd_lookup` / `chain.ablation`; drop truth metrics from reports |
| `recs/synthetic/stub_nights.py` output (in memory) | the same syn_* tables, used only when no `live_sim.db` | Poisson report arrivals ∝ true crowd; style-specific hour curves; scout archetypes (honest/casual/sloppy/gamer/shill); nightly reputation update; seed 42 | `data/live_sim.db`, then real tables | build `live_sim.db` (`make data`) or set `LIVE_SIM_DB`; recs prefers it automatically; delete the stub when live data is permanent |
| `recs/artifacts/synthetic/crowd_model.joblib` + `.json` (`is_synthetic: true`) | demand model (crowd by venue × hour) | `python -m recs train-crowd` on live-sim data (origin/nightlife/live-sim beaa382) | retrain on ≥ 4 weeks of real `scout_reports` | `python -m recs train-crowd` with real data; move out of `synthetic/`; set `is_synthetic: false` |
| `recs/reports/crowd_model.md`, `chaining.md`, `routing.md` | evaluation write-ups | `python -m recs eval` | re-run on real data | each starts with a "Demo data — synthetic" banner |
| `data/synthetic_live/demo_night_snapshots.csv` (live-sim writes; values come from `recs.chain.snapshots`) | Live State every 30 min, Sat Nov 14 20:00–03:00 | `python -m recs snapshots --out …` | not needed with real data (backend computes live) | regenerate after any `live_state` change |
| `recs/tests/golden_recs_derived/G1–G8.json` | worked examples | hand-derived by ml-recs from specs PRD §5 before specs pushed theirs | stays synthetic (tests) | none |
| `recs/tests/specs_copy/` (copy of specs' `golden_synthetic/`, `PARAMETERS.md`, `tools/reference_scoring.py`) | specs' golden vectors + oracle | specs | stays synthetic (tests) | re-copy when specs changes; tests use `docs/specs/` when present |
| `recs/tests/fixtures/synthetic/*.csv` (`syn-v-*`, `syn-s-*`, `syn-r-*`, `syn-u-*`) | a tiny night: 5 venues, 3 scouts, 40 reports, 4 updates | one-off seeded script (seed 42) | stays synthetic (tests) | none |
| `recs/examples/prefs_*.json` | a group's preferences | hand-written | real user prefs from the request | none |

Not synthetic: `recs/artifacts/clusters.*` and `recs/artifacts/complaint_risk.*` are trained on real public data
(`data/manhattan_bars.db`), `is_synthetic: false`.

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
| `recs/` | 9 |
| `research/` | 25 |
| `scripts/` | 1 |
| `simulator/` | 12 |
| `tests/` | 1 |
| **total** | **74** |

_Generated from 7 registries at commit `3533a79`._
