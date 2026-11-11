# OUTLINE: backend build plan

Follow [`RULES.md`](RULES.md). Requirements and AC IDs (BE-n) are in [`PRD.md`](PRD.md).
Sizes: **S** ≤ 1 h, **M** 1–3 h, **L** 3–6 h. Total ≈ 30–38 h of build time (placeholder).
Calendar (today Nov 11): deploy skeleton first, full API by Nov 14, hardening Nov 15–16,
integration Nov 17.

## 1. Ordered tasks

### Phase 0 — skeleton deployed (target Nov 12; covers the missed Oct 13 milestone)
- [ ] T0.1 **S** `backend/` scaffold: `pyproject.toml` (ruff, pytest config), `requirements.txt` (pinned), `requirements-dev.txt`, `.env.example`, `README.md`.
- [ ] T0.2 **S** `app/config.py` (Settings, all env vars from RULES §9), `app/timeutil.py`, `app/logging.py`.
- [ ] T0.3 **S** `app/main.py` `create_app()`; CORS; error-envelope handlers (CR-1); `GET /api/health`; `X-Recs-Engine` / `X-Data-Mode` middleware; OpenAPI at `/api/docs`.
- [ ] T0.4 **S** `tests/test_health.py`, `conftest.py` (temp DB, TestClient, settings override).
- [ ] T0.5 **M** `Dockerfile` (python:3.12-slim, non-root, `uvicorn app.main:app --host 0.0.0.0 --port $PORT`), `.dockerignore`, `scripts/start.sh` (alembic upgrade → optional seed → uvicorn).
- [ ] T0.6 **M** `backend/render.yaml`; deploy health-only build to Render (**blocked on Ryan's account** — see §7). Record URL in `docs/workstreams/backend.md`.

### Phase 1 — schema + seed (Nov 12–13)
- [ ] T1.1 **M** `app/db.py` (engine/session from `DATABASE_URL`, SQLite pragmas: WAL, foreign_keys), `app/models.py`: `venues`, `scouts`, `scout_reports`, `venue_updates`, `api_tokens`, `app_events`, and the eight `syn_` tables (seven contract + `syn_venue_events`, `syn_owner_claims`).
- [ ] T1.2 **S** Alembic init + revision `0001_initial`; test `alembic upgrade head` on empty SQLite.
- [ ] T1.3 **M** `seed/load_public.py`: read-only open of `data/manhattan_bars.db`; copy `v_bars` columns needed (license_id→venue_id, name, address, zip, lat, lon, venue_type, neighborhood, noise_complaints, osm_id) + `osm_venues.name/opening_hours/website`; display-name rule (PRD F6); `is_launch` from `launch_venues.csv` (assert 35).
- [ ] T1.4 **M** `seed/load_synthetic.py`: load every `data/synthetic_live/*.csv` into its `syn_` table; validate columns against contract; check `is_synthetic==1` on every row; fail loudly with a column diff.
- [ ] T1.5 **M** `seed/fixtures.py`: deterministic (seed 42) mini synthetic set for tests and as a fallback when live-sim CSVs are absent: attributes for 35 venues, 20 scouts, ~200 reports over one Saturday 20:00–03:00, 15 updates, 5 bounties, `syn_venue_events`, `syn_owner_claims`. Writes small CSVs to `backend/seed/synthetic/`, committed so tests and Render work without live-sim.
- [ ] T1.6 **S** `seed/__main__.py`: `python -m seed [--reset] [--fixtures-only] [--include-all-bars]`; idempotent; prints row counts and demo tokens.
- [ ] T1.7 **S** `repo/sources.py`: one place that builds `scout_reports UNION ALL syn_scout_reports` (and updates/events) honoring `INCLUDE_SYNTHETIC` and `now`.

### Phase 2 — engine adapter (Nov 13)
- [ ] T2.1 **M** `engine/base.py` Protocol with the 4 contract functions; `engine/recs_engine.py` (wraps `recs`, converts DataFrames as `recs` expects); `engine/stub.py`.
- [ ] T2.2 **M** Stub logic: live_state = reputation-weighted mean with exp decay (half-life 45 min `# PLACEHOLDER(specs)`), confidence = min(1, Σweights/3), trend from last-30-min vs prior; recommend = hard-limit exclusions (cover, line, distance) + score 0.5·vibe + 0.3·distance score + 0.2·genre overlap, honest reasons/missing; plan_night = greedy nearest-next of top 8.
- [ ] T2.3 **S** `engine/__init__.py get_engine()` with per-call fallback + logging; tests for both modes.

### Phase 3 — endpoints (Nov 13–14)
- [ ] T3.1 **M** `routers/venues.py`: `GET /api/venues` (q, neighborhood, style, genre, launch_only, limit/offset), `GET /api/venues/{id}`, `GET /api/venues/{id}/state` — BE-2/3/4.
- [ ] T3.2 **S** `routers/heatmap.py` — BE-11.
- [ ] T3.3 **M** `routers/auth.py` + `services/auth.py` (demo-login, bearer dependency, role checks) — BE-13.
- [ ] T3.4 **M** `routers/reports.py` + `services/reports.py`: validation, haversine verified_presence, rate limit, points + bounty claim — BE-5.
- [ ] T3.5 **S** `routers/scouts.py` (leaderboard) + `routers/bounties.py` — BE-6.
- [ ] T3.6 **M** `routers/recommend.py`: `/api/recommend`, `/api/plan-night`; log `recommend_impression` events — BE-7/8.
- [ ] T3.7 **M** `routers/owner.py`: dashboard (app_events ∪ syn_venue_events, demand_by_hour) + updates — BE-9/10.
- [ ] T3.8 **S** `app_events` middleware: log `view` on venue detail, `tap` on `/state`. (No PII; user optional.)

### Phase 4 — hardening + docs (Nov 15–16)
- [ ] T4.1 **M** Contract-shape tests against CONTRACTS.md examples; `INCLUDE_SYNTHETIC=0` sweep; replay/midnight tests; coverage ≥ 85%.
- [ ] T4.2 **S** `scripts/smoke.py BASE_URL` (all endpoints, exits non-zero on any failure).
- [ ] T4.3 **S** `scripts/export_openapi.py` → `backend/openapi.json` (frontend generates TS types from it).
- [ ] T4.4 **S** Postgres check: run test suite once with `DATABASE_URL=postgresql+psycopg://...` in a local container (if Docker available); note results.
- [ ] T4.5 **M** Docs: `backend/README.md` (run, seed, env, deploy), `docs/workstreams/backend.md` (built, how to run, issues, contract change requests copied from PRD §13), `docs/synthetic/backend.md` (registry, §4 below).
- [ ] T4.6 **S** Redeploy to Render with `SEED_ON_START=1`, `DEMO_NOW` set; smoke passes; hand URL + tokens to integration.

## 2. File tree to create

```
backend/
  README.md
  pyproject.toml              # ruff + pytest config
  requirements.txt            # pinned runtime
  requirements-dev.txt        # pytest, pytest-cov, httpx, ruff
  .env.example
  .dockerignore
  Dockerfile
  render.yaml
  alembic.ini
  openapi.json                # generated (T4.3)
  migrations/
    env.py
    versions/0001_initial.py
  app/
    __init__.py
    main.py                   # create_app, middleware, handlers
    config.py                 # Settings + PLACEHOLDER(specs) constants
    timeutil.py               # parse_now, to_ny_iso
    logging.py
    db.py
    models.py                 # SQLAlchemy 2.0 models (real + syn_)
    schemas.py                # Pydantic: contract shapes + CR-5 shapes
    errors.py                 # error envelope
    deps.py                   # get_db, get_now, auth dependencies
    repo/
      __init__.py
      venues.py
      reports.py
      updates.py
      scouts.py
      events.py
      sources.py              # real ∪ syn_ unions, INCLUDE_SYNTHETIC
    services/
      auth.py
      reports.py              # validation, verified_presence, points, bounty claim
      venues.py               # cards, profile assembly
      owner.py                # dashboard aggregation
    engine/
      __init__.py             # get_engine(), fallback
      base.py                 # Protocol
      recs_engine.py
      stub.py
    routers/
      health.py  venues.py  heatmap.py  reports.py  scouts.py
      bounties.py  recommend.py  owner.py  auth.py
  seed/
    __init__.py
    __main__.py
    load_public.py
    load_synthetic.py
    fixtures.py
    synthetic/                # backend-generated synthetic CSVs (small, committed)
  scripts/
    start.sh
    smoke.py
    export_openapi.py
  tests/
    conftest.py
    fixtures/                 # tiny CSVs incl. 5-venue public extract
    test_health.py  test_venues.py  test_state.py  test_reports.py
    test_scouts_bounties.py  test_recommend.py  test_plan_night.py
    test_owner.py  test_heatmap.py  test_auth.py  test_replay.py
    test_synthetic_toggle.py  test_contract_shapes.py  test_migrations.py
docs/workstreams/backend.md
docs/synthetic/backend.md
```

## 3. Interfaces

### Consumed
| From | Interface | Contract ref |
|---|---|---|
| existing | `data/manhattan_bars.db` → `v_bars`, `osm_venues` (read-only) | CONTRACTS "Repository layout", "Launch venues" |
| existing | `data/launch_venues.csv` (35 rows, `license_id` = `venue_id`) | "Launch venues" |
| live-sim | `data/synthetic_live/{syn_venue_attributes,syn_scouts,syn_users,syn_scout_reports,syn_venue_updates,syn_feedback,syn_bounties}.csv` (+ `syn_venue_events.csv` if CR-7 accepted) | "Data schemas" |
| ml-recs | `recs.live_state.compute / compute_all`, `recs.scoring.recommend`, `recs.routing.plan_night` | "Python interface" |
| specs | half-life, reputation weights, radius, points, thresholds (copied into `config.py`) | `docs/specs/` |

Adapter data passing to `recs` (assumption, confirm with ml-recs): `reports_df`/`updates_df` are
pandas DataFrames with contract columns, `ts` as tz-aware datetime; `venues` is a list of dicts
with `venue_id, name, lat, lon` + `syn_venue_attributes` fields; `now` is tz-aware datetime.

### Provided
| To | Interface |
|---|---|
| frontend | HTTP API in CONTRACTS.md (all 12 rows) + `POST /api/auth/demo-login`; `backend/openapi.json`; CORS for its origin; `is_synthetic` on objects; headers `X-Recs-Engine`, `X-Data-Mode`, `X-Total-Count` |
| integration | `python -m seed`, `scripts/start.sh`, `scripts/smoke.py`, Dockerfile, `render.yaml`, env var table, deployed URL |
| tableau (later) | optional `GET /api/export/{table}.csv` |

Endpoint → engine call map:
- `/venues`, `/venues/{id}`, `/state`, `/heatmap` → `live_state.compute_all` (or `compute`) at `now`
- `/recommend` → `compute_all` → `scoring.recommend(prefs, states, venues, now)`
- `/plan-night` → `compute_all` → `routing.plan_night(prefs, states, venues, start_time=now, n_stops)`

## 4. Synthetic datasets the backend needs

| Dataset | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `syn_venue_attributes` (live-sim; fixture fallback) | genres, style, dance floor, cover, capacity, price | live-sim; fallback `seed/fixtures.py` seed 42, style by venue_type + OSM tags | operator-claimed profiles (owner form) + Google/Yelp Places where terms allow | add `venue_attributes` real table, write owner form endpoint, change `repo/sources.py` to prefer real row per venue, set `INCLUDE_SYNTHETIC=0` |
| `syn_scouts` | scout profiles, reputation | live-sim | real `scouts` table (already exists for app sign-ups) | drop union in `sources.py` |
| `syn_users` | group prefs, home location | live-sim | real user accounts + saved prefs (later) | not used by MVP endpoints except owner demand; remove from seed |
| `syn_scout_reports` | 10-second vibe checks over Thu–Sat nights | live-sim; fallback ~200 rows | real `scout_reports` from `POST /api/reports` during pilot | `INCLUDE_SYNTHETIC=0`; delete `syn_` rows; nothing else changes (same columns) |
| `syn_venue_updates` | operator posts, offers | live-sim; fallback 15 rows | real `venue_updates` from owner endpoint | same as above |
| `syn_bounties` | open bounties | live-sim; fallback 5 rows | bounties auto-created by a rule (low confidence + high demand) or owners (later) | add `bounties` real table + creation job; switch source |
| `syn_feedback` | post-visit outcomes | live-sim | real `POST /api/feedback` (later) | loaded but unused in MVP; register anyway |
| `syn_venue_events` (CR-7; backend fallback) | owner-dashboard views/taps/saves/impressions by hour | live-sim if accepted, else `seed/fixtures.py`: Poisson per venue-hour, rate ∝ syn crowd curve, seed 42 | real `app_events` (logged by middleware) | `INCLUDE_SYNTHETIC=0`; dashboard reads only `app_events` |
| `syn_owner_claims` (backend) | which operator owns which venue | `seed/fixtures.py`: one demo owner per launch venue | real claim flow (verify via phone/email/SLA license) | add `owner_claims` table + claim endpoint; delete demo tokens |

All rows `is_synthetic=1`; each registered in `docs/synthetic/backend.md`; each code read site
marked `# SYNTHETIC: ...`.

## 5. Test plan

| Layer | What | Tool |
|---|---|---|
| Unit | `parse_now` (offsets, Z, naive → reject), haversine, display-name cleanup, stub scoring (exclusions, null handling), points rules | pytest |
| Repo | unions with/without synthetic, `now` filter, pagination | pytest + temp SQLite |
| API | every endpoint happy path + each AC in PRD §5 (401/403/404/422/429) | TestClient |
| Contract | keys/types of Live Venue State, Recommendation result, heatmap rows equal CONTRACTS.md examples | `test_contract_shapes.py` |
| Engine | stub always; real recs if importable (`pytest.importorskip("recs")`); recs raising → stub fallback + header | pytest |
| Migration | `alembic upgrade head` on empty DB; downgrade base | pytest |
| Seed | fixtures-only seed yields 35 launch venues, counts > 0, all syn rows `is_synthetic=1` | pytest |
| Public DB smoke | real `manhattan_bars.db` loads 35 launch + 1,727 bars | `@pytest.mark.publicdb` |
| Deployed | `scripts/smoke.py https://<render-url>` | manual + integration |
| Postgres | full suite on Postgres once (T4.4) | local Docker |

Commands: `cd backend && pytest -q --cov=app` · `ruff check . && ruff format --check .`

## 6. Demo script (≈4 min, for Nov 17)

Setup: Render deployed with `DEMO_NOW=2026-11-14T22:00:00-05:00`, `SEED_ON_START=1`. Warm the
service 2 min before (`curl $URL/api/health`).
1. `GET /api/health` → `{"ok": true}`; point out `X-Recs-Engine: recs` and `X-Data-Mode: synthetic`.
2. `GET /api/venues` → 35 LES cards; most have low confidence at 22:00. Show the `/api/docs` page.
3. Replay: `GET /api/heatmap?now=2026-11-15T00:30:00-05:00` → vibe scores up along Ludlow/Orchard.
4. `POST /api/recommend` with the contract's example prefs (hip-hop, dancing, ≤$20, ≤15 min line) at 00:30 → top 3 with reasons and `missing`; one venue excluded for cover.
5. Demo-login as scout → `POST /api/reports` at a venue (crowd 5, dancing 2, line 20) → 201, points +10; `GET /state` shows confidence up and `n_reports` +1; bounty claimed.
6. `POST /api/plan-night` `n_stops=3` → ordered route with walk minutes.
7. Demo-login as owner of the same venue → `POST /updates` with an offer → appears in `GET /venues/{id}`; `GET /dashboard` shows demand by hour, flagged `is_synthetic: true`.
8. Close: flip to a local instance with `INCLUDE_SYNTHETIC=0` → same API, only real rows (the one report from step 5). That's the swap path.

## 7. Deploy steps (Ryan supplies accounts)

Ryan provides: Render account connected to GitHub `ryanmmehta/manhattan-bars-ml`; later the
Vercel frontend URL. Nothing else (no paid APIs).
1. Render → New → Blueprint → repo, branch `nightlife/backend` (integration later switches to the merged branch), blueprint path `backend/render.yaml`.
2. `render.yaml` (to be written): one `web` service, `runtime: docker`, `dockerfilePath: backend/Dockerfile`, `dockerContext: .` (needs `data/`), `healthCheckPath: /api/health`, plan `free` (placeholder; Starter if a persistent disk is wanted), env vars: `SEED_ON_START=1`, `INCLUDE_SYNTHETIC=1`, `DEMO_AUTH=1`, `RECS_MODE=auto`, `CORS_ORIGINS=<vercel url>,http://localhost:5173`, `DEMO_NOW=<set at demo time>`, `ADMIN_TOKEN` (`generateValue: true`).
3. Deploy; wait for health check; run `python backend/scripts/smoke.py https://<service>.onrender.com`.
4. Free tier caveats (verify current Render limits at deploy time): sleeps after idle (~15 min), ephemeral filesystem → SQLite reseeded on every boot, demo writes lost on restart.
5. Postgres later: create Render Postgres, set `DATABASE_URL` (as `postgresql+psycopg://...`), `start.sh` runs `alembic upgrade head` then seed. No code changes expected.

## 8. Assumptions recorded
- `recs` accepts pandas DataFrames for reports/updates (confirm with ml-recs).
- live-sim writes one CSV per `syn_` table named exactly after the table.
- Venue display names come from OSM (all 35 launch venues have `osm_id`).
- Neighborhood for all launch venues is `LES/Chinatown` (from `venues.neighborhood`).
- Demo night = Saturday Nov 14 → Sunday Nov 15, 2026, 20:00–03:00 ET (placeholder; live-sim decides).
- Docker build context is the repo root so `data/manhattan_bars.db` (≈40 MB) can be copied read-only.
