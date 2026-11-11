# OUTLINE: backend build plan

Follow [`RULES.md`](RULES.md). Requirements and AC IDs (BE-n) are in [`PRD.md`](PRD.md).
Revised for Contracts v2 (Nov 11). Sizes: **S** ≤ 1 h, **M** 1–3 h, **L** 3–6 h.
Total ≈ 28–36 h of build time (placeholder).

Calendar (v2 §I): upstream deadline **Fri Nov 13 18:00 ET**; integration merges backend
after ml-recs; deploy dry-run Nov 15; freeze Nov 16 20:00; demo Nov 17.
Order: deploy skeleton → data layer + stub → endpoints → hardening. Heatmap and plan-night
sit behind `FEATURE_HEATMAP` / `FEATURE_ROUTING` so they can ship last without blocking.

## 1. Ordered tasks

### Phase 0: skeleton deployed (Nov 11–12; covers the missed Oct 13 milestone)
- [ ] T0.1 **S** `backend/` scaffold: `pyproject.toml` (ruff, pytest), pinned `requirements.txt`, `requirements-dev.txt`, `.env.example`, `README.md`.
- [ ] T0.2 **S** `app/config.py` (all env vars from RULES §9, v2 §A constants), `app/timeutil.py`, `app/logging.py`.
- [ ] T0.3 **S** `app/main.py` `create_app()`; CORS; error envelope (v2 §G); `GET /api/health` → `{ok, recs, data, demo_now}`; `X-Data` header helper; `/openapi.json`, docs at `/api/docs`.
- [ ] T0.4 **S** `tests/conftest.py` (temp app DB, fixture sim DB, TestClient, settings override), `test_health.py`.
- [ ] T0.5 **M** `Dockerfile` (python:3.12-slim, non-root, build context = repo root), `.dockerignore`, `scripts/start.sh` (migrate → ensure sim DB → uvicorn on `$PORT`).
- [ ] T0.6 **M** `backend/render.yaml`; deploy health-only build (**blocked on Ryan's Render account**, §7). Record URL in `docs/workstreams/backend.md`.

### Phase 1: data layer (Nov 12)
- [ ] T1.1 **M** `app/db.py`: engine from `DATABASE_URL`; on SQLite, `ATTACH` `PUBLIC_DB_PATH` as `pub` and `LIVE_SIM_DB` as `sim` (read-only URIs) on every connection; WAL + foreign keys.
- [ ] T1.2 **M** `app/models.py` (real tables only): `users`, `scouts`, `api_tokens`, `scout_reports` (+ `status`, `distance_m`), `venue_updates`, `venue_events`, `points_ledger`, `bounties`, `feedback`, `venue_attributes`. Columns mirror the `syn_` twins (v2 §E).
- [ ] T1.3 **S** Alembic `0001_initial`; migration test.
- [ ] T1.4 **M** `repo/sources.py`: the only place that builds `real UNION ALL sim.syn_*` selects; honors `INCLUDE_SYNTHETIC` and `now`; never touches `syn_true_state`/`syn_scout_truth`.
- [ ] T1.5 **M** `repo/venues.py`: launch list from `launch_venues_full.csv` if present, else `pub.v_bars` ⋈ `pub.osm_venues`; display-name rule; attributes = manual CSV row else `syn_venue_attributes`; `complaint_risk` from `noise_complaints`.
- [ ] T1.6 **M** `app/simdb.py` + `scripts/ensure_sim.py`: check `LIVE_SIM_DB` exists and its schema matches v2 §E (column diff on mismatch); if missing and `GENERATE_SIM_ON_START=1`, run the live-sim CLI; if still missing, build the fixture sim DB and log a warning.
- [ ] T1.7 **M** `tests/fixtures/make_sim.py`: deterministic (seed 42) tiny sim DB: attributes for 35 venues, 20 scouts, ~200 reports Sat Nov 14 20:00–03:00, 15 updates, 5 bounties, events, points ledger. IDs `syn-…`. Output under `backend/tests/fixtures/synthetic/` (built at test time, gitignored).
- [ ] T1.8 **S** Postgres copy-in path in `scripts/ensure_sim.py --copy-to-db` (CR-12); not run on SQLite.

### Phase 2: engine adapter (Nov 12)
- [ ] T2.1 **M** `engine/base.py` Protocol (4 contract functions); `engine/recs_engine.py` (passes lists of dicts; joins `reputation`); `engine/stub.py`.
- [ ] T2.2 **M** Stub with v2 §A constants: decayed reputation-weighted live state, confidence (k 1.5), display bands, trend windows, cutoff; recommend with hard-limit exclusions, unknown = 0.4 + missing entry, `rank_score`; plan_night greedy nearest-next of top 8.
- [ ] T2.3 **S** `engine/__init__.py get_engine()` with per-call fallback; golden vector tests G1, G5.

### Phase 3: endpoints (Nov 12–13)
- [ ] T3.1 **M** `routers/venues.py`: list (q, neighborhood, style, genre, launch_only, lat/lon, limit/offset, `X-Total-Count`, `X-Data`), detail `{venue, state, recent_reports, offers}`, state. BE-2/3/4.
- [ ] T3.2 **M** `routers/auth.py` + `services/auth.py`: demo-login (user/scout/owner), bearer dependency, role checks. BE-13.
- [ ] T3.3 **M** `routers/reports.py` + `services/reports.py`: validation (genre vocab from `simulator/genres.py`, fallback copy), `distance_m`, 150 m presence, owner-own-venue block, rate limit, `status=pending`, points ledger + implicit bounty claim → `{report_id, ts, status, points_pending}`. BE-5.
- [ ] T3.4 **S** `routers/scouts.py` (leaderboard with `points_week`) + `routers/bounties.py` (open, not expired, `venue_name`). BE-6.
- [ ] T3.5 **M** `routers/recommend.py`: `/api/recommend` (sorted by `rank_score`; impression events) and `/api/plan-night` (v2 §F stop shape; `FEATURE_ROUTING`). BE-7/8.
- [ ] T3.6 **M** `routers/owner.py`: dashboard (v2 §G shape, `venue_events ∪ syn_venue_events`) + updates. BE-9/10.
- [ ] T3.7 **M** `routers/heatmap.py`: per-venue at `now` and `by=hour` (20–03), `FEATURE_HEATMAP`. BE-11.
- [ ] T3.8 **S** `routers/feedback.py`. BE-14.
- [ ] T3.9 **S** view/tap logging in the venue routers (no PII).
- [ ] T3.10 **S** push by **Fri Nov 13 18:00 ET**; tell master the branch is ready.

### Phase 4: hardening + docs (Nov 13–15)
- [ ] T4.1 **M** Contract-shape tests vs CONTRACTS v2 shapes; `INCLUDE_SYNTHETIC=0` sweep; midnight/replay tests; coverage ≥ 85%.
- [ ] T4.2 **S** `scripts/smoke.py BASE_URL` (every endpoint; non-zero exit on failure).
- [ ] T4.3 **S** `scripts/export_openapi.py` → `backend/openapi.json` for frontend TS types.
- [ ] T4.4 **S** One test run on Postgres (local container if Docker is available); record result.
- [ ] T4.5 **M** Docs: `backend/README.md`, `docs/workstreams/backend.md` (as-built, how to run, issues, CRs), `docs/synthetic/backend.md` (§4).
- [ ] T4.6 **S** Deploy dry-run with integration (Nov 15): `DEMO_NOW=2026-11-14T23:30:00-05:00`; smoke passes; hand URL to frontend.

## 2. File tree to create

```
backend/
  README.md
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  .env.example
  .dockerignore
  Dockerfile
  render.yaml                 # integration may move to repo root (v2 §C)
  alembic.ini
  openapi.json                # generated (T4.3)
  migrations/
    env.py
    versions/0001_initial.py
  app/
    __init__.py
    main.py                   # create_app, middleware, handlers
    config.py                 # Settings, v2 §A constants, PLACEHOLDER(specs) values
    timeutil.py               # parse_now, to_ny_iso
    logging.py
    db.py                     # engine, ATTACH pub + sim
    simdb.py                  # sim DB schema check
    models.py                 # real tables (twins of syn_)
    schemas.py                # Pydantic: CONTRACTS + v2 §F/§G shapes
    errors.py                 # error envelope
    deps.py                   # get_db, get_now, auth deps
    genres.py                 # imports simulator.genres.GENRES, fallback copy
    repo/
      __init__.py
      sources.py              # real ∪ syn_ unions, INCLUDE_SYNTHETIC
      venues.py  reports.py  updates.py  scouts.py  events.py  bounties.py  ledger.py
    services/
      auth.py
      reports.py              # validation, distance_m, presence, points, bounty claim
      venues.py               # card/detail assembly
      owner.py                # dashboard aggregation
    engine/
      __init__.py             # get_engine(), fallback
      base.py
      recs_engine.py
      stub.py
    routers/
      health.py  venues.py  heatmap.py  reports.py  scouts.py  bounties.py
      recommend.py  owner.py  auth.py  feedback.py
  scripts/
    start.sh
    ensure_sim.py
    load_manual_attributes.py
    smoke.py
    export_openapi.py
  tests/
    conftest.py
    fixtures/
      make_sim.py
      public_mini.sqlite.sql  # 5-venue public extract as SQL text
      golden.py               # G1, G5 inputs/outputs from specs
    test_health.py  test_venues.py  test_state.py  test_reports.py  test_auth.py
    test_scouts_bounties.py  test_recommend.py  test_plan_night.py  test_owner.py
    test_heatmap.py  test_feedback.py  test_replay.py  test_synthetic_toggle.py
    test_contract_shapes.py  test_migrations.py  test_golden.py  test_no_truth_tables.py
docs/workstreams/backend.md
docs/synthetic/backend.md
```

## 3. Interfaces

### Consumed
| From | Interface | Contract ref |
|---|---|---|
| existing | `data/manhattan_bars.db` (`v_bars`, `osm_venues`), read-only | Repository layout, Launch venues |
| existing | `data/launch_venues.csv` (header `license_id`, aliased to `venue_id`) | v2 §D |
| integration | `data/launch_venues_full.csv` (launch venues + OSM name/hours) | v2 §D |
| team | `data/venue_attributes_manual.csv` (optional override, `is_synthetic=0`) | v2 §D |
| live-sim | `data/live_sim.db`: `syn_venue_attributes`, `syn_scouts`, `syn_users`, `syn_scout_reports`, `syn_venue_updates`, `syn_feedback`, `syn_bounties`, `syn_venue_events`, `syn_disputes`, `syn_points_ledger`; CLI to generate it; `simulator/genres.py` | Data schemas, v2 §B/§E |
| ml-recs | `recs.live_state.compute / compute_all`, `recs.scoring.recommend`, `recs.routing.plan_night` (lists of dicts or DataFrames; reports carry `reputation`) | Python interface, v2 §F |
| specs | v2 §A constants, golden vectors G1/G5, point values | v2 §A |

### Provided
| To | Interface |
|---|---|
| frontend | HTTP API (CONTRACTS table + v2 §G), `GET /openapi.json` / `backend/openapi.json`, CORS, `is_synthetic` on every object, headers `X-Data`, `X-Total-Count`; `now=` forwarded from `VITE_DEMO_NOW` |
| integration | `scripts/start.sh`, `scripts/smoke.py`, Dockerfile, `backend/render.yaml`, env var table, deployed URL |
| tableau (later) | optional CSV export |

Endpoint → engine call map:
- `/venues`, `/venues/{id}`, `/state`, `/heatmap` → `live_state.compute_all` (or `compute`) at `now` (per hour for `by=hour`)
- `/recommend` → `compute_all` → `scoring.recommend(prefs, states, venues, now)`
- `/plan-night` → `compute_all` → `routing.plan_night(prefs, states, venues, start_time or now, n_stops)`

## 4. Synthetic datasets the backend uses

live-sim generates all of them into `data/live_sim.db` (v2 §D/§E). Backend reads them and lists
them in `docs/synthetic/backend.md`, pointing to live-sim's registry for generation details.

| Dataset | Imitates | Generated by | Real replacement | Swap steps |
|---|---|---|---|---|
| `syn_venue_attributes` | genres, style, dance floor, cover, capacity, price, claimed, hours | live-sim (seed 42) | `data/venue_attributes_manual.csv` now; owner-claimed profiles later | fill the manual CSV (overrides per venue automatically); later write owner profile edits to `venue_attributes` |
| `syn_scouts` | scout profiles, reputation, activity | live-sim | real `scouts` (demo-login / sign-up) | `INCLUDE_SYNTHETIC=0` |
| `syn_users` | group members and prefs | live-sim | real `users` | `INCLUDE_SYNTHETIC=0` |
| `syn_scout_reports` | vibe checks, Thu–Sat Sep 3 → Nov 14 | live-sim | real `scout_reports` from `POST /api/reports` | `INCLUDE_SYNTHETIC=0`; same columns, nothing else changes |
| `syn_venue_updates` | operator posts, offers | live-sim | real `venue_updates` from owner endpoint | same |
| `syn_bounties` | open bounties | live-sim | real `bounties` (rule-based creation job or owners, later) | add creation job; flag off |
| `syn_points_ledger` | points history | live-sim | real `points_ledger` written by `POST /api/reports` | flag off |
| `syn_venue_events` | dashboard views/taps/saves/impressions | live-sim | real `venue_events` logged by the API | flag off; dashboard reads only real events |
| `syn_feedback` | post-visit outcomes | live-sim | real `feedback` from `POST /api/feedback` | flag off |
| `syn_disputes` | report disputes | live-sim | real disputes table (later) | not read by MVP endpoints; registered only |
| test fixture sim DB | a tiny one-night `live_sim.db` | `backend/tests/fixtures/make_sim.py` (seed 42) | real `live_sim.db` (tests only), then real tables | test-only; also the boot fallback if `live_sim.db` can't be generated |

Never read: `syn_true_state`, `syn_scout_truth` (evaluation-only). Every read site is marked
`# SYNTHETIC: ...`; all rows `is_synthetic=1`, IDs `syn-…`.

## 5. Test plan

| Layer | What | Tool |
|---|---|---|
| Unit | `parse_now` (offsets, Z, naive rejected), haversine/`distance_m`, display-name cleanup, stub scoring (cutoff, exclusions, null handling, unknown 0.4), points | pytest |
| Golden | G1 (vibe 65 / conf 0.67), G5 (match 83) through the stub; and through `recs` if importable | `test_golden.py` |
| Repo | unions with/without synthetic, `now` filter, manual-attribute override, pagination | temp app DB + fixture sim DB |
| API | every endpoint happy path + each AC (401/403/404/422/429; owner can't report own venue) | TestClient |
| Contract | keys/types match CONTRACTS + v2 §F/§G shapes; `is_synthetic` everywhere; `X-Data` on lists | `test_contract_shapes.py` (integration's `tests/contract/` also runs at merge) |
| Engine | stub always; real recs if importable; recs raising → stub fallback, `/health` still truthful | pytest |
| Migration | `alembic upgrade head` on empty DB; downgrade base | pytest |
| Sim DB | schema check catches a missing column; missing DB → fixture fallback | pytest |
| Safety | no `syn_true_state`/`syn_scout_truth` strings in `backend/app/`; no raw lat/lon columns | `test_no_truth_tables.py` |
| Public DB smoke | real DB → 35 launch + 1,727 bars | `@pytest.mark.publicdb` |
| Deployed | `scripts/smoke.py https://<render-url>` | manual + integration |
| Postgres | full suite once on Postgres | local container |

Commands: `cd backend && pytest -q --cov=app` · `ruff check . && ruff format --check .`

## 6. Demo script (≈4 min, Nov 17)

Setup: Render with `DEMO_NOW=2026-11-14T23:30:00-05:00`, real `live_sim.db`. Warm it 2 min before.
1. `GET /api/health` → `{ok: true, recs: "real", data: "synthetic", demo_now: "2026-11-14T23:30:00-05:00"}`. Show `/api/docs`.
2. `GET /api/venues` → 35 LES cards at 23:30 Saturday; point out the `display` bands (show / low / none) and `is_synthetic`.
3. `GET /api/heatmap?by=hour` → vibe building 20:00 → 23:00 along Ludlow/Orchard.
4. `POST /api/recommend` with the contract's example prefs → ranked by `rank_score` with reasons and `missing`; one venue excluded with `excluded_reason` (cover over $20). Point at `complaint_risk` labelled "311 noise-complaint risk".
5. Demo-login as scout → `POST /api/reports` (crowd 5, dancing 2, line 20, lat/lon at the door) → `{status: "pending", points_pending: …}`; `GET /state` shows `n_reports` +1 and confidence up; bounty gone from `/api/bounties`; scout on `/leaderboard`.
6. `POST /api/plan-night` `n_stops=3` → route with walk minutes and expected vibe.
7. Demo-login as owner of the same venue → `POST /updates` with an offer → shows in venue detail `offers`; `GET /dashboard` shows `demand_by_hour`, `is_synthetic: true`. Try reporting own venue → 403.
8. Close: a local instance with `INCLUDE_SYNTHETIC=0` → same API; health says `data: "real"`; only the step-5 report remains. That's the swap path.

## 7. Deploy steps (Ryan supplies accounts)

Ryan provides: a Render account connected to GitHub `ryanmmehta/manhattan-bars-ml`; integration
provides the Vercel URL. No paid APIs.
1. Render → New → Blueprint → repo, branch `nightlife/backend` (integration later switches to the merged branch), Blueprint path `backend/render.yaml` (or root copy, v2 §C).
2. `render.yaml` (to write): one `web` service, `runtime: docker`, `dockerfilePath: backend/Dockerfile`, `dockerContext: .`, `healthCheckPath: /api/health`, plan `free` (placeholder; Starter for a disk). Env: `DEMO_NOW=2026-11-14T23:30:00-05:00`, `INCLUDE_SYNTHETIC=1`, `GENERATE_SIM_ON_START=1`, `DEMO_AUTH=1`, `RECS_MODE=auto`, `FEATURE_ROUTING=1`, `FEATURE_HEATMAP=1`, `CORS_ORIGINS=<vercel url>,http://localhost:5173`, `ADMIN_TOKEN` (`generateValue: true`).
3. Generate `live_sim.db` in the Docker build if live-sim's CLI is fast enough; otherwise at boot (open question 3).
4. Deploy; wait for the health check; `python backend/scripts/smoke.py https://<service>.onrender.com`.
5. Free-tier caveats (check Render's current limits at deploy time): sleeps when idle; ephemeral disk, so app-DB writes reset on restart.
6. Postgres later: create Render Postgres, set `DATABASE_URL=postgresql+psycopg://...`; `start.sh` runs migrations then `ensure_sim.py --copy-to-db` (CR-12).

## 8. Assumptions recorded
- live-sim ships a CLI that writes `data/live_sim.db` deterministically and fast enough for build/boot (to confirm).
- Pending reports count in live state; flagged/removed don't.
- Neighborhood for all launch venues is `LES/Chinatown` (`venues.neighborhood`).
- Docker build context is the repo root so `data/` and `simulator/` are available.
- Point values: base 10, verified bonus 5 (placeholders until specs).
