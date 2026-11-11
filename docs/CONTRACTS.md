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
