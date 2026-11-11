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
- `data/manhattan_bars.db`, `data/launch_venues.csv`, `data/raw/`, `data/synthetic/` — never write,
  never migrate, never `VACUUM`. Open with `sqlite3.connect("file:...?mode=ro", uri=True)`.
- `data/synthetic_live/` (owned by live-sim) — read only.
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
- Placeholder numbers (radius, rate limits, points) live only in `config.py`, each with
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
  in recs logs a warning and falls back to the stub for that call. Every response sets header
  `X-Recs-Engine`.
- Validate recs output with the Pydantic response models before returning. Never return a
  dict straight from recs.
- Response models in `backend/app/schemas.py` use the exact CONTRACTS.md field names.
  Do not rename, nest or add required fields without a change request; optional extra
  fields are allowed only if listed in PRD §13.
- Missing data is `null`. Never substitute a favourable default (e.g. line 0, cover 0).
- Error envelope per CR-1 via exception handlers; no bare `HTTPException(detail=...)` strings leak.

## 5. Auth rules (MVP)
- Reads are public. Writes need `Authorization: Bearer <token>`.
- Tokens: `secrets.token_urlsafe(32)`, stored as SHA-256 hex in `api_tokens(token_hash, role, subject_id, created_at, revoked)`.
- Roles: `scout` (subject = scout_id), `owner` (subject = venue_id), `admin` (from `ADMIN_TOKEN` env).
- Owner endpoints check `subject_id == venue_id` → else 403.
- `/api/auth/demo-login` exists only when `DEMO_AUTH=1`. Never log tokens.

## 6. Coding conventions
- `ruff check` and `ruff format` clean; line length 100; type hints on every function.
- Names: snake_case; routers named by resource (`venues.py`, `reports.py`).
- No print; use `logging` (JSON formatter in `app/logging.py`).
- No commented-out code. Docstrings only where the why isn't obvious.
- IDs: `report_id`, `update_id`, `event_id` = UUID4 strings; `venue_id` = SLA `license_id`.

## 7. Synthetic-data marking (mandatory, from CONTRACTS.md)
1. Every synthetic table has `is_synthetic` (1); every synthetic DB table name starts with `syn_`.
2. Real app tables (`scout_reports`, `venue_updates`, `app_events`, `scouts`) set `is_synthetic = 0`
   and have the same columns as their `syn_` twin so reads can `UNION ALL`.
3. Every line that reads or generates synthetic data gets a comment:
   `# SYNTHETIC: <real source that replaces this>`, e.g.
   `# SYNTHETIC: replace with real scout reports from scout_reports once pilot runs`.
4. Any synthetic file the backend itself creates goes under `backend/seed/synthetic/`
   (path contains "synthetic").
5. Register every synthetic dataset the backend creates or loads in `docs/synthetic/backend.md`
   with: file/table, what it imitates, how generated (script + seed), real replacement, swap steps.
6. API objects built from any synthetic row include `is_synthetic: true` so the UI can show the
   "demo data" badge. Response header `X-Data-Mode: synthetic` while `INCLUDE_SYNTHETIC=1`.
7. `INCLUDE_SYNTHETIC=0` must work: every query that unions `syn_` tables checks this flag in one place (`repo/sources.py`).

## 8. Testing requirements
- pytest under `backend/tests/`; run with `cd backend && pytest -q`.
- Tests use a temp SQLite DB built from fixtures (`backend/tests/fixtures/`), never the real
  public DB file directly (except one marked `@pytest.mark.publicdb` smoke test, skipped if missing).
- Required:
  - one test per endpoint for the happy path and each listed AC in PRD §5;
  - contract-shape tests: compare response keys to the CONTRACTS.md JSON examples;
  - stub-engine tests (recs absent) and recs-engine tests (skipped if `recs` not importable);
  - `now` replay tests incl. a report at 23:59 and `now` at 00:10 next day;
  - auth tests: no token 401, wrong owner 403, demo-login off → 404;
  - `INCLUDE_SYNTHETIC=0` test for every read endpoint;
  - a migration test: `alembic upgrade head` on empty SQLite succeeds.
- Suite time < 30 s. Coverage ≥ 85% on `backend/app/` (`pytest --cov=app`).
- Smoke script `backend/scripts/smoke.py <BASE_URL>` hits every endpoint; must pass against the Render URL.

## 9. Config / env vars (all read in `config.py`)
`DATABASE_URL` (default `sqlite:///./backend/app.db`), `PUBLIC_DB_PATH` (`data/manhattan_bars.db`),
`LAUNCH_VENUES_CSV`, `SYNTHETIC_LIVE_DIR` (`data/synthetic_live`), `INCLUDE_SYNTHETIC` (1),
`SEED_ON_START` (0 locally, 1 on Render), `DEMO_NOW` (unset), `DEMO_AUTH` (1), `ADMIN_TOKEN`
(required in prod), `RECS_MODE` (`auto|recs|stub`), `CORS_ORIGINS`, `LOG_LEVEL` (INFO),
`ALLOW_WRITE_NOW` (0). Document each in `backend/README.md` and `.env.example`. Never commit `.env`.

## 10. Definition of done (for the build phase)
- [ ] Every CONTRACTS.md endpoint + demo-login implemented with contract field names.
- [ ] `alembic upgrade head` + `cd backend && python -m seed` builds the DB from scratch with no manual steps.
- [ ] `pytest -q` green, < 30 s, coverage ≥ 85%; `ruff check` clean.
- [ ] Works with `RECS_MODE=stub` and with real `recs` if present.
- [ ] `INCLUDE_SYNTHETIC=0` doesn't crash any endpoint.
- [ ] Docker image builds and runs locally (`docker run -p 8000:8000`), health 200.
- [ ] Deployed to Render (once Ryan provides the account); smoke script passes on the URL.
- [ ] `docs/workstreams/backend.md` (what/how/issues + change requests) and
      `docs/synthetic/backend.md` (registry) written.
- [ ] Every synthetic touchpoint has a `# SYNTHETIC:` comment (`grep -rn "syn_" backend/app | grep -v "SYNTHETIC"` reviewed).
- [ ] Branch pushed; no files outside the owned list changed (`git diff --stat nightlife/contracts`).
