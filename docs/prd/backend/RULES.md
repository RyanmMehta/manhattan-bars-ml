# RULES: backend build session

Read this before writing any code in `backend/`. These rules are binding for the
build session. Also obey `docs/CONTRACTS.md`; if they conflict, CONTRACTS.md wins.

## 1. Branch and git
- Work only on `nightlife/backend` (branched from `nightlife/contracts`).
- Push with `git push -u origin nightlife/backend`. No PRs. Never push to `main`.
- Small commits, imperative subject (`Add /api/reports endpoint`). Run tests before each push.
- Don't edit `docs/CONTRACTS.md`. Put proposed changes under "Contract change requests" in
  `docs/workstreams/backend.md` (and keep `docs/prd/backend/PRD.md` §13 in sync).

## 2. What you own / must not touch
**Own (write freely):**
- `backend/**`
- `docs/workstreams/backend.md`, `docs/synthetic/backend.md`, `docs/prd/backend/**`
- `backend/render.yaml` (backend service only). The repo root isn't ours: if Render's
  Blueprint needs the file at root, integration copies it there (logged as CR-10), or Ryan
  sets a custom Blueprint path in the Render dashboard.

**Read only:**
- `data/manhattan_bars.db`, `data/live_sim.db`, `data/launch_venues*.csv`,
  `data/venue_attributes_manual.csv`, `data/raw/`, `data/synthetic/` — never write,
  never migrate, never `VACUUM`. Open with `sqlite3.connect("file:...?mode=ro", uri=True)`.
- `data/synthetic_live/`, `simulator/` (owned by live-sim) — read only; the start script may *run*
  the live-sim CLI to generate `live_sim.db`, never edit it.
- `recs/` (ml-recs) — import only; never patch it. If it's broken, fall back to the stub and
  file an issue in `docs/workstreams/backend.md`.

**Do not touch:** `src/`, `simulator/`, `frontend/`, `analytics/`, `research/`, `coursework/`,
`docs/specs/`, other workstreams' docs, `run_all.sh`, root `requirements.txt`, `README.md`
(integration updates it).

## 3. Stack and versions
Pin exact versions in `backend/requirements.txt` at build time (latest patch available that
day, then frozen). Minimums:

| Package | Min | Why |
|---|---|---|
| Python | 3.12 (Docker `python:3.12-slim`) | dev box has 3.13; code must run on both |
| fastapi | 0.115 | |
| uvicorn[standard] | 0.32 | |
| pydantic | 2.9 | v2 API only (`model_validate`, `ConfigDict`) |
| pydantic-settings | 2.6 | env config |
| sqlalchemy | 2.0.36 | 2.0 style (`select()`, `Mapped[]`), no legacy `Query` |
| alembic | 1.14 | migrations |
| pandas | 3.0 | same major as root; used only in seed + recs calls |
| psycopg[binary] | 3.2 | Postgres driver (optional extra, installed in Docker) |
| pytest | 8.3 | |
| httpx | 0.27 | FastAPI TestClient |
| ruff | 0.8 | lint + format |

No other runtime dependencies without writing the reason in `docs/workstreams/backend.md`.
No ORMs besides SQLAlchemy, no Flask/Django, no Celery/Redis.

## 4. Architecture rules
- App factory: `backend/app/main.py: create_app(settings) -> FastAPI`. Module-level `app = create_app()` for uvicorn.
- Layers: `routers/` (HTTP only) → `services/` (logic) → `repo/` (SQL) and `engine/` (recs adapter).
  Routers never run SQL; repo never imports FastAPI.
- All config through `backend/app/config.py` (`Settings(BaseSettings)`). No `os.environ` elsewhere.
- Placeholder numbers not yet fixed by specs (rate limits, points) live only in `config.py`, each with
  `# PLACEHOLDER(specs): <what decides this>`.
- DB: SQLAlchemy 2.0 models in `backend/app/models.py`; every schema change is an Alembic
  revision. `create_all()` allowed only in tests.
- Portable SQL only: no SQLite-only functions in queries (`julianday`, `strftime`), no
  Postgres-only types. Timestamps stored as timezone-aware UTC (`DateTime(timezone=True)`);
  API emits ISO 8601 in America/New_York (contract).
- Time: one helper `app/timeutil.py: parse_now(str|None) -> datetime` (aware, UTC internally).
  Never call `datetime.now()` outside it. Reads use `now` from query → `DEMO_NOW` → server clock.
- recs: import only via `backend/app/engine/__init__.py: get_engine()`. It tries `import recs`;
  on ImportError or `RECS_MODE=stub` it returns `StubEngine`. Each call is wrapped: an exception
  in recs logs a warning and falls back to the stub for that call. `/api/health` reports
  `recs: real|stub`; the request log records which engine served each call.
- Stub constants are the v2 §A values (half-lives 30/60/120 min, cutoff 180 min, `w_rep = 0.25+0.75r`,
  unverified 0.6, k 1.5, display 0.40/0.20, unknown component 0.4, presence 150 m, rank formula),
  defined once in `config.py` with `# SPEC(v2 §A)` comments.
- Pass recs report rows with `reputation` joined from scouts (default 0.5) (v2 §F).
- Validate recs output with the Pydantic response models before returning. Never return a
  dict straight from recs.
- Response models in `backend/app/schemas.py` use the exact CONTRACTS.md field names.
  Do not rename, nest or add required fields without a change request; optional extra
  fields are allowed only if listed in CONTRACTS v2 or PRD §13.
- Missing data is `null`. Never substitute a favourable default (e.g. line 0, cover 0).
- Error envelope per CR-1 via exception handlers; no bare `HTTPException(detail=...)` strings leak.

## 5. Auth rules (MVP)
- Reads are public. Writes need `Authorization: Bearer <token>`.
- Tokens: `secrets.token_urlsafe(32)`, stored as SHA-256 hex in `api_tokens(token_hash, role, subject_id, created_at, revoked)`.
- Roles: `user` (subject = user_id), `scout` (subject = scout_id), `owner` (subject = venue_id),
  `admin` (from `ADMIN_TOKEN` env).
- Owner endpoints check `subject_id == venue_id` → else 403. Owners cannot report their own venue (v2 §G).
- Store `distance_m` only; never store or log raw report lat/lon (v2 §A).
- `/api/auth/demo-login` exists only when `DEMO_AUTH=1`. Never log tokens.

## 6. Coding conventions
- `ruff check` and `ruff format` clean; line length 100; type hints on every function.
- Names: snake_case; routers named by resource (`venues.py`, `reports.py`).
- No print; use `logging` (JSON formatter in `app/logging.py`).
- No commented-out code. Docstrings only where the why isn't obvious.
- IDs: `report_id`, `update_id`, `event_id` = UUID4 strings; `venue_id` = SLA `license_id`.

## 7. Synthetic-data marking (mandatory, from CONTRACTS.md)
1. Every synthetic table has `is_synthetic` (1); every synthetic DB table name starts with `syn_`.
2. Real app tables (`scout_reports`, `venue_updates`, `venue_events`, `scouts`, `users`, `bounties`,
   `points_ledger`, `feedback`, `venue_attributes`) set `is_synthetic = 0` and have the same columns
   as their `syn_` twin so reads can `UNION ALL` (v2 §E). Real IDs are UUID4; synthetic IDs start `syn-`.
2a. `data/live_sim.db` is attached read-only as `sim`. Never write to it. Never read
   `syn_true_state`, `syn_scout_truth` (evaluation-only, v2 §E) or `syn_scout_reputation_history`
   (training/eval only; the live app uses current reputation, v2.1) — a test greps for them.
3. Every line that reads or generates synthetic data gets a comment:
   `# SYNTHETIC: <real source that replaces this>`, e.g.
   `# SYNTHETIC: replace with real scout reports from scout_reports once pilot runs`.
4. The only synthetic data the backend creates is the test fixture sim DB, built at test time under `backend/tests/fixtures/synthetic/`
   (path contains "synthetic").
5. Register every synthetic dataset the backend creates or loads in `docs/synthetic/backend.md`
   with: file/table, what it imitates, how generated (script + seed), real replacement, swap steps.
6. API objects built from any synthetic row include `is_synthetic: true` so the UI can show the
   "demo data" badge. Every response object has `is_synthetic`; list endpoints set header
   `X-Data: synthetic|real|mixed` (v2 §G).
7. `INCLUDE_SYNTHETIC=0` must work: every query that unions `syn_` tables checks this flag in one place (`repo/sources.py`).

## 8. Testing requirements
- pytest under `backend/tests/`; run with `cd backend && pytest -q`.
- Tests use a temp app DB plus a tiny fixture `live_sim` DB built by `tests/fixtures/make_sim.py`,
  never the real public DB or `data/live_sim.db` directly (except one marked `@pytest.mark.publicdb` smoke test, skipped if missing).
- Required:
  - one test per endpoint for the happy path and each listed AC in PRD §5;
  - contract-shape tests: compare response keys to the CONTRACTS.md JSON examples;
  - stub-engine tests (recs absent) and recs-engine tests (skipped if `recs` not importable);
  - `now` replay tests incl. a report at 23:59 and `now` at 00:10 next day;
  - auth tests: no token 401, wrong owner 403, demo-login off → 404;
  - `INCLUDE_SYNTHETIC=0` test for every read endpoint;
  - a migration test: `alembic upgrade head` on empty SQLite succeeds;
  - golden vectors G1 (vibe 65 / conf 0.67) and G5 (match 83) against the stub (v2 §A);
  - a test that no code under `backend/app/` mentions `syn_true_state` / `syn_scout_truth`.
- Suite time < 30 s. Coverage ≥ 85% on `backend/app/` (`pytest --cov=app`).
- Smoke script `backend/scripts/smoke.py <BASE_URL>` hits every endpoint; must pass against the Render URL.

## 9. Config / env vars (all read in `config.py`)
Reserved names (v2 §H) used exactly: `DATABASE_URL` (default `sqlite:///./backend/app.db`),
`LIVE_SIM_DB` (`data/live_sim.db`), `INCLUDE_SYNTHETIC` (1), `DEMO_NOW` (demo: `2026-11-14T23:30:00-05:00`),
`CORS_ORIGINS`, `FEATURE_ROUTING` (1), `FEATURE_HEATMAP` (1).
Backend-only names: `PUBLIC_DB_PATH` (`data/manhattan_bars.db`), `LAUNCH_VENUES_CSV`
(`data/launch_venues.csv`), `LAUNCH_VENUES_FULL_CSV` (`data/launch_venues_full.csv`),
`MANUAL_ATTRIBUTES_CSV` (`data/venue_attributes_manual.csv`), `ALLOW_FIXTURE_SIM` (1 in dev/tests, 0 on
Render; `live_sim.db` is built at build time, v2 §J), `DEMO_AUTH` (1), `ADMIN_TOKEN` (required in prod), `RECS_MODE` (`auto|recs|stub`),
`LOG_LEVEL` (INFO), `ALLOW_WRITE_NOW` (0). Don't invent names that collide with `VITE_*`. Document each in `backend/README.md` and `.env.example`. Never commit `.env`.

## 10. Definition of done (for the build phase)
- [ ] Every CONTRACTS.md endpoint + v2 §G additions (demo-login, feedback, heatmap `by=hour`) with contract field names.
- [ ] `scripts/start.sh` does `alembic upgrade head`, checks `live_sim.db` (built at build time, v2 §J; fixture only if `ALLOW_FIXTURE_SIM=1`), loads optional manual attributes, starts uvicorn — no manual steps.
- [ ] `pytest -q` green, < 30 s, coverage ≥ 85%; `ruff check` clean.
- [ ] Works with `RECS_MODE=stub` and with real `recs` if present.
- [ ] `INCLUDE_SYNTHETIC=0` doesn't crash any endpoint.
- [ ] Docker image builds and runs locally (`docker run -p 8000:8000`), health 200.
- [ ] Deployed to Render (once Ryan provides the account); smoke script passes on the URL.
- [ ] `docs/workstreams/backend.md` (what/how/issues + change requests) and
      `docs/synthetic/backend.md` (registry) written.
- [ ] Every synthetic touchpoint has a `# SYNTHETIC:` comment (`grep -rn "syn_" backend/app | grep -v "SYNTHETIC"` reviewed).
- [ ] Branch pushed; no files outside the owned list changed (`git diff --stat nightlife/contracts`).
