# Nightlife Autopilot: frontend

Mobile-first React (Vite + TypeScript) app for the Nightlife Autopilot demo. Built against `docs/CONTRACTS.md`
(v2.2 + §J). Plans: `docs/prd/frontend/`. As-built notes: `docs/workstreams/frontend.md`.

## Run it
```bash
cd frontend
nvm use            # Node 20 (works on 22 too)
npm ci
npm run dev        # http://localhost:5173 — mock API (MSW) by default (.env.development)
```
Live backend: start the FastAPI backend on `:8000` (see `backend/README.md` on `nightlife/backend`), then
`VITE_API_MODE=live npm run dev` (Vite proxies `/api`). Checks: `npm run contract:live && npm run e2e:live`.
At runtime, `?mock=1` / `?mock=0` or the demo panel (`?demo=1`, or tap the logo 5×) switches mode.

## Scripts
| Script | What |
|---|---|
| `npm run build` / `preview` | typecheck + production build / serve `dist` on :4173 |
| `npm run typecheck`, `lint` | `tsc --noEmit`; ESLint (typescript-eslint, react-hooks, jsx-a11y, no hex literals, no `?? 0` in venue components) |
| `npm test` / `test:cov` | Vitest unit + component + jsdom route walk (81 tests, ~81% line coverage) |
| `npm run e2e` | Playwright, mock mode, 390×844 (flows, badge on every route, axe, no horizontal scroll) |
| `npm run e2e:live` | Playwright against a live build (`--mode live`, preview proxies `/api` to :8000); skips if the backend is down |
| `npm run mockups` | export `mockups/*.png` + contact sheet from the running app |
| `npm run contract:live` | validate a live backend's `/api/*` against the app's type guards (`CONTRACT_BASE=…`, default `http://localhost:8000/api`; `CONTRACT_BASE=selftest` checks the checker against the mocks) |
| `npm run fixtures` | regenerate `src/mocks/fixtures/synthetic/syn_*.json` (seed 42) |

Playwright uses the preinstalled Chromium (`@playwright/test` 1.63.0 matches it). Don't run `playwright install`.

## Env (reserved names only, CONTRACTS §H)
See `.env.example`: `VITE_API_MODE` (mock|live), `VITE_API_BASE`, `VITE_DEMO_NOW`, `VITE_FEATURE_ROUTING`,
`VITE_FEATURE_HEATMAP`. `.env.production` defaults to **mock** until the Render URL is confirmed.

## Deploy to Vercel (not deployed yet; no account)
1. In Vercel: **Add New → Project →** import `ryanmmehta/manhattan-bars-ml`, branch `nightlife/integration`
   (or `nightlife/frontend` for a preview). **Root Directory: `frontend`**. Framework preset: Vite (also set in `vercel.json`).
2. Environment variables (Production and Preview):
   - Demo without backend: `VITE_API_MODE=mock`, `VITE_DEMO_NOW=2026-11-14T23:30:00-05:00`, `VITE_FEATURE_ROUTING=1`, `VITE_FEATURE_HEATMAP=1`.
   - With backend: `VITE_API_MODE=live`, `VITE_API_BASE=/api` (uses the `vercel.json` rewrite). Edit the rewrite
     destination in `vercel.json` to the real Render host if it isn't `nightlife-autopilot-api.onrender.com`.
     Alternatively set `VITE_API_BASE=https://<render-host>/api` and add the Vercel domain to the backend's `CORS_ORIGINS`.
3. Deploy. Check `/tonight`, `/map`, and `/venue/0370-21-116653` deep links (SPA rewrite) and `?mock=1`.
4. CLI alternative: `npm i -g vercel && cd frontend && vercel link && vercel env add VITE_API_MODE && vercel --prod`.
