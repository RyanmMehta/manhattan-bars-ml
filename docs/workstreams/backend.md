# Workstream: backend (as built)

Owner: Ryan Mehta · Branch: `nightlife/backend` · Folder: `backend/` · Built Tue Nov 17 2026 (demo day).
Plan: `docs/prd/backend/` (PRD, RULES, OUTLINE). Contract: `docs/CONTRACTS.md` v2.2 (`b46d75f`).

## What was built
- FastAPI app (`backend/app/`), app factory `create_app(settings)`, every endpoint in the
  CONTRACTS table plus v2 §G (`/api/auth/demo-login`, `/api/feedback`, `/api/heatmap?by=hour`).
  Error envelope on all errors (incl. 422), `X-Data` on lists, `X-Total-Count` on `/api/venues`,
  `is_synthetic` on every response object, `now=` replay on every read.
- Layers: `routers/` (HTTP) → `services/` → `repo/` (SQL) + `engine/` (recs adapter).
  `repo/sources.py` is the only place that builds `real UNION ALL sim.syn_*`; `INCLUDE_SYNTHETIC=0`
  removes the synthetic side there.
- SQLAlchemy 2.0 models for the real twin tables (`users, scouts, api_tokens, scout_reports,
  venue_updates, venue_events, points_ledger, bounties, bounty_claims, feedback, disputes,
  venue_attributes`), all created empty by Alembic `0001`.
- Engine: `get_engine()` uses real `recs` when importable, else `StubEngine` (specs §5 formulas,
  v2 §A constants). Each recs call that raises falls back to the stub for that call; recs output
  is validated with the Pydantic models (malformed → stub). Health reports `recs: real|stub`.
- Scripts: `start.sh` (migrate → ensure_sim → uvicorn), `build_sim.sh` (build-time live_sim.db),
  `ensure_sim.py` (schema check; `--copy-to-db` for Postgres), `smoke.py BASE_URL`,
  `export_openapi.py` → `backend/openapi.json`. `Dockerfile` (+ `Dockerfile.dockerignore`),
  `render.yaml`.

## Verified
- `cd backend && pytest -q --cov=app`: **94 passed (+2 skipped without a real live_sim.db), ~5 s, ~95% coverage**; `ruff check` clean.
- **Specs golden vectors G1–G8** (`docs/specs/golden_vectors.json` from origin/nightlife/specs `fdcd327`,
  copied as test fixture `backend/tests/fixtures/specs_golden_vectors.json`): all 8 states and the
  G4/G5/G6 recommendations match within specs' tolerances, on the stub and on real recs.
  Covers every endpoint, each PRD §5 AC, auth (401/403/404), 422/429, golden G1 (vibe 65 /
  conf 0.67) and G5 (match 83 / rank 76), midnight replay (23:59 report seen at 00:10),
  `INCLUDE_SYNTHETIC=0` sweep, migration up/down, sim schema check, recs-failure fallback,
  no truth/reputation-history tables referenced in `app/`.
- **Against real `recs`** (origin/nightlife/ml-recs `7153736`, re-checked on `219b735`; via `PYTHONPATH`, not copied):
  full suite 107 passed on `219b735` (G1/G5 also run through recs); local server + smoke script: 18/18 calls
  served by recs, 0 stub fallbacks; `/api/venues` ~10 ms, `/api/recommend` ~16 ms,
  `/api/heatmap?by=hour` ~27 ms.
- Local boot with `start.sh` + `smoke.py`: all endpoints OK (stub and recs).
- **Real `live_sim.db`** (live-sim `9921e56`, built with `python -m simulator --seed 42 --out data/live_sim.db`
  in 12 s, 18 MB): schema matches v2 §E with no diffs; with real recs (`ef9717c`) the full suite passes (109,
  incl. `tests/test_real_livesim.py`), smoke 18/18 with 0 stub fallbacks; at DEMO_NOW the 35 launch
  venues show 16 show / 12 low / 7 none; every endpoint < 100 ms (`launch_only=false` 88 ms).
- Heatmap `by=hour` vs live-sim's `demo_night_snapshots.csv`: 209/245 HH:30 cells identical; the rest
  differ because live-sim computed snapshots with its own `simulator/_live_state.py`, not recs
  (e.g. a single thin report gets vibe 25 there, null in recs). Integration already plans to regenerate
  the snapshots after the ml-recs merge.
- **Not verified:** Docker build (no Docker daemon in the build container), Render deploy (no
  account yet), Postgres run.

## How to run
See `backend/README.md`. Short version:
`pip install -r backend/requirements-dev.txt && DEMO_NOW=2026-11-14T23:30:00-05:00 backend/scripts/start.sh`.

## Deploy (Render, once Ryan has an account)
1. Render → New → Blueprint → repo `ryanmmehta/manhattan-bars-ml`, branch `nightlife/backend`
   (integration later points it at the merged branch), Blueprint path `backend/render.yaml`.
2. The Blueprint creates one Docker web service (`dockerfilePath: backend/Dockerfile`,
   `dockerContext: .`, health check `/api/health`, plan free) with `DEMO_NOW`, `INCLUDE_SYNTHETIC=1`,
   `ALLOW_FIXTURE_SIM=0`, `DEMO_AUTH=1`, `RECS_MODE=auto`, both feature flags on, `ADMIN_TOKEN`
   generated, and `CORS_ORIGINS` = placeholder Vercel URL + localhost. **Replace the Vercel URL**
   once frontend deploys.
3. The image build runs `backend/scripts/build_sim.sh` (live-sim's generator) so `live_sim.db`
   is baked in. With `ALLOW_FIXTURE_SIM=0`, boot fails loudly if it is missing — so deploy from a
   branch that contains `simulator/` (and `recs/`), i.e. the integration branch.
   For a quick demo without live-sim, set `ALLOW_FIXTURE_SIM=1` (one fixture night).
4. After deploy: `python backend/scripts/smoke.py https://<service>.onrender.com`.
5. Free tier sleeps when idle and has an ephemeral disk: app-DB writes reset on restart.
   Warm it 2 minutes before class (`curl …/api/health`).
6. Postgres later: `DATABASE_URL=postgresql+psycopg://…`; release step `alembic upgrade head &&
   python backend/scripts/ensure_sim.py --copy-to-db`.

## Assumptions (recorded during the build; no questions asked)
1. **Timestamps are ISO 8601 strings in America/New_York** in the real tables too (not
   `DateTime(timezone=True)` as RULES §4 said), so real and `syn_` twins `UNION ALL` without casts.
   SQL filters lexically with a 90-min slack, then exact filtering happens in Python (DST-safe).
2. **Writes are stamped at `DEMO_NOW` when it is set** (else server clock), so a report posted in
   the demo shows up in the replayed night (demo step 5). `ALLOW_WRITE_NOW=1` (tests) lets writes take `?now=`.
3. Public venue data (launch list, `v_bars`, OSM names/hours) is loaded once, read-only, into
   memory instead of `ATTACH … AS pub`; works the same on SQLite and Postgres. Source priority:
   `launch_venues_full.csv` → `manhattan_bars.db` → `launch_venues.csv` alone.
   `launch_only=false` returns the 1,709 `v_bars` rows that have coordinates (18 have none).
4. Pending and accepted reports count in live state; disputed half; flagged/removed zero.
5. Points (placeholders, `config.py`): base 10, verified +5, first report at that venue tonight +5,
   plus the bounty's points. Bounties are claimed only by a **verified** report (specs §7.3 #6).
   Synthetic bounties can't be updated in the read-only sim DB, so claims are recorded in the real
   `bounty_claims` table and merged on read.
6. Rate limit: one report per scout per venue per 15 min (placeholder) → 429.
7. Heatmap `by=hour` returns only hours that have started by `now` (state at HH:30, capped at
   `now`); at DEMO_NOW that is 20–23.
8. Owner dashboard counts are since 18:00 ET of the current night; `demand_by_hour` = all events
   per hour from 18:00 to `now`.
9. Stub plan-night: greedy over the top 8 by `rank_score`, objective `rank_score − 10·walk_km`
   (specs §5.12), walk budget counts legs between stops (not the walk to the first stop).
10. Stub never excludes on opening hours (all hours treated as unknown); real recs parses them.
11. 311 complaint-risk bands: low < 25 ≤ medium < 100 ≤ high (placeholder).
12. Feedback `user_id` defaults to the token's user; a different `user_id` → 403.
13. `/api/recommend` with a user token attaches `user_id` to impression events (used for feedback's `recommended_at`).
14. CORS default includes a placeholder `https://nightlife-autopilot.vercel.app`.

15. The backend sets `rank` itself after ordering (non-excluded by `rank_score`, then excluded),
    because recs leaves `rank` null on excluded rows. The stub scores an over-limit cover or line with
    its normal formula (specs G6); the exclusion is a separate flag.

## Optional fields added (all optional, no renames)
Venue card: `address`, `neighborhood`. Report response: `verified_presence`, `distance_m`.
Login response: `role`, `venue_id`. Health: `is_synthetic`. Recommendation/Stop: as v2 §F.

## Open issues
- Docker image build and Postgres run not tested here (no Docker daemon).
- Not built (later per PRD): dispute endpoints, velocity/outlier anti-gaming checks at write time,
  pending → accepted promotion job, bounty auto-creation job, owner-created bounties.
- recs' own `complaint_risk` is null; the backend fills it from public data (v2 §F says it's a
  recommendation field, so either side can own it).

## Contract change requests
- **CR-15 (build command) — accepted (contracts `f5c95d2`), build_sim.sh now runs `python -m simulator …`:** `python -I -m simulator …` fails from the repo root because `-I`
  drops the cwd from `sys.path` ("No module named simulator"; reproduced). Either install
  `simulator` as a package before running it, or drop `-I` (use `-P`-free `python -m`).
  `backend/scripts/build_sim.sh` tries the contract command, then falls back to `python -m simulator`.
- **CR-16 (Stop shape) — accepted:** `walk_minutes_from_prev` is a float in real recs (e.g. 5.3) — the
  backend schema accepts float; please state "number" in the contract.
- **CR-18 (rank) — accepted (contracts `ad2dd2f`, API owns final rank):** recs returns `rank: null` for excluded rows; the contract implies a 1-based
  rank on every row. The backend fills it in; recs or the contract should pick one.
- **CR-17 (heatmap) — accepted:** document that `by=hour` omits hours that haven't started at `now`.
- Still open from PRD §13: backend keeps internal `users`, `venue_attributes` (and now
  `bounty_claims`) real tables — integration please confirm.
