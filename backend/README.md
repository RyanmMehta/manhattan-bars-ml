# Nightlife Autopilot backend

FastAPI + SQLAlchemy 2.0 + Alembic. Contract: `docs/CONTRACTS.md` (v2.2). Machine-readable
contract: `GET /openapi.json` (copy in `backend/openapi.json`); Swagger UI at `/api/docs`.

## Run locally
```bash
pip install -r backend/requirements-dev.txt
DEMO_NOW=2026-11-14T23:30:00-05:00 backend/scripts/start.sh     # http://localhost:8000/api/health
python backend/scripts/smoke.py http://localhost:8000           # hits every endpoint
```
`start.sh` = `alembic upgrade head` → `scripts/ensure_sim.py` → uvicorn on `$PORT` (8000).
Without `data/live_sim.db` it uses a tiny fixture sim DB (one night, seed 42) when
`ALLOW_FIXTURE_SIM=1` (the default locally; `0` on Render).

Build the real synthetic DB (needs live-sim's `simulator/`): `bash backend/scripts/build_sim.sh`
(from the repo root). To use real `recs`, have `recs/` importable (repo root on `PYTHONPATH`);
otherwise the stub engine (same formulas, v2 §A constants) serves every call.

## Tests
```bash
cd backend && pytest -q --cov=app            # 101 tests, ~5 s, ~95% coverage
BACKEND_TEST_RECS_MODE=recs PYTHONPATH=<dir containing recs/> pytest -q   # same suite on real recs
ruff check . && ruff format --check .
```

## Environment variables (all read in `app/config.py`)
| Name | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `sqlite:///backend/app.db` | app DB (real writes). Postgres: `postgresql+psycopg://…` |
| `LIVE_SIM_DB` | `data/live_sim.db` | live-sim output, attached read-only as `sim` |
| `INCLUDE_SYNTHETIC` | `1` | `0` hides every `syn_` row (swap-to-real-data path) |
| `DEMO_NOW` | unset | default `now` for reads; writes are stamped at it too |
| `CORS_ORIGINS` | `http://localhost:5173,https://nightlife-autopilot.vercel.app` | comma list (Vercel URL is a placeholder) |
| `FEATURE_ROUTING` / `FEATURE_HEATMAP` | `1` | `0` → `/api/plan-night` / `/api/heatmap` return 404 |
| `PUBLIC_DB_PATH` | `data/manhattan_bars.db` | public venue data (read-only) |
| `LAUNCH_VENUES_CSV` / `LAUNCH_VENUES_FULL_CSV` | `data/launch_venues.csv` / `data/launch_venues_full.csv` | full CSV preferred when present |
| `MANUAL_ATTRIBUTES_CSV` | `data/venue_attributes_manual.csv` | hand-labelled attributes override synthetic ones |
| `ALLOW_FIXTURE_SIM` | `1` | fall back to the fixture sim DB (dev/tests only) |
| `DEMO_AUTH` | `1` | `0` disables `/api/auth/demo-login` |
| `ADMIN_TOKEN` | unset | bearer token with all roles (Render generates it) |
| `RECS_MODE` | `auto` | `auto` / `recs` (require recs) / `stub` |
| `LOG_LEVEL` | `INFO` | JSON logs to stdout |
| `ALLOW_WRITE_NOW` | `0` | tests only: lets writes take `?now=` |

`.env.example` lists them; the app does not read `.env` files (export them or use `docker --env-file`).

## Docker / Render
```bash
docker build -f backend/Dockerfile -t nightlife-backend .     # context = repo root
docker run -p 8000:8000 -e DEMO_NOW=2026-11-14T23:30:00-05:00 nightlife-backend
```
The image runs `scripts/build_sim.sh` at build time, so `live_sim.db` is baked in.
Render steps: see `docs/workstreams/backend.md` → "Deploy".
