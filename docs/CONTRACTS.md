# Nightlife Autopilot — shared build contracts

Every workstream builds against this file so the pieces fit together at
integration (Nov 17). If you need to change a contract, write the change in
your workstream's `docs/workstreams/<name>.md` under "Contract change requests";
don't edit this file on your branch.

## Product in one line
Help a group choose where to go *right now* by matching their preferences with
fresh information about nearby nightlife venues. Launch area: Manhattan's Lower
East Side (zip 10002).

## Repository layout (one owner per folder)

| Folder | Owner workstream | Contents |
|---|---|---|
| `src/` (existing), `data/manhattan_bars.db` | existing | public-data pipeline, venue DB, complaint-risk models — do not break |
| `docs/specs/` | specs | architecture, requirements, scoring/freshness/credibility rules |
| `research/` | research | competitor refresh, interview guide, synthetic interview data |
| `analytics/tableau/` | tableau | CSV extracts, dashboard image, Tableau build steps |
| `simulator/`, `data/synthetic_live/` | live-sim | time-based simulator of scouts, reports, venue updates, users |
| `recs/` | ml-recs | Python package: live state, scoring, crowd model, clustering, routing |
| `backend/` | backend | FastAPI app, DB schema/migrations, deploy config |
| `frontend/` | frontend | React (Vite + TypeScript) app and design mockups |
| `coursework/` | coursework | individual exercises (tiny transformer, churn model) |
| `docs/workstreams/<name>.md` | each workstream | what was built, how to run it, open issues |
| `docs/synthetic/<name>.md` | each workstream | registry of every synthetic/placeholder dataset it created |

## Launch venues
`data/launch_venues.csv` — 35 LES bars/clubs from `v_bars` (zip 10002,
venue_type Bar/Tavern or Club, OSM-matched first). `venue_id` everywhere means
the SLA `license_id` (e.g. `0370-24-138636`).

## Synthetic data rule (mandatory)
We have no real live data yet. Anything not from the public pipeline is synthetic
and must be easy to find and replace:
1. Every synthetic table/CSV has a column `is_synthetic` (1 = synthetic).
2. Synthetic files live under a path containing `synthetic` (e.g.
   `data/synthetic_live/`), and synthetic DB tables are prefixed `syn_`.
3. Code that uses synthetic data marks the spot with a comment
   `# SYNTHETIC: <what real source replaces this>` (or `// SYNTHETIC:` in TS).
4. Each workstream lists every synthetic dataset in `docs/synthetic/<name>.md`
   with: file/table, what it imitates, how it was generated, the real source that
   should replace it, and the steps to swap it.
5. The UI shows a small "demo data" badge wherever synthetic data is displayed.

## Data schemas (CSV columns = SQLite columns)

`syn_venue_attributes` (static venue facts the public data lacks)
- venue_id, genres (pipe-separated, e.g. `hip-hop|r&b`), style
  (dive|cocktail|club|lounge|pub|restaurant-bar), has_dance_floor (0/1),
  typical_cover_usd, capacity, price_level (1-4), is_synthetic

`syn_scouts`
- scout_id, display_name, joined_at, reputation (0-1), points, level,
  reports_count, is_synthetic

`syn_users`
- user_id, display_name, home_lat, home_lon, prefs_json (see Preferences), is_synthetic

`syn_scout_reports` (the 10-second vibe check)
- report_id, venue_id, scout_id, ts (ISO 8601, America/New_York),
  crowd (1-5), dancing (0 none / 1 some / 2 lots), line_minutes (int),
  cover_usd (nullable), music_genre (nullable), verified_presence (0/1),
  is_synthetic

`syn_venue_updates` (official operator posts)
- update_id, venue_id, ts, cover_usd, dj (nullable), genres, event (nullable),
  offer (nullable), offer_expires_at (nullable), is_synthetic

`syn_feedback` (post-visit outcome)
- feedback_id, user_id, venue_id, recommended_at, visited (0/1),
  rating (1-5, nullable), is_synthetic

`syn_bounties`
- bounty_id, venue_id, created_at, points, reason, claimed_by (nullable), is_synthetic

## Preferences (request body / prefs_json)
```json
{
  "genres": ["hip-hop", "r&b"],
  "want_dancing": true,
  "crowd_pref": 4,
  "max_cover_usd": 20,
  "max_line_minutes": 15,
  "max_distance_km": 1.5,
  "lat": 40.7203, "lon": -73.9881,
  "group_size": 4
}
```

## Live Venue State (computed, never stored as truth)
```json
{
  "venue_id": "0370-24-138636",
  "crowd": 3.8, "dancing": 1.4, "line_minutes": 10, "cover_usd": 15,
  "music_genres": ["hip-hop"],
  "vibe_score": 78,
  "confidence": 0.71,
  "freshness_minutes": 12,
  "n_reports": 4,
  "trend": "rising",
  "sources": ["scout", "venue_update"],
  "is_synthetic": true
}
```
Rules: older reports count less (exponential decay; half-life set in
`docs/specs/`); reporter reputation weights each report; missing fields are
`null` — never filled with a favourable default; `confidence` is separate from
`vibe_score`.

## Recommendation result
```json
{
  "venue_id": "...", "name": "...",
  "match_score": 91, "vibe_score": 78, "confidence": 0.71,
  "distance_km": 0.4,
  "reasons": ["Hip-hop playing (2 reports, 12 min ago)", "Line ~10 min, under your 15"],
  "missing": ["cover not reported tonight"],
  "excluded": false
}
```

## Python interface (`recs/`, imported by the backend)
```python
from recs import live_state, scoring, routing
live_state.compute(venue_id, reports, updates, now) -> dict          # Live Venue State
live_state.compute_all(reports_df, updates_df, now) -> list[dict]
scoring.recommend(prefs: dict, states: list[dict], venues: list[dict], now) -> list[dict]
routing.plan_night(prefs, states, venues, start_time, n_stops=3) -> list[dict]
```

## HTTP API (`backend/`, FastAPI, JSON, base path `/api`)
| Method | Path | Returns |
|---|---|---|
| GET | `/api/health` | `{"ok": true}` |
| GET | `/api/venues?q=&neighborhood=&style=&genre=&launch_only=true` | list of venue cards (profile + live state) |
| GET | `/api/venues/{venue_id}` | profile + live state + recent reports + offers |
| GET | `/api/venues/{venue_id}/state` | Live Venue State |
| POST | `/api/reports` | create a scout report (schema above, server sets ts/report_id) |
| POST | `/api/recommend` | body: Preferences → list of Recommendation results |
| POST | `/api/plan-night` | body: Preferences + `n_stops` → ordered stops |
| GET | `/api/scouts/leaderboard` | top scouts |
| GET | `/api/bounties` | open bounties |
| GET | `/api/owner/{venue_id}/dashboard` | views, taps, reports, demand (synthetic for now) |
| POST | `/api/owner/{venue_id}/updates` | create a venue update |
| GET | `/api/heatmap` | `[{venue_id, lat, lon, vibe_score, confidence}]` |

Query param `now=<ISO>` on read endpoints lets the demo replay a simulated night.

## Branches
Each workstream works on `nightlife/<name>` branched from `nightlife/contracts`,
pushes it, and does not open PRs or push to `main`. Integration merges them.

---

# v2 amendments (Nov 11, master) — these override anything above

Resolved from every workstream's "Contract change requests". Where two plans
disagreed, the decision is stated here; follow it.

## A. Canonical constants (owned by specs; all are placeholders until pilot data)
| Constant | Value | Note |
|---|---|---|
| Half-life crowd/dancing/line | 30 min | ml-recs' 45 min placeholder is replaced |
| Half-life scout cover/genre | 60 min | |
| Half-life operator cover/genres/dj | 120 min; offers until `offer_expires_at` | |
| Input cutoff | 180 min old, or ts > now+2 min | |
| Reputation weight | `w_rep = 0.25 + 0.75·r`, new scouts r = 0.5 | |
| Unverified presence weight | 0.6 | |
| Confidence k | 1.5 | |
| Display threshold | conf ≥ 0.40 show; 0.20–0.39 greyed "low confidence"; < 0.20 or vibe null → "No fresh reports" | ml-recs' 0.35 is replaced |
| Unknown match component | scores 0.4 and adds a `missing` entry | |
| Presence radius | 150 m (store distance_m only, never raw GPS) | backend's 100 m is replaced |
| Rank | `rank_score = match_score · (0.75 + 0.25·confidence)` | |
| Trend | `rising` / `steady` / `falling` / `null` (Δ ±0.4, 30 vs 30–90 min windows) | |
Full formulas: `docs/prd/specs/PRD.md` §5–7 (built version moves to `docs/specs/SCORING.md`).
Golden vectors G1 (vibe 65 / conf 0.67) and G5 (match 83) are the shared unit tests for ml-recs and backend.

## B. Demo time and data window
- Simulated history: Thu–Sat nights from **Thu Aug 27 → Sat Nov 14, 2026** (12 weeks,
  36 nights), seed 42, 20:00–03:00 ET. Detailed reports for all nights. This gives
  coursework ≥ 10 weeks for churn and ml-recs ≥ 8 nights for a temporal holdout
  (hold out the last 2 nights: Nov 13–14)
- Scout churn label (coursework): no report in 21 days; ~150 scouts in weekly cohorts.
- Scouts follow an engagement process with drop-off (latent engagement decays; bounties/rewards bump it).
- **DEMO_NOW = 2026-11-14T23:30:00-05:00** for every workstream (tableau's "tonight"
  heatmap uses Sat Nov 14 20:00–03:00). The class demo replays this moment.
- Frontend: env `VITE_DEMO_NOW` and URL `?now=` are forwarded as API `now=`.

## C. Folder ownership additions
- `docs/prd/<name>/` = plans (each workstream); `docs/workstreams/<name>.md` = as-built notes. Both kept.
- specs: `docs/specs/` for built specs; drafts `docs/specs/team/` (PR template, CONTRIBUTING), integration copies to `.github/` and root.
- integration owns: `tests/e2e/`, `tests/contract/`, `scripts/`, `Makefile`, `.github/`,
  root `README.md`, `SYNTHETIC_DATA.md`, `DEMO.md`, `CONTRIBUTING.md`, root `render.yaml`.
- backend writes `backend/render.yaml`; integration moves it to root if needed.
- tableau may use `analytics/tableau/extracts/synthetic/`.

## D. IDs and data files
- `data/launch_venues.csv` keeps header `license_id`; loaders alias `license_id AS venue_id`.
- Synthetic primary keys start with `syn-` (e.g. `syn-r-000123`, `syn-s-0042`).
- Synthetic tables are loaded into a separate **`data/live_sim.db`** (not into
  `manhattan_bars.db`); backend attaches both. Generated `.db` files are not committed;
  the generator is deterministic (seed 42). integration produces `data/launch_venues_full.csv`
  (launch venues + OSM name/hours) so deploys don't need the 39 MB DB.
- Hand-labelled venue attributes: if the team fills `data/venue_attributes_manual.csv`
  (same columns as `syn_venue_attributes`, `is_synthetic=0`), it overrides synthetic rows.
- Launch venues are all Bar/Tavern (the two LES "Club" licences are not nightclubs). Dancing
  signal comes from `syn_venue_attributes.has_dance_floor`; expect it to be sparse.

## E. Schema additions (live-sim generates unless noted)
- `syn_scout_reports` + `status` (pending|accepted|flagged|disputed|removed), `distance_m` (nullable int).
- `syn_scouts` + `last_active_at` (nullable), `archetype` NOT here (see truth tables).
- `syn_venue_attributes` + `is_claimed` (0/1), `opening_hours` (nullable, from OSM when present).
- `syn_bounties` + `expires_at`, `claimed_at` (nullable). Claimed implicitly by the first qualifying report; no claim endpoint in MVP.
- New `syn_venue_events`: event_id, venue_id, ts, event_type (view|tap|save|recommend_impression), user_id (nullable), is_synthetic. (Owner-dashboard demand is aggregated from this; `syn_venue_demand` is dropped.)
- New `syn_disputes`: dispute_id, report_id, opened_by, reason, opened_at, status, resolved_at, is_synthetic.
- New `syn_points_ledger`: entry_id, scout_id, report_id, bounty_id, points, reason, ts, is_synthetic.
- **Evaluation-only** (never read by the app or API, never used as model features):
  `syn_true_state` (venue_id, ts 15-min slots, crowd_true, dancing_true, line_minutes_true,
  cover_usd_true, genre_true, occupancy, is_synthetic) — replaces specs' `syn_venue_truth`;
  `syn_scout_truth` (scout_id, archetype honest|casual|sloppy|gamer|shill, home_venue_id, true_accuracy, cohort_week, churned_at, is_synthetic).
- research (own folder, not in the DB): `syn_interviews`, `syn_interview_quotes`, `syn_survey_responses`.
- Shared genre vocabulary (17 slugs, owned by live-sim at `simulator/config/genres.json`): `hip-hop, r&b, afrobeats, latin, reggaeton, house, techno, edm, disco, pop, top-40, throwbacks, indie, rock, punk, jazz, soul-funk`.
- `syn_scout_reputation_history` (scout_id, as_of_date, reputation, points, level, is_synthetic): models and evaluation must join reputation **as of the report date** — joining the final `syn_scouts.reputation` to past reports leaks the future. The live app uses current reputation.
- Real app tables mirror their `syn_` twins without the prefix (`scout_reports`, `venue_updates`, `venue_events`, …). Backend reads `UNION ALL`; `INCLUDE_SYNTHETIC=0` hides synthetic rows. That switch is the swap-to-real-data path.

## F. recs interface additions
- Report rows passed to `recs` carry `reputation` (backend joins from scouts; default 0.5).
- `venues` arg: `venue_id, name, lat, lon` + optional `syn_venue_attributes` fields.
- Inputs are lists of dicts (backend may pass DataFrames; recs accepts both).
- Live State optional keys: `display` (show|low|none), `predicted_crowd`, `predicted_source`; `vibe_score`, `confidence`, `trend` may be null. Predictions never overwrite observed fields.
- Recommendation adds: `rank_score`, `rank`, `excluded_reason` (str|null), `cluster_label`, `complaint_risk` (labelled "311 noise-complaint risk"), `is_synthetic`.
- Preferences optional: `start_time`, `dwell_minutes` (60), `max_total_walk_minutes` (30), `exclude_venue_ids` (plan-night).
- `plan_night` stop: `{order, venue_id, name, lat, lon, arrive_at, leave_at, walk_minutes_from_prev, distance_km, expected_vibe, match_score, confidence, reasons[]}`.

## G. HTTP API additions
- Every response object carries `is_synthetic`; list endpoints also return top-level header `X-Data: synthetic|real|mixed`.
- Errors: `{"error": {"code", "message", "details"}}` (422s reshaped too).
- `/api/health` → `{"ok": true, "recs": "real"|"stub", "data": "synthetic"|"real"|"mixed", "demo_now": ISO|null}`.
- Auth (MVP): `POST /api/auth/demo-login {display_name, role: user|scout|owner, venue_id?}` → `{token, user_id|scout_id}`; writes need `Authorization: Bearer <token>`. Owners cannot report their own venue.
- `/api/venues`: `limit` (50, max 200), `offset`; bare list + `X-Total-Count`.
- `POST /api/reports`: client sends venue_id, crowd, dancing, line_minutes, cover_usd?, music_genre?, lat?, lon?; server sets report_id, scout_id, ts, verified_presence, distance_m, status. Returns `{report_id, ts, status, points_pending}`.
- `POST /api/feedback` (syn_feedback fields minus id/recommended_at).
- `/api/heatmap?now=&by=hour` items: `{venue_id, lat, lon, hour?, vibe_score, confidence, n_reports, is_synthetic}`.
- Response shapes:
  - venue card: `{venue_id, name, display_name, style, genres[], price_level, typical_cover_usd, lat, lon, distance_km?, opening_hours, is_claimed, state, complaint_risk, is_synthetic}`
  - venue detail: `{venue, state, recent_reports[], offers[]}`
  - leaderboard row: `{rank, scout_id, display_name, level, points, points_week, reputation, is_synthetic}`
  - bounty row: syn_bounties fields + `venue_name`
  - owner dashboard: `{venue_id, views, taps, saves, reports_tonight, rec_appearances, demand_by_hour:[{hour, value}], is_synthetic}`
- Backend publishes these as Pydantic models; `GET /openapi.json` is the machine-readable contract.

## H. Env names (reserved)
`INCLUDE_SYNTHETIC`, `DEMO_NOW`, `CORS_ORIGINS`, `DATABASE_URL`, `LIVE_SIM_DB`, `FEATURE_ROUTING`, `FEATURE_HEATMAP`,
`VITE_API_BASE`, `VITE_API_MODE` (mock|live), `VITE_DEMO_NOW`, `VITE_FEATURE_ROUTING`, `VITE_FEATURE_HEATMAP`.

## I. Schedule (from integration)
Upstream deliverables pushed by **Fri Nov 13 18:00 ET** (moved up a day from integration's Nov 14 so there is slack); integration merges from Nov 13 in the order
specs → research → tableau → coursework → live-sim → ml-recs → backend → frontend; deploy dry-run Nov 15; freeze Nov 16 20:00; demo Nov 17.
Frontend mockup PNGs (overdue Nov 10 deliverable) are the first frontend priority: target Thu Nov 12.

## J. v2.2 additions (Nov 11)
- **Vibe label bands** (frontend copy): 0–34 "Chill", 35–64 "Lively", 65–100 "Packed"; null → no label.
- **Stale cutoff:** inputs older than 180 min are ignored (§A). In the UI, freshness > 60 min shows a "stale" tag even if confidence clears the threshold.
- **Map tiles:** MapLibre GL with a free no-key style (OpenFreeMap or CARTO dark-matter); no paid tile keys.
- **Demo-night snapshots** (live-sim): `data/synthetic_live/demo_night_snapshots.csv` — venue_id, snapshot_ts (every 30 min, 20:00–03:00 Sat Nov 14), crowd, dancing, line_minutes, vibe_score, confidence, n_reports, is_synthetic. Values are recs Live Venue State computed at snapshot_ts. Tableau's hourly cell for hour HH uses the **HH:30** snapshot.
- **Backend CR-11..14 accepted:** `/api/venues` takes optional `lat`, `lon` (distance_km computed, sort by distance when given); on Postgres, synthetic tables are copied in (no ATTACH); real twin tables (`scout_reports`, `venue_updates`, `venue_events`, `feedback`, `bounties`, `disputes`, `points_ledger`) exist empty from day one; owner identity = demo-login with `role=owner` + `venue_id`, one owner per venue in MVP.
- **live_sim.db generation** runs at **build time** (Render build command / `make data`), not at boot; live-sim targets < 60 s for the full 36-night run on a laptop CPU.
