# PRD — integration (Nightlife Autopilot, Mockups V1 / Nov 17)

Workstream: `integration` · Branch: `nightlife/integration` (from `nightlife/contracts`) · Owner: Ryan Mehta
Status: planning (no code yet) · Written 2026-11-11, **rev 2 for Contracts v2 (commit 2129052)** · Upstream deadline **Fri 2026-11-13 18:00 ET** · Hard deadline: **Tue 2026-11-17, class demo**

> Rev 2: CR-1…CR-7 accepted in CONTRACTS.md v2 (§C, §D, §G, §H). Synthetic tables now live in a separate uncommitted `data/live_sim.db` (seed 42); deploys use `data/launch_venues_full.csv` (integration-owned) instead of the 39 MB DB; `DEMO_NOW = 2026-11-14T23:30:00-05:00` confirmed.

## 1. Problem

Eight workstreams (specs, research, tableau, live-sim, ml-recs, backend, frontend,
coursework) build on separate `nightlife/*` branches against `docs/CONTRACTS.md`.
Each one can be green on its own and still fail when combined: mismatched column
names, a backend that can't import `recs/`, a frontend that only ever ran against its
mock API, synthetic data that isn't loaded where the API reads it, or a deploy nobody
has tried. The Nov 17 deliverable is a **working model, deployed**: one URL a
classmate can open, pick preferences, and see ranked LES venues with vibe / match /
confidence scores driven by (synthetic) live reports. Integration turns the eight
branches into that one URL plus the docs that let anyone see what is fake and how to
swap it for real data.

## 2. Goals

1. **G1 One integrated branch.** Every `nightlife/*` branch merged into
   `nightlife/integration` with conflicts resolved, the contract checked, and the
   existing pipeline (`src/`, `data/manhattan_bars.db`, `run_all.sh`) still working.
2. **G2 Wired end to end.** live-sim CSVs → loaded into `syn_*` tables → backend
   calls `recs.live_state` / `recs.scoring` / `recs.routing` → frontend calls the real
   API (mock mode off) for every MVP screen.
3. **G3 Tested end to end.** A contract test suite (API shapes vs CONTRACTS.md) and a
   browser smoke test (Playwright) that run in one command and in CI.
4. **G4 Seeded demo night.** The fixed, reproducible simulated history (Thu–Sat,
   Sep 3 → Nov 14, seed 42, v2 §B); the demo replays `DEMO_NOW = 2026-11-14T23:30:00-05:00`.
5. **G5 Deployed.** Backend on Render, frontend on Vercel, both reachable from a
   phone, health check green, cold-start understood.
6. **G6 Honest about synthetic data.** Root `SYNTHETIC_DATA.md` that consolidates
   every `docs/synthetic/*.md` with swap-to-real steps per dataset; "demo data" badge
   visible wherever synthetic data is shown.
7. **G7 Presentable.** Updated root `README.md` and a timed (≤ 5 min placeholder)
   class demo script with a fallback path.

## 3. Non-goals

- New product features or new scoring logic (owned by ml-recs / specs).
- Real live data, real users, real auth/payments, or venue claiming verification.
- Changing `docs/CONTRACTS.md` directly (changes go to §12 "Contract change requests").
- Opening PRs or pushing to `main` (Ryan decides when/if `nightlife/integration` → `main`).
- Production hardening (rate limiting, monitoring, Postgres migration) beyond what
  the demo needs — listed as "later".
- Tableau dashboard itself and coursework exercises (only checked that they merge
  cleanly and are linked from the README).

## 4. Users of this workstream

| User | Needs from integration |
|---|---|
| Ryan (owner / presenter) | one URL, one demo script, confidence it won't break live in class |
| Instructor / classmates | open the URL on a phone, understand what's real vs synthetic |
| Other workstreams | a clear "deliver this first" checklist and a single place where their parts meet |
| Future build sessions | `SYNTHETIC_DATA.md` swap steps; reproducible `make demo` |
| End-user personas (via the demo) | group/consumer, Scout, venue operator — exercised in the demo script |

## 5. User stories and acceptance criteria

**US-1 Merge** — As Ryan, I want all workstream branches merged into one branch so the
app runs from a single checkout.
- AC: `git log nightlife/integration` contains a merge commit for each of the 8 branches
  (or a recorded reason a branch was skipped/partially taken in `docs/workstreams/integration.md`).
- AC: no file outside a workstream's owned folder was changed by that workstream
  without being listed in the merge log (ownership audit script output attached).
- AC: `SKIP_SCRAPE=1 ./run_all.sh` still completes (or a documented equivalent smoke
  subset: `python -I src/build_db.py` + `src/simulate.py --n 100`).

**US-2 Contract check** — As integration, I want an automated check that every
synthetic table and API response matches CONTRACTS.md.
- AC: `pytest tests/contract` validates column sets of every app `syn_*` table in
  `data/live_sim.db` (the 7 v1 tables with v2 §E additions, plus `syn_venue_events`,
  `syn_disputes`, `syn_points_ledger`), the Live Venue State (v2 §F optional keys),
  Recommendation result (incl. `rank_score`, `rank`, `excluded_reason`, `complaint_risk`)
  and every `/api/*` route (status, required keys, types, `is_synthetic` on every object,
  `X-Data` header on lists, v2 §G error shape). Backend's `/openapi.json` is diffed
  against `tests/contract/schemas.py`.
- AC: every `syn_*` row has `is_synthetic = 1` and a `syn-` primary key; every
  `venue_id` is one of the 35 in `data/launch_venues.csv` (`license_id AS venue_id`).
- AC: evaluation-only tables (`syn_true_state`, `syn_scout_truth`) are never read by
  `backend/` or `recs/` runtime code (grep test + an API test with those tables dropped).
- AC: golden vectors G1 (vibe 65 / conf 0.67) and G5 (match 83) pass through the
  deployed API path, not only in unit tests.
- AC: with `INCLUDE_SYNTHETIC=0` the API returns empty live state / `"data": "real"`
  without errors (the swap-to-real switch works).

**US-3 Group gets a pick** — As a group of 4 on Ludlow St at 23:30, I want to enter
preferences and get ranked venues with reasons.
- AC: on the deployed frontend, onboarding → "Tonight" shows ≥ 5 (placeholder)
  non-excluded venues for the default prefs in CONTRACTS.md, each with match, vibe,
  confidence, distance, ≥ 1 reason, and a "missing" list where applicable.
- AC: the same request to `POST /api/recommend?now=<demo time>` returns identical
  ordering on two runs (determinism).
- AC: p95 latency of `/api/recommend` < 1.5 s warm on Render free tier (placeholder).

**US-4 Scout reports and sees the effect** — As a Scout, I want to submit a 10-second
vibe check and see the venue update.
- AC: after `POST /api/auth/demo-login` (role scout), submitting a report in the UI →
  `POST /api/reports` returns `{report_id, ts, status, points_pending}`; `GET /api/venues/{id}/state` afterwards shows `n_reports` +1 and
  `freshness_minutes` ≈ 0.
- AC: leaderboard and bounties screens render real API data with the demo badge.

**US-5 Operator posts an update** — As a venue operator, I want to post tonight's
cover/DJ/offer and see demand analytics.
- AC: demo-login as owner → `POST /api/owner/{id}/updates` then the venue profile shows
  the new cover/offer; an owner reporting their own venue is rejected;
  owner dashboard renders views/taps/reports/demand labelled "demo data".

**US-6 Run My Night & heatmap** (later-tier, included if delivered) —
- AC: `/api/plan-night` with `n_stops=3` returns 3 ordered distinct venues within
  `max_distance_km`; map screen renders `/api/heatmap` points for all 35 venues.
- AC: if ml-recs routing isn't ready, the screen is hidden behind a feature flag, not broken.

**US-7 Replay the demo night** — As the presenter, I want the app pinned to a demo time.
- AC: frontend env `VITE_DEMO_NOW` (or a URL param `?now=`) is passed to all read
  endpoints; a visible clock chip shows the simulated time.
- AC: `make seed-demo` regenerates `data/live_sim.db` with seed 42; a per-table row
  count + content hash (ordered `SELECT *`) matches the values recorded in
  `docs/workstreams/integration.md` on two machines (or two runs).

**US-8 See what's fake** — As a classmate/instructor, I want to know what's synthetic.
- AC: `SYNTHETIC_DATA.md` lists every dataset from every `docs/synthetic/*.md` with:
  file/table, imitates, generated by, real replacement, swap steps, owner.
- AC: `grep -rn "SYNTHETIC:"` count is recorded and every hit maps to a row in it.
- AC: every screen that shows `is_synthetic` data shows the badge (checked in Playwright).

**US-9 Deployed** — As anyone, I want to open one link.
- AC: `https://<frontend>.vercel.app` (placeholder) loads on mobile Safari/Chrome;
  `https://<backend>.onrender.com/api/health` returns `{"ok": true}`.
- AC: CORS (`CORS_ORIGINS`) allows only the Vercel origin(s) + localhost.
- AC: the Render image contains `data/launch_venues_full.csv` and a freshly generated
  `data/live_sim.db`, not the 39 MB `manhattan_bars.db`.
- AC: a warm-up step (curl health 2 min before class) is in the demo script.

**US-10 Docs** — As a reader of the repo, I want an accurate README.
- AC: README has: one-paragraph product summary, live URLs, architecture diagram link
  (from specs), local quickstart (≤ 5 commands), per-folder table, synthetic-data
  warning linking `SYNTHETIC_DATA.md`, and the original pipeline sections preserved.

## 6. Scope

**MVP (must ship Nov 17)**: merged branch; `syn_*` loaded; backend endpoints
health/venues/venue/state/reports/recommend/leaderboard/bounties/owner dashboard/
owner updates; frontend screens onboarding, Tonight, venue cards + filters + search,
venue profile, vibe check, leaderboard + bounties, owner dashboard; demo badge; demo
night seeded; contract + smoke tests; Render + Vercel deploy; SYNTHETIC_DATA.md;
README; demo script; workstream checklist.

**Later (ship if green by Nov 16 18:00, else feature-flagged off)**: heatmap/map
screen, Run My Night, crowd model predictions surfaced in UI, clustering "similar
venues", complaint-risk display, Tableau embed/link, CI deploy previews, Postgres.

## 7. Requirements

Functional
- R1 Merge order and conflict policy as in OUTLINE §2; ownership from CONTRACTS.md wins.
- R2 Data build: `scripts/build_launch_venues_full.py` (integration, v2 §D) writes
  committed `data/launch_venues_full.csv` (35 launch venues + OSM name, opening hours,
  website flag, neighborhood) from `manhattan_bars.db`; live-sim's generator writes
  uncommitted `data/live_sim.db` (seed 42). Integration reuses the generator, it does
  not write its own.
- R3 In deploy the backend reads `launch_venues_full.csv` + `live_sim.db` (`LIVE_SIM_DB`)
  only; the Docker build runs the generator. `manhattan_bars.db` stays local/pipeline-only.
- R4 All read endpoints accept `now=`; the frontend forwards a single demo time.
- R5 Feature flags `FEATURE_ROUTING`, `FEATURE_HEATMAP` (backend env) and
  `VITE_FEATURE_*` (frontend) default off until their e2e checks pass.
- R6 `recs/` import falls back to backend's stub only if `recs` import fails; the
  fallback logs a warning and `/api/health` reports v2 §G keys (`recs`, `data`, `demo_now`).
- R7 Swap path: real tables mirror `syn_` twins without the prefix; `INCLUDE_SYNTHETIC`
  toggles synthetic rows (v2 §E). `SYNTHETIC_DATA.md` documents this as step 1 of every swap.
- R8 Root files from specs: copy `docs/specs/team/` PR template → `.github/pull_request_template.md`
  and CONTRIBUTING → root `CONTRIBUTING.md`; move `backend/render.yaml` to root if Render needs it (v2 §C).

Non-functional
- N1 Reproducible: fixed seeds; `make demo` from clean checkout < 5 min (placeholder).
- N2 Deterministic outputs for a given `now`.
- N3 Mobile-first: demo screens usable at 390×844.
- N4 Cold start: Render free tier sleeps; warm-up documented; target first response < 60 s.
- N5 No secrets in repo; deploy env vars listed in README / RULES.

## 8. Dependencies on other workstreams

| Workstream | Integration needs (must arrive by) |
|---|---|
| **specs** | `docs/specs/SCORING.md` matching v2 §A constants + golden vectors G1/G5; architecture diagram; `docs/specs/team/` PR template + CONTRIBUTING — **Nov 13 18:00** |
| **research** | nothing blocking; one-line positioning + interview status for README/demo; `syn_interviews`/`syn_interview_quotes`/`syn_survey_responses` registered — Nov 13 18:00 (soft) |
| **tableau** | extracts (synthetic ones under `analytics/tableau/extracts/synthetic/`) + PNG; link for README/demo slide — Nov 13 18:00 (soft) |
| **live-sim** | deterministic generator (seed 42) → `data/live_sim.db` with all v2 §E tables, Sep 3 → Nov 14 nights, `simulator/genres.py`, `docs/synthetic/live-sim.md` — **Nov 13 18:00** |
| **ml-recs** | `recs/` importable with the 4 contract functions + v2 §F keys, accepts lists of dicts or DataFrames, G1/G5 tests green; routing optional — **Nov 13 18:00** |
| **backend** | all MVP endpoints incl. v2 §G (demo-login, error shape, `X-Data`, `/openapi.json`), attaches `live_sim.db`, `INCLUDE_SYNTHETIC`, Dockerfile + `backend/render.yaml`, pytest — **Nov 13 18:00** |
| **frontend** | mockup PNGs (target Nov 12); MVP screens against the contract API, `VITE_API_MODE=mock|live`, `VITE_DEMO_NOW`/`?now=`, demo badge, `VITE_API_BASE`, vercel config — **Nov 13 18:00** |
| **coursework** | stays inside `coursework/`, doesn't change root requirements — Nov 13 18:00 (soft) |
| **integration** | (this) merges from Nov 13, deploy dry-run Nov 15, freeze Nov 16 20:00 |

Accounts: Render and Vercel accounts + GitHub app connection must be supplied by Ryan
(blocking for G5) — **Nov 13**.

## 9. Success metrics (for Nov 17)

| Metric | Target (placeholder) |
|---|---|
| Branches merged | 8/8 (≥ 6/8 with documented reasons minimum) |
| Contract tests passing | 100% of MVP routes and every v2 §E app table; G1/G5 golden vectors |
| Playwright smoke | 100% green on deployed URL, 3 consecutive runs |
| Demo script rehearsal | ≥ 2 full run-throughs, each ≤ 5 min, zero hard failures |
| `/api/recommend` p95 warm | < 1.5 s |
| Synthetic datasets documented in SYNTHETIC_DATA.md | 100% of `docs/synthetic/*.md` entries |
| Screens with synthetic data lacking badge | 0 |
| Deploy uptime during class window | 100% (warm-up done) |

## 10. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Upstream branches late (esp. backend/frontend) | High | deadline Fri Nov 13 18:00 ET gives a day of slack; merge whatever is pushed; backend stub + frontend mock mode as fallbacks; feature flags |
| Schema drift vs CONTRACTS.md | Med | contract tests run first after each merge; adapters only in integration-owned shim with a CR filed |
| Binary `.db` conflicts | Low (v2 §D: `live_sim.db` uncommitted) | `manhattan_bars.db` always taken from `nightlife/contracts`; any committed `live_sim.db` is removed and gitignored |
| Generator non-determinism across machines (pandas/numpy versions) | Med | pin versions in the Docker image; compare row counts + content hashes, not file bytes |
| Evaluation-only truth tables leak into app/features | Low/high impact | grep + drop-table contract test |
| `requirements.txt` / root file conflicts | High | union + pin; one root `requirements.txt` plus per-package `backend/requirements.txt`, `recs/pyproject.toml` |
| Render free tier cold start / sleep mid-demo | High | warm-up curl; keep-alive ping during class; local fallback (`make demo` on laptop) + recorded video |
| Render image too big / build slow (pandas, sklearn) | Med | slim app DB; only install backend + recs deps |
| CORS / env misconfig on Vercel | Med | dry-run deploy Nov 15; documented env table |
| Timezone bugs in `now=` (ET vs UTC) | Med | all ts ISO 8601 with offset; tests at 23:59→00:01 rollover and DST-free demo date |
| Synthetic data mistaken for real in class | Low/high impact | badge + SYNTHETIC_DATA.md + demo script line |
| Complaint risk shown as "quality" | Low | label check in Playwright ("complaint risk") |

## 11. Open questions

- Q1 Does `nightlife/integration` get merged to `main` after Nov 17, and who does it? (assumed: Ryan, manually)
- ~~Q2 demo time~~ — resolved: `DEMO_NOW = 2026-11-14T23:30:00-05:00` (v2 §B).
- ~~Q3 39 MB DB on Render~~ — resolved: `launch_venues_full.csv` + generated `live_sim.db` (v2 §D).
- Q3b Generate `live_sim.db` at Docker build time or at container start? (assumed build time; start-time fallback if build exceeds Render limits)
- Q4 Render/Vercel account owner, project names, custom domain? (assumed default subdomains)
- ~~Q5 auth~~ — resolved: `POST /api/auth/demo-login` (v2 §G); demo script uses pre-chosen personas.
- Q6 Are POSTs during the demo persisted (Render disk is ephemeral)? (assumed reset on redeploy; acceptable)
- Q7 Do Run My Night and heatmap count toward "working model"? (assumed nice-to-have)
- Q8 Is CI (GitHub Actions) wanted, or local `make test` enough for the course?

## 12. Contract change requests

Recorded here per the brief. CONTRACTS.md is not edited.
**Status (Contracts v2, commit 2129052): CR-1 … CR-7 all accepted** — CR-1 → v2 §C,
CR-2/CR-6 → §G, CR-3 → §D, CR-4 → §B, CR-5 → §H, CR-7 → §C. No open CRs.
Original text kept below for history.

- **CR-1 Integration-owned paths.** CONTRACTS.md's folder table has no row for
  integration. Proposed rows: `tests/e2e/`, `tests/contract/`, `scripts/` (integration
  scripts only), root `SYNTHETIC_DATA.md`, root `README.md` (integration edits; others
  propose), `Makefile`, `.github/workflows/`, `docs/prd/integration/`,
  `docs/workstreams/integration.md`, `docs/synthetic/integration.md`, `DEMO.md`.
- **CR-2 Health detail.** `/api/health` → `{"ok": true, "recs": "real"|"stub", "data": "synthetic", "demo_now": "<ISO>|null"}` (extra keys only; `ok` unchanged).
- **CR-3 `venue_id` vs `license_id`.** `data/launch_venues.csv` header uses
  `license_id`; contract says `venue_id` everywhere. Proposal: keep the CSV as is,
  loaders alias `license_id AS venue_id`; state this explicitly in CONTRACTS.md.
- **CR-4 Demo-time propagation.** Add a frontend convention: env `VITE_DEMO_NOW` and URL
  param `?now=` forwarded as the API `now=` on every read endpoint.
- **CR-5 Feature flags.** Reserve env names `FEATURE_ROUTING`, `FEATURE_HEATMAP`,
  `VITE_FEATURE_ROUTING`, `VITE_FEATURE_HEATMAP`, `VITE_API_MODE`, `VITE_API_BASE`, `CORS_ORIGINS`.
- **CR-6 Response `is_synthetic`.** Venue cards and dashboard responses should carry a
  top-level `is_synthetic` so the frontend can decide the badge without guessing.
- **CR-7 Workstream doc location.** Briefs put plans in `docs/prd/<name>/`; CONTRACTS
  names `docs/workstreams/<name>.md` for build notes. Confirm both are kept (plan vs as-built).
