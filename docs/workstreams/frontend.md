# Workstream: frontend (as built)

Owner: Ryan Mehta · Branch: `nightlife/frontend` · Built Nov 17 2026 against CONTRACTS v2.2 + §J (`b46d75f`).
Folder: `frontend/` (see `frontend/README.md` for run and deploy steps). Synthetic registry: `docs/synthetic/frontend.md`.

## What was built
- **Every MVP screen (PRD §5) works in mock mode and is wired for live mode:** onboarding/prefs (US-01), tonight pick with
  hero, "also good", "show N excluded" and share link (US-02), browse with search/style/genre/sort (US-03), venue
  profile with live state, reports, offers, directions and "311 noise-complaint risk" (US-04), MapLibre map with
  vibe/confidence dots, heat layer, time slider and SVG fallback (US-05), 10-second vibe check with nearest-venue
  pre-select, 150 m hint, visible timer and offline queue (US-06), leaderboard with week/all-time tabs and a pinned
  demo scout, plus bounties (US-07), Run My Night with swap stop and route mini-map behind `VITE_FEATURE_ROUTING` (US-08),
  owner dashboard with KPIs, lazy Recharts demand chart, update form and live preview (US-09), demo panel with persona,
  time travel, API mode and synthetic outline (US-10), and demo badges plus a global banner (US-11). Post-visit feedback
  prompt (T18) on the venue profile.
- **API layer:** a single typed client (`src/api/client.ts`) that adds `now` to every request, sends bearer tokens on
  writes, maps the `{error:{code,message,details}}` envelope, reads `X-Total-Count`/`X-Data`, and checks every
  response with hand-written type guards (`adapters.ts`). It also has TanStack Query hooks and demo-login tokens
  (`na.token.v1`, 24 h).
- **Mock API:** MSW handlers for all 14 endpoints over seeded `syn_*` fixtures. Writes change an in-memory copy, so the
  OUTLINE §7 demo loop works offline: a report raises confidence and pays bounty points, and the demo scout moves up.
- **Mockups (deliverable):** `frontend/mockups/` contains 01-onboarding, 02-pick, 03-browse, 04-venue, 05-map,
  06-heatmap, 07-vibe-check, 08-leaderboard, 09-bounties, 10-run-my-night, 11-owner, 11-owner-desktop,
  05-map-desktop and contact-sheet. All are exported from the app via `npm run mockups` at DEMO_NOW.
- **Deploy config:** `frontend/vercel.json` (SPA rewrite + `/api/*` → Render rewrite). **Not deployed:** there is no Vercel account yet.

## Status vs OUTLINE
| Task | Status |
|---|---|
| T1–T15 | done |
| T16 live mode | done against the contract; **pending backend**: `nightlife/backend` had no code on Nov 17, so `contract:live` has only been run in self-test mode (8/8 pass). The live build shows "live API isn't answering → Use demo mode" when `/api/health` fails or takes over 5 s. |
| T17 Run My Night | done (mock) |
| T18 feedback prompt | done (mock) |
| T19 e2e + a11y | done: 24 Playwright tests (flows, badge on every route, axe 0 serious/critical on 11 routes, no horizontal scroll at 360/390 px) |
| T20 perf | done; see scores below |
| T21 Vercel | config + steps written; not deployed (no account) |
| T22 docs | this file, `docs/synthetic/frontend.md`, `frontend/README.md`, `frontend/mockups/README.md` |

## Quality gates (Nov 17, all run locally)
- `npm run typecheck`: pass. `npm run lint`: pass (0 warnings).
- `npm test`: 81 Vitest tests pass; line coverage 81.5% on `src/api`, `src/state`, `src/components`, `src/lib`.
- `npm run e2e`: 24/24 pass (3 repeated runs of the main suite green).
- Bundle: initial JS ≈ 87 KB gzip (react 51.6 + query 13.8 + app 21.7). MapLibre (220 KB gz), Recharts (104 KB gz)
  and the mock API (141 KB gz) load lazily.
- **Lighthouse** (v12.2.1, mobile emulation, production build in mock mode, `/tonight`): **Performance 94,
  Accessibility 100, Best Practices 100**. FCP 2.1 s, LCP 2.8 s, TBT 40 ms, CLS 0.

## Env vars
`VITE_API_MODE` (mock|live), `VITE_API_BASE` (default `/api`), `VITE_DEMO_NOW` (`2026-11-14T23:30:00-05:00`),
`VITE_FEATURE_ROUTING` (`1` shows Run My Night), `VITE_FEATURE_HEATMAP` (`0` hides the Heat toggle). Precedence for `now`:
URL `?now=` > demo panel > `VITE_DEMO_NOW` > `health.demo_now`. The demo panel also rewrites a URL `?now=` so time travel works on shared links.

## Deploy URL
None yet. Steps are in `frontend/README.md` § Deploy. `.env.production` defaults to mock mode, so a deploy works without the backend.

## Assumptions (made without asking)
- A6 No live-sim CSVs (`data/synthetic_live/`) or backend code existed on any remote branch on Nov 17, so fixtures come
  from the seeded generator. `npm run fixtures` will pick up `syn_venue_attributes.csv` automatically once it lands.
  `demo_night_snapshots.csv` still needs a small loader change.
- A7 Contrast fixes to PRD §6 tokens: muted `#9A9AB0` → `#A3A3B8` and Chill `#5B4BDB` → `#8A7CF4`. The PRD values failed
  WCAG AA (4.5:1) on the surface colour. All other tokens are as specified.
- A8 The fixture `display_name` for 6 venues is hand-set (e.g. "Subject", "Attaboy"). The rest use the PRD F6 cleaner.
- A9 Added `/scout/bounties` and `/more` routes, plus `/owner`, which redirects to the persona's venue, alongside the PRD F7 deep links.
- A10 `contract:live` is a Vitest suite (`tests/live/`, `vitest.live.config.ts`) rather than `scripts/contract-live.mjs`.
  This lets it reuse the app's TypeScript type guards.
- A11 Mockups are full-page captures for the long screens (pick, venue, plan, owner) and viewport captures for the rest.
- A12 The Vercel `/api/*` rewrite destination `nightlife-autopilot-api.onrender.com` is a placeholder until integration
  confirms the Render host.
- A13 Points in the mock = 10 per report + bounty points. The real values come from the backend.

## Dependencies added beyond RULES §2
- `@types/node` (types for the Playwright config and Node scripts), `axe-core` (a11y checks in e2e, T19),
  `@vitest/coverage-v8` (coverage gate). All are dev-only.

## Open issues
1. LCP 2.8 s on simulated 4G in mock mode (target 2.5 s). Causes: the Google Fonts request and MSW start-up before
   first render. Fixes: self-host the fonts or use `preload`; in live mode MSW isn't loaded at all.
2. Live mode has not been verified against a real backend (none existed). Run `npm run contract:live` as soon as
   `backend/` is up and log mismatches as CRs.
3. Heatmap `by=hour` uses the nearest 30-min snapshot in the mock; real `hour` semantics come from the backend.
4. The Vercel account and domain (PRD Q5) are still with Ryan.

## Contract change requests
None new. Observations for integration:
- CR-15 (suggestion): add `address` to the venue card shape (§G). The profile shows it, and the mock already sends it.
  If the backend omits it, the UI falls back to lat/lon.
- CR-16 (suggestion): give `syn_venue_updates.genres` one type on the wire (array). The UI accepts both a pipe-string and an array.
