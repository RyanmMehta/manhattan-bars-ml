# Synthetic data registry: frontend

Every synthetic dataset and placeholder the frontend workstream created (CONTRACTS "Synthetic data rule").
All fixture rows carry `is_synthetic: 1`, live under `frontend/src/mocks/fixtures/synthetic/`, and are only
served in **mock mode** (`VITE_API_MODE=mock` or `?mock=1`). In the UI, every synthetic item shows a
"demo data" badge, and a global banner is visible in mock mode or when `X-Data` / `health.data` is
`synthetic|mixed`. An e2e test walks every route and asserts the banner (`tests/e2e/app.spec.ts`).

Regenerate the fixtures with `npm run fixtures` (`frontend/scripts/build-fixtures.mjs`, seed 42). The script
reads `data/launch_venues.csv` (real public data) and, if live-sim has produced them,
`data/synthetic_live/*.csv`. **Current fixtures come from the seeded generator:** `data/synthetic_live/`
did not exist on any branch at build time.

## Datasets

| File | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `syn_venues.json` | 35 venue cards (`/api/venues` card shape §G) | Real name/address/lat/lon/noise_complaints from `data/launch_venues.csv`; style, genres, price, cover, dance floor and capacity from `syn_venue_attributes.csv` if present, else seeded random (seed 42). Hand-set attributes for 6 demo venues (Subject, The Box, Mehanata, Clockwork Bar, Treasure Club, Attaboy) in `OVERRIDES`. `complaint_risk` = noise complaints ÷ max (real public signal, normalised). | `GET /api/venues` (backend over `venues` + `syn_venue_attributes` / `venue_attributes_manual.csv`) | Set `VITE_API_MODE=live`; delete the fixture and the `/venues` handler |
| `syn_states.json` | Live Venue State per venue every 30 min, Sat Nov 14 20:00 → Sun 03:00 (15 snapshots; 23:30 = DEMO_NOW) | Seeded Gaussian energy curve per venue; ~20% of fields `null`; `display` from CONTRACTS §A thresholds. Story venues have fixed values (e.g. Subject vibe 78 / conf 0.71 at 22:30). Should be copied from `data/synthetic_live/demo_night_snapshots.csv` once live-sim publishes it (§J). | `recs.live_state.compute_all` via `/api/venues/{id}/state` | as above |
| `syn_recommendations.json` | `/api/recommend` results for 3 preset prefs (hip-hop dancers, cocktail chill, cheap & close) × 15 snapshots | Fixture-time weighted match (genre, crowd, dancing, line, cover, distance; unknown = 0.4 + `missing` entry); `rank_score = match·(0.75+0.25·conf)`; top 3 excluded rows with `excluded_reason`. Subject's match pinned to 91 for the demo script. **Not app logic**: the browser never scores. The mock handler picks the closest preset to the request prefs. | `recs.scoring.recommend` via `POST /api/recommend` | as above; delete preset matching in `handlers.ts` |
| `syn_reports.json` | Recent scout reports (§G `recent_reports`) | Sampled around each snapshot from that state (crowd ±0.5, 80% verified presence) | `syn_scout_reports` → real `scout_reports` | as above |
| `syn_leaderboard.json` | 25 scouts + the "Demo Scout" persona | Seeded first names + initial; points decay by rank; reputation 0.45–0.95 | `GET /api/scouts/leaderboard` over `syn_scouts` / `scouts` | as above |
| `syn_bounties.json` | 6 open bounties | Lowest-confidence venues at 23:30; Clockwork Bar fixed at 50 pts for the demo | `GET /api/bounties` over `syn_bounties` / `bounties` | as above |
| `syn_owner_dashboard.json` | Owner KPIs (views, taps, saves, reports_tonight, rec_appearances) + demand 18:00–03:00 | Seeded scale per venue; demand curve peaking 23:00–00:00 | `GET /api/owner/{id}/dashboard` aggregated from `syn_venue_events` / `venue_events` | as above |
| plan-night (derived, no file) | `POST /api/plan-night` stops | Mock handler chains non-excluded fixture recommendations greedily by distance; walk minutes = haversine at 5 km/h; `// SYNTHETIC:` in `handlers.ts` | `recs.routing.plan_night` | as above |
| heatmap (derived, no file) | `GET /api/heatmap?by=hour` | Projection of `syn_states` at the nearest snapshot (HH:30 rule, §J) + venue lat/lon | `/api/heatmap` | as above |
| mock write effects | Report → venue `n_reports` +1, confidence +0.25, freshness 0; bounty claimed; points = 10 + bounty | In-memory only (`handlers.ts`), reset on reload | backend `POST /api/reports` + credibility rules | as above |
| `src/mocks/fixtures/contract-samples/*.json` | One example per endpoint, copied from CONTRACTS.md (used only by the contract test) | Hand-copied | `GET /openapi.json` + `npm run contract:live` | Keep; update when CONTRACTS changes |

## Placeholders in code (marked `// SYNTHETIC:`)

| Where | What | Replace with |
|---|---|---|
| `src/state/persona.tsx` `DEMO_NAMES`, `DEMO_OWNER_VENUE` | Demo persona names for demo-login; default owner venue (Mehanata) | Real accounts + claim flow |
| `src/screens/OwnerDashboard.tsx` | KPI tiles + demand chart (synthetic until backend analytics exist) | `/api/owner/{id}/dashboard` over real `venue_events` |
| `src/screens/VibeCheck.tsx` | "Points are calculated on the server" copy + demo badge on points toast | Real points ledger |
| `scripts/mockups.mjs` `PREFS` | Demo prefs for the exported mockups | n/a (deliverable only) |
| `src/main.tsx`, `src/mocks/browser.ts`, `src/mocks/db.ts`, `src/mocks/handlers.ts` | Mock API | `VITE_API_MODE=live` |

## Full swap to real data
1. Set `VITE_API_MODE=live` and `VITE_API_BASE` (or keep `/api` with the Vercel rewrite) in every Vercel environment.
2. Run `npm run contract:live` against the backend. It must report 0 mismatches.
3. Delete `src/mocks/fixtures/synthetic/`, `scripts/build-fixtures.mjs`, `src/mocks/{db,handlers,browser}.ts` and the
   mock branch in `src/main.tsx`; remove `msw` from package.json and `public/mockServiceWorker.js`.
4. Badges then follow the backend's `is_synthetic` flags and `X-Data` header automatically.
