# PRD: backend (Nightlife Autopilot API)

Workstream: `backend` · Branch: `nightlife/backend` · Folder: `backend/`
Status: planning (Nov 11, 2026). No code yet.
Governing contract: [`docs/CONTRACTS.md`](../../CONTRACTS.md). Where this PRD and
the contract disagree, the contract wins until a change request below is accepted.

## 1. Problem

Nightlife Autopilot needs one service that every other piece talks to. Right now
there is a public-data SQLite DB (`data/manhattan_bars.db`), and plans for a
synthetic live-data simulator (`live-sim`), a scoring package (`ml-recs`) and a
React app (`frontend`). Nothing connects them, nothing is deployed, and the
course's Nov 17 milestone is "working model, deployed". The Oct 13 "deployed team
skeleton" milestone was also never met, so the first backend task is a live
`/api/health` on a public URL.

The backend has to:
- serve venue profiles from the real public data, joined with synthetic live data
  that is clearly labelled and easy to swap for real data later;
- accept writes (scout vibe checks, owner updates) so the demo feels live;
- call `recs/` for live state, recommendations and routing, and keep working
  (with a simple stub) if `recs/` isn't ready;
- run locally with one command and on Render with one `render.yaml`.

## 2. Goals

1. Implement **every endpoint in the CONTRACTS.md HTTP API table**, with the
   contract's JSON shapes, under `/api`.
2. One schema, defined in SQLAlchemy 2.0 with Alembic migrations, that runs on
   SQLite now and on Postgres by changing `DATABASE_URL` only.
3. Load the 35 launch venues (and optionally all 1,727 `v_bars`) from the public
   DB, plus every `syn_` table from `data/synthetic_live/`, with one seed command.
4. Import `recs/` through a single adapter; fall back to a built-in stub with the
   same signatures when `recs/` is missing or raises.
5. Simple auth: anyone can read; scouts and owners need a token to write.
6. `now=<ISO>` replay on every read endpoint so the class demo can play a
   simulated Saturday night.
7. pytest suite that covers every endpoint; runs in under 30 s.
8. Dockerfile + `render.yaml`; deploy steps Ryan can follow once he has a Render
   account.

## 3. Non-goals (this phase)

- Real user accounts, passwords, OAuth, email verification, payments.
- Real-time push (websockets/SSE). The frontend polls (suggest every 60 s).
- Any scoring logic beyond the stub. Scoring belongs to `ml-recs`; formulas to `specs`.
- Generating the main synthetic live datasets (that's `live-sim`). Backend only
  generates the small datasets it alone needs (see §8) and only if live-sim doesn't.
- Editing `src/`, `data/manhattan_bars.db`, or any folder another workstream owns.
- Production hardening (rate limiting beyond a basic per-token cap, audit logs, backups).
- Moderation/dispute workflows for scout reports (specs defines them; later).

## 4. Users and clients

| Client | Who | What they need from the API |
|---|---|---|
| Frontend app (consumer mode) | groups deciding where to go | venue cards, profile, live state, `/recommend`, `/plan-night`, `/heatmap` |
| Frontend app (Scout mode) | Scouts doing a 10-second vibe check | `POST /reports`, leaderboard, bounties, their own points |
| Frontend app (owner mode) | venue operators with a claimed profile | dashboard, `POST /owner/{id}/updates` |
| Tableau workstream | analysts | not the API — reads CSV extracts; backend offers an optional `GET /api/export/*.csv` later |
| Integration workstream | demo runner | seed command, `now=` replay, health check, deployed URL |
| Ryan (owner) | deployer | env var list, Render steps, who-supplies-what checklist |

## 5. User stories and acceptance criteria

IDs are `BE-n`. "AC" = acceptance criteria; each AC maps to at least one pytest test.

**BE-1 Health / skeleton.** As the team, I need a deployed URL that answers so we
know the pipeline works.
- AC: `GET /api/health` → `200 {"ok": true}` locally and on Render.
- AC: response includes header `X-Recs-Engine: recs|stub` and `X-Data-Mode: synthetic|real`.

**BE-2 Browse venues.** As a group, I want to list launch venues with their current vibe.
- AC: `GET /api/venues` with default `launch_only=true` returns exactly the 35
  venues in `data/launch_venues.csv`.
- AC: `q` matches display name or address, case-insensitive, substring.
- AC: `style`, `genre`, `neighborhood` filter using `syn_venue_attributes` /
  `venues.neighborhood`; unknown values return `[]`, not 400.
- AC: each card has profile fields + a `live` object in Live Venue State shape;
  venues with no fresh reports have `vibe_score: null`, `confidence: 0`, never a default number.
- AC: `launch_only=false` returns the `v_bars` set (1,727) with `limit`/`offset`
  (default limit 50, max 200). *(pagination = change request CR-3)*
- AC: p95 latency < 300 ms locally for the 35-venue list (placeholder target).

**BE-3 Venue profile.** As a group, I want details on one venue.
- AC: `GET /api/venues/{venue_id}` returns profile, `live`, the last 10 reports
  (newest first, scout display name + reputation, no user ids beyond scout_id),
  and active offers (from venue updates whose `offer_expires_at > now`).
- AC: unknown id → `404` with the error envelope (CR-1).

**BE-4 Live state.** `GET /api/venues/{id}/state` returns exactly the Live Venue
State JSON, computed at `now` (query param or server time), via `recs.live_state.compute`.
- AC: with `now` set before any report that night, `n_reports = 0`, `freshness_minutes = null`.
- AC: `is_synthetic` is `true` whenever any contributing report/update is synthetic.

**BE-5 Scout vibe check.** As a Scout, I submit crowd/dancing/line (+ optional cover, music) in ≤10 s.
- AC: `POST /api/reports` with a valid scout token and body
  `{venue_id, crowd, dancing, line_minutes, cover_usd?, music_genre?, lat?, lon?}`
  → `201` with the stored report (server sets `report_id` UUID4 string, `ts` now in
  America/New_York, `scout_id` from token, `is_synthetic: 0`).
- AC: `verified_presence = 1` only if lat/lon is within 100 m (placeholder; specs
  owns the real threshold) of the venue; otherwise 0. *(lat/lon in body = CR-4)*
- AC: validation: crowd 1–5, dancing 0–2, line 0–180, cover 0–200 → else `422`.
- AC: rate limit: same scout + same venue at most once per 15 min (placeholder) → `429`.
- AC: the next `GET /venues/{id}/state` reflects the new report.
- AC: scout gets points (placeholder +10, +5 bonus if verified, + bounty points if
  an open bounty for the venue exists → bounty marked claimed). Points rules come from specs.

**BE-6 Leaderboard and bounties.**
- AC: `GET /api/scouts/leaderboard?limit=20` → `[{rank, scout_id, display_name, points, level, reputation, reports_count}]` sorted by points desc. *(shape = CR-5)*
- AC: `GET /api/bounties` → open bounties (`claimed_by IS NULL`) with venue name, points, reason, created_at.

**BE-7 Recommend.** As a group, I post my preferences and get ranked venues with reasons.
- AC: `POST /api/recommend` with a Preferences body → list of Recommendation results
  from `recs.scoring.recommend`, sorted by `match_score` desc, excluded venues last
  with `excluded: true`.
- AC: missing optional pref fields are allowed; invalid ranges → `422`.
- AC: works with the stub engine (stub ranks by distance + vibe, fills `reasons`
  honestly, e.g. "Ranked by distance only (scoring engine offline)").

**BE-8 Run My Night.** `POST /api/plan-night` (Preferences + `n_stops`, default 3,
max 5) → ordered stops from `recs.routing.plan_night`.
- AC: each stop has `{order, venue_id, name, arrive_at, leave_at, walk_minutes_from_prev, reasons}` *(shape = CR-6)*.
- AC: stub: greedy nearest-next among top-N recommended, 60 min per stop.

**BE-9 Owner dashboard.** As an operator, I see demand for my venue.
- AC: `GET /api/owner/{venue_id}/dashboard` with that venue's owner token → `200`
  `{venue_id, period, views, taps, saves, reports, recommend_impressions, demand_by_hour:[{hour, value}], is_synthetic}`.
  Wrong/missing token → `401/403`.
- AC: real counts come from `app_events` (logged by the API itself); synthetic
  baseline from `syn_venue_events`; response says `is_synthetic: true` while any synthetic rows are included.

**BE-10 Owner update.** `POST /api/owner/{venue_id}/updates` with owner token,
body `{cover_usd?, dj?, genres?, event?, offer?, offer_expires_at?}` → `201`;
appears in venue profile offers and in the next live-state computation.

**BE-11 Heatmap.** `GET /api/heatmap` → `[{venue_id, lat, lon, vibe_score, confidence}]`
for launch venues at `now`. Null vibe stays null.

**BE-12 Replay.** As the demo runner, I pass `now=2026-11-14T23:30:00-05:00` to any
read endpoint and see the night as of that moment.
- AC: reports/updates with `ts > now` are ignored; offers are active relative to `now`.
- AC: `DEMO_NOW` env var sets a default `now` for the whole deployment (so the
  frontend doesn't have to pass it).

**BE-13 Demo login.** As a tester, I can get a scout or owner token without signup.
- AC: `POST /api/auth/demo-login {role: "scout"|"owner", scout_id?|venue_id?}` → `{token, role, subject_id}`; enabled only when `DEMO_AUTH=1`. *(new endpoint = CR-2)*

## 6. Scope

**MVP (by Nov 17)**: BE-1 … BE-13; SQLite; seeded from public DB + `data/synthetic_live/`;
recs adapter + stub; Docker; Render deploy; pytest green.

**Later**: Postgres on Render; availability heatmap by hour (`/api/heatmap?hour=`);
group compatibility score endpoint; per-user saved prefs (`syn_users` → real users);
`POST /api/feedback`; bounty creation by owners; report disputes; CSV export
endpoints for Tableau; SSE live updates; real auth (magic link).

## 7. Requirements

### Functional
- F1. All CONTRACTS.md endpoints, paths and JSON field names exactly as written.
- F2. Read endpoints accept `now`; write endpoints ignore it and use server time
  (unless `ALLOW_WRITE_NOW=1` in tests/demo seeding).
- F3. Reads merge real-app tables and `syn_` tables (e.g. `scout_reports` ∪
  `syn_scout_reports`). A single env var `INCLUDE_SYNTHETIC=1|0` turns synthetic rows off.
- F4. Missing data is `null`, never a favourable default (contract rule).
- F5. All synthetic-derived responses carry `is_synthetic: true` at the object level.
- F6. venue display name: OSM `osm_venues.name` when matched, else title-cased SLA
  `name` with LLC/INC/CORP stripped. All 35 launch venues have an `osm_id`.

### Non-functional
- N1. Python 3.12+ (container uses 3.12; dev box has 3.13), FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2.
- N2. Cold start on Render < 60 s including seeding (placeholder; seed is ~35 venues + ~20k synthetic rows).
- N3. p95 < 300 ms for list/state endpoints on 35 venues; `/recommend` < 800 ms (placeholders).
- N4. CORS allows the frontend origins from `CORS_ORIGINS` (comma list); default `http://localhost:5173`.
- N5. No secrets in the repo. Tokens are random 32-byte URL-safe strings, stored as SHA-256 hashes.
- N6. Structured JSON logs to stdout; every request logs method, path, status, ms, engine.
- N7. OpenAPI docs at `/api/docs` (FastAPI default moved under `/api`).

## 8. Data the backend owns

| Table | Real or synthetic | Source |
|---|---|---|
| `venues` | real (public) | copied from `manhattan_bars.db` `v_bars` + `osm_venues.name`; `is_launch` flag from `launch_venues.csv` |
| `scout_reports` | real app writes (`is_synthetic=0`) | `POST /api/reports` |
| `venue_updates` | real app writes | `POST /api/owner/{id}/updates` |
| `scouts` | real app rows | created on demo-login / first report |
| `api_tokens` | real app rows | demo-login, seed |
| `app_events` | real app rows | middleware logs view/tap/impression |
| `syn_venue_attributes`, `syn_scouts`, `syn_users`, `syn_scout_reports`, `syn_venue_updates`, `syn_feedback`, `syn_bounties` | synthetic | loaded from `data/synthetic_live/*.csv` (live-sim) |
| `syn_venue_events` | synthetic | backend-generated only if live-sim doesn't provide it (CR-7) |
| `syn_owner_claims` | synthetic | backend-generated: which demo owner token owns which venue |

Real-app tables and `syn_` tables share column names so a swap is a `UNION ALL` removal.

## 9. Dependencies on other workstreams

| Workstream | Backend needs from it | By | If late |
|---|---|---|---|
| **specs** | decay half-life, reputation weighting, verified-presence radius, points rules, rate limits, confidence display threshold | Nov 13 | use placeholders in `backend/app/config.py`, marked `# PLACEHOLDER(specs)` |
| **research** | nothing at runtime; interview findings may change MVP priorities | — | — |
| **tableau** | nothing; backend may expose CSV export later | — | — |
| **live-sim** | `data/synthetic_live/*.csv` matching the contract schemas, one Thu–Sat night min, seed fixed | Nov 14 | backend ships a tiny fixture generator (`backend/seed/fixtures.py`, ~200 reports) so tests and deploy don't block |
| **ml-recs** | importable `recs` package with the 4 contract functions | Nov 14 | stub engine in `backend/app/engine/stub.py` |
| **backend** | (self) | | |
| **frontend** | consumes the API; needs deployed URL + CORS origin + response shapes for change requests | URL by Nov 14 | frontend mock-API mode |
| **coursework** | none | — | — |
| **integration** | merges branches, runs seed, deploys Render + Vercel, end-to-end tests | Nov 15–17 | backend provides `make demo` and a smoke-test script |

## 10. Success metrics

- All 12 contract endpoints + demo-login return 2xx on the deployed URL (smoke script passes).
- pytest: 100% of endpoints covered, ≥ 85% line coverage on `backend/app/` (placeholder target).
- Zero contract-shape mismatches found by the frontend at integration (target 0; measured as bugs filed Nov 15–17).
- Swap test: setting `INCLUDE_SYNTHETIC=0` returns only real rows and no endpoint 500s.
- Demo: a 5-minute replay of a simulated Saturday runs without manual DB edits.
- Render cold start < 60 s; warm p95 within N3.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Render free tier sleeps / ephemeral disk wipes SQLite | high | demo writes vanish on restart | reseed on boot (`SEED_ON_START=1`); writes are demo-only; Postgres later. Hit `/api/health` 2 min before class |
| `recs` interface drifts from contract | med | 500s | adapter validates outputs with Pydantic; falls back to stub per-call and logs |
| live-sim CSV columns differ from contract | med | seed fails | loader validates columns, reports exact mismatch; fixtures fallback |
| 40 MB public DB in Docker image | low | slow builds | seed extracts only needed rows; image copies DB once; consider derived `venues` CSV (CR-8) |
| SQLite vs Postgres differences (datetime, UPSERT) | med | bugs at migration | store ts as ISO text + UTC column; use SQLAlchemy constructs only; CI job against Postgres later |
| Timezone bugs in `now` replay | high | wrong live state | single helper `parse_now()`; all comparisons in UTC; tests across midnight + DST (Nov 1, 2026 already passed) |
| Demo tokens abused on public URL | low | junk reports | `DEMO_AUTH` can be turned off; per-token rate limit; `ADMIN_TOKEN` reset endpoint |
| Late start (Oct 13 skeleton missed; 6 days left) | high | incomplete | build order puts deploy first, stub second, full endpoints third |

## 12. Open questions

1. Does Ryan already have a Render account (and GitHub connected)? Free or Starter plan (Starter allows a persistent disk)?
2. Frontend host confirmed as Vercel? Need the production origin for `CORS_ORIGINS`.
3. Should `/api/venues` include all 1,727 `v_bars` at launch or only the 35? (Plan: 35 by default, others via `launch_only=false`, mostly with null live state.)
4. Who sets points/levels rules — specs or backend? (Plan: specs; backend uses placeholders.)
5. Is anonymous reporting allowed (no token)? (Plan: no; demo-login is one tap.)
6. Should complaint risk (`noise_complaints`) be shown on venue profiles? It's real public data but ≠ quality; plan: include as `complaint_risk` with a label field, frontend decides.
7. Will integration run Postgres for the Nov 17 demo or stay on SQLite? (Plan: SQLite.)

## 13. Contract change requests

CONTRACTS.md says to file these in `docs/workstreams/backend.md`; this brief puts
them here. Integration should copy them over. None of these are applied on this branch.

- **CR-1 Error envelope.** All non-2xx: `{"error": {"code": "not_found", "message": "...", "details": {}}}`. FastAPI 422s reshaped to the same envelope.
- **CR-2 Auth.** Add `POST /api/auth/demo-login` (see BE-13). Writes use `Authorization: Bearer <token>`.
- **CR-3 Pagination.** `limit` (default 50, max 200) and `offset` on `/api/venues`; response stays a bare list, with `X-Total-Count` header.
- **CR-4 Report body.** Add optional `lat`, `lon` to `POST /api/reports` (not stored; used to set `verified_presence`). Client never sends `verified_presence`, `scout_id`, `ts`, `report_id`.
- **CR-5 Response shapes not in contract.** Define venue card, leaderboard row, bounty row, dashboard and plan-night stop as in BE-2/6/8/9 (backend will publish them as Pydantic models + OpenAPI).
- **CR-6 Plan-night stop shape** (BE-8).
- **CR-7 `syn_venue_events`** table: `event_id, venue_id, ts, event_type (view|tap|save|recommend_impression), user_id (nullable), is_synthetic` — ask live-sim to generate it; else backend generates.
- **CR-8 Optional derived file** `data/launch_venues_full.csv` (launch venues + OSM name/hours) so the backend image doesn't need the 40 MB DB. Owner: existing/integration.
- **CR-10 render.yaml location.** Backend writes `backend/render.yaml`; integration moves/merges it to the repo root if the Render Blueprint needs it there (frontend is on Vercel, so it holds only the API service).
- **CR-9 Bounty claim.** Bounties are claimed implicitly by the first qualifying report; no separate claim endpoint in MVP. Confirm.
