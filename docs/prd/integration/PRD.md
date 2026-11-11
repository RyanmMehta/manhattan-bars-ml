# PRD — integration (Nightlife Autopilot, Mockups V1 / Nov 17)

Workstream: `integration` · Branch: `nightlife/integration` (from `nightlife/contracts`) · Owner: Ryan Mehta
Status: planning (no code yet) · Written 2026-11-11 · Hard deadline: **Tue 2026-11-17, class demo**

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
4. **G4 Seeded demo night.** A fixed, reproducible simulated night (default:
   Saturday 2026-11-14, 21:00–02:00 ET, placeholder) the demo replays with `now=`.
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
- AC: `pytest tests/contract` validates column sets of all 7 `syn_*` tables, the
  Live Venue State, Recommendation result and every `/api/*` route in the table
  (status 200, required keys, types, `null` allowed only where the contract says).
- AC: every `syn_*` row has `is_synthetic = 1`; every `venue_id` in synthetic data is
  one of the 35 in `data/launch_venues.csv`.

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
- AC: submitting a report in the UI → `POST /api/reports` returns 201 with server-set
  `report_id`/`ts`; `GET /api/venues/{id}/state` afterwards shows `n_reports` +1 and
  `freshness_minutes` ≈ 0.
- AC: leaderboard and bounties screens render real API data with the demo badge.

**US-5 Operator posts an update** — As a venue operator, I want to post tonight's
cover/DJ/offer and see demand analytics.
- AC: `POST /api/owner/{id}/updates` then the venue profile shows the new cover/offer;
  owner dashboard renders views/taps/reports/demand labelled "demo data".

**US-6 Run My Night & heatmap** (later-tier, included if delivered) —
- AC: `/api/plan-night` with `n_stops=3` returns 3 ordered distinct venues within
  `max_distance_km`; map screen renders `/api/heatmap` points for all 35 venues.
- AC: if ml-recs routing isn't ready, the screen is hidden behind a feature flag, not broken.

**US-7 Replay the demo night** — As the presenter, I want the app pinned to a demo time.
- AC: frontend env `VITE_DEMO_NOW` (or a URL param `?now=`) is passed to all read
  endpoints; a visible clock chip shows the simulated time.
- AC: `make seed-demo` rebuilds the demo DB from seeds with byte-identical `syn_*`
  CSV hashes (recorded in `docs/workstreams/integration.md`).

**US-8 See what's fake** — As a classmate/instructor, I want to know what's synthetic.
- AC: `SYNTHETIC_DATA.md` lists every dataset from every `docs/synthetic/*.md` with:
  file/table, imitates, generated by, real replacement, swap steps, owner.
- AC: `grep -rn "SYNTHETIC:"` count is recorded and every hit maps to a row in it.
- AC: every screen that shows `is_synthetic` data shows the badge (checked in Playwright).

**US-9 Deployed** — As anyone, I want to open one link.
- AC: `https://<frontend>.vercel.app` (placeholder) loads on mobile Safari/Chrome;
  `https://<backend>.onrender.com/api/health` returns `{"ok": true}`.
- AC: CORS allows only the Vercel origin(s) + localhost.
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
- R2 Single data build step `scripts/build_app_db.py` (or backend's equivalent, if it
  already exists — reuse, don't duplicate) producing `data/app.db` from
  `data/manhattan_bars.db` launch venues + `data/synthetic_live/*.csv`.
- R3 Backend reads only `data/app.db` in deploy (the 39 MB pipeline DB is not shipped
  to Render unless backend already does so and it fits; see Q3).
- R4 All read endpoints accept `now=`; the frontend forwards a single demo time.
- R5 Feature flags `FEATURE_ROUTING`, `FEATURE_HEATMAP` (backend env) and
  `VITE_FEATURE_*` (frontend) default off until their e2e checks pass.
- R6 `recs/` import falls back to backend's stub only if `recs` import fails; the
  fallback logs a warning and `/api/health` reports `{"ok": true, "recs": "stub"|"real"}`
  (see CR-2).

Non-functional
- N1 Reproducible: fixed seeds; `make demo` from clean checkout < 5 min (placeholder).
- N2 Deterministic outputs for a given `now`.
- N3 Mobile-first: demo screens usable at 390×844.
- N4 Cold start: Render free tier sleeps; warm-up documented; target first response < 60 s.
- N5 No secrets in repo; deploy env vars listed in README / RULES.

## 8. Dependencies on other workstreams

| Workstream | Integration needs (must arrive by) |
|---|---|
| **specs** | final scoring constants (half-life, display threshold, match weights) in `docs/specs/`; architecture diagram for README — **Nov 13** |
| **research** | nothing blocking; one-line positioning + interview status for README/demo — Nov 15 |
| **tableau** | extracts + PNG in `analytics/tableau/`; link for README/demo slide — Nov 15 |
| **live-sim** | `data/synthetic_live/*.csv` for all 7 `syn_*` tables covering the demo night, CLI with seed, `docs/synthetic/live-sim.md` — **Nov 13** |
| **ml-recs** | `recs/` importable with the 4 contract functions, pinned deps, unit tests passing; routing optional — **Nov 14** |
| **backend** | all MVP endpoints, loader for syn_ tables, Dockerfile + render.yaml, pytest suite, CORS env var — **Nov 14** |
| **frontend** | MVP screens against the contract API, mock mode toggle (`VITE_API_MODE=mock|live`), demo badge component, `VITE_API_BASE`, vercel config — **Nov 14** |
| **coursework** | stays inside `coursework/`, doesn't change root requirements — Nov 16 |
| **integration** | (this) merges from Nov 13, deploy dry-run Nov 15, freeze Nov 16 20:00 |

Accounts: Render and Vercel accounts + GitHub app connection must be supplied by Ryan
(blocking for G5) — **Nov 14**.

## 9. Success metrics (for Nov 17)

| Metric | Target (placeholder) |
|---|---|
| Branches merged | 8/8 (≥ 6/8 with documented reasons minimum) |
| Contract tests passing | 100% of MVP routes and 7/7 syn tables |
| Playwright smoke | 100% green on deployed URL, 3 consecutive runs |
| Demo script rehearsal | ≥ 2 full run-throughs, each ≤ 5 min, zero hard failures |
| `/api/recommend` p95 warm | < 1.5 s |
| Synthetic datasets documented in SYNTHETIC_DATA.md | 100% of `docs/synthetic/*.md` entries |
| Screens with synthetic data lacking badge | 0 |
| Deploy uptime during class window | 100% (warm-up done) |

## 10. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Upstream branches late (esp. backend/frontend) | High | merge whatever is pushed daily from Nov 13; backend stub + frontend mock mode as fallbacks; feature flags |
| Schema drift vs CONTRACTS.md | Med | contract tests run first after each merge; adapters only in integration-owned shim with a CR filed |
| Binary `data/manhattan_bars.db` conflicts (two branches rewrite it) | Med | DB is regenerated, never hand-merged; syn_ tables live in CSV + `data/app.db` (gitignored or rebuilt) |
| `requirements.txt` / root file conflicts | High | union + pin; one root `requirements.txt` plus per-package `backend/requirements.txt`, `recs/pyproject.toml` |
| Render free tier cold start / sleep mid-demo | High | warm-up curl; keep-alive ping during class; local fallback (`make demo` on laptop) + recorded video |
| Render image too big / build slow (pandas, sklearn) | Med | slim app DB; only install backend + recs deps |
| CORS / env misconfig on Vercel | Med | dry-run deploy Nov 15; documented env table |
| Timezone bugs in `now=` (ET vs UTC) | Med | all ts ISO 8601 with offset; tests at 23:59→00:01 rollover and DST-free demo date |
| Synthetic data mistaken for real in class | Low/high impact | badge + SYNTHETIC_DATA.md + demo script line |
| Complaint risk shown as "quality" | Low | label check in Playwright ("complaint risk") |

## 11. Open questions

- Q1 Does `nightlife/integration` get merged to `main` after Nov 17, and who does it? (assumed: Ryan, manually)
- Q2 Exact demo night date/time — must match a night live-sim generates (placeholder Sat 2026-11-14 23:30 ET).
- Q3 Ship the 39 MB `manhattan_bars.db` to Render or a slim `app.db`? (assumed slim, launch venues + needed columns)
- Q4 Render/Vercel account owner, project names, custom domain? (assumed default subdomains)
- Q5 Should scout/owner auth be faked (pick-a-persona) for the demo? (assumed yes, per backend's MVP auth)
- Q6 Are POSTs during the demo persisted (Render disk is ephemeral)? (assumed reset on redeploy; acceptable)
- Q7 Do Run My Night and heatmap count toward "working model"? (assumed nice-to-have)
- Q8 Is CI (GitHub Actions) wanted, or local `make test` enough for the course?

## 12. Contract change requests

Recorded here per the brief (also copied to `docs/workstreams/integration.md` at build time). CONTRACTS.md is not edited.

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
