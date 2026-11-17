# Class demo script — Nightlife Autopilot (Tue Nov 17, ~5 min)

Demo clock: **Sat Nov 14, 11:30 PM** (`DEMO_NOW = 2026-11-14T23:30:00-05:00`). All "tonight"
data is synthetic (seed 42) and shows the **demo data** badge; see `SYNTHETIC_DATA.md`.

## Before class (T-15 min)
1. Local fallback ready on the laptop: `make setup && make data && make demo` → open
   `http://127.0.0.1:5173/` (backend on :8000). Check `http://127.0.0.1:8000/api/health` shows
   `"recs": "real"` and `"demo_now": "2026-11-14T23:30:00-05:00"`.
2. If deployed: `API_URL=https://<backend>.onrender.com scripts/integration/warmup.sh --loop` (Render free tier sleeps; first hit can take ~60 s).
3. Phone + laptop open on the frontend; clock chip reads **Sat 11:30 PM**.

## Script
| t | Beat | Say / do |
|---|---|---|
| 0:00 | Problem (30 s) | Groups lose time choosing where to go and the info they find is stale. Public data covers 5,737 Manhattan venues; we launch on 35 Lower East Side bars. |
| 0:30 | Honesty (15 s) | Point at the **demo data** badge: live reports are simulated until real Scouts exist; `SYNTHETIC_DATA.md` lists how each piece is swapped for real data (one switch: `INCLUDE_SYNTHETIC=0`). |
| 0:45 | Group flow (90 s) | Onboarding: hip-hop + r&b, want dancing, **Crowd 4**, cover ≤ $20, line ≤ 15 min, group of 4 → **Save** → **Tonight** (expected top pick: The Mayfly, vibe 78 "Packed"). Read the top pick's match / vibe / confidence and its reasons; show a venue hidden by limits (line too long) and a greyed "low confidence" / "No fresh reports" one. Vibe = how busy it is now; match = fit to your group; confidence = how much fresh evidence we have. |
| 2:15 | Scout flow (60 s) | Open a venue → 10-second vibe check (crowd 5, dancing lots, line 5) → submit → report count +1, "0 min ago" → leaderboard / bounties. |
| 3:15 | Operator flow (45 s) | Owner login for one venue → post "$10 cover before midnight" → appears on the venue profile; owner dashboard demand chart (demo data). |
| 4:00 | Later features (30 s) | Run My Night (3 stops) and the heatmap if enabled; else skip. |
| 4:30 | Under the hood (30 s) | Public data → Scout reports → live state (time decay, scout reputation) → recommend. 311 noise-complaint risk is a separate label, never "quality". Tableau dashboard in `analytics/tableau/`. |
| 5:00 | End | Repo + URL. |

## Fallbacks
- Render asleep → keep talking through beats 1–2 while warm-up finishes.
- Backend down → laptop `make demo` (local, same data, same clock).
- Everything down → screenshots in `docs/demo/` (e2e run writes them; copy the latest set there).

## Deploy (prepared, not run — needs Ryan's Render + Vercel accounts)
Branch for both: `nightlife/integration`. Nothing below needs a secret in the repo.

**1. Backend on Render (Docker, free tier)**
1. Render → New → **Blueprint** → connect GitHub repo `ryanmmehta/manhattan-bars-ml`, branch `nightlife/integration`, Blueprint path `render.yaml` (root).
2. It creates web service **`nightlife-autopilot-api`** (Docker, `backend/Dockerfile`, context = repo root). Keep that name: `frontend/vercel.json` proxies `/api/*` to `https://nightlife-autopilot-api.onrender.com`. If Render gives a different URL, edit that rewrite.
3. The image build runs `backend/scripts/build_sim.sh` → `python -m simulator --seed 42 --out data/live_sim.db` (build time, v2.2 §J); boot runs `alembic upgrade head`, checks the sim DB, starts uvicorn. The image excludes `data/manhattan_bars.db` and uses `data/launch_venues_full.csv`.
4. Env (from `render.yaml`): `DEMO_NOW=2026-11-14T23:30:00-05:00`, `INCLUDE_SYNTHETIC=1`, `ALLOW_FIXTURE_SIM=0`, `DEMO_AUTH=1`, `RECS_MODE=auto`, `FEATURE_ROUTING=1`, `FEATURE_HEATMAP=1`, `ADMIN_TOKEN` (generated), `CORS_ORIGINS` (set to `https://<your-app>.vercel.app,http://localhost:5173`).
5. Check: `curl https://nightlife-autopilot-api.onrender.com/api/health` → `{"ok": true, "recs": "real", "data": "synthetic", "demo_now": "2026-11-14T23:30:00-05:00"}`.

**2. Frontend on Vercel**
1. Vercel → Add New → Project → import the same repo; **Root Directory `frontend`**; production branch `nightlife/integration` (Settings → Git). `frontend/vercel.json` sets Vite, `npm run build`, `dist`, the `/api` proxy and SPA rewrites.
2. Environment variables (Production): `VITE_API_MODE=live` (the committed `.env.production` defaults to `mock`), `VITE_API_BASE=/api` (same-origin via the proxy, so no CORS needed), `VITE_DEMO_NOW=2026-11-14T23:30:00-05:00`, `VITE_FEATURE_ROUTING=1`, `VITE_FEATURE_HEATMAP=1`. Redeploy after setting them (Vite bakes env at build time).
3. Put the Vercel URL in Render's `CORS_ORIGINS` (only needed if you later call the API cross-origin).

**3. Verify**
```
make test-deployed BASE_URL=https://<your-app>.vercel.app API_URL=https://nightlife-autopilot-api.onrender.com   # run 3×
API_URL=https://nightlife-autopilot-api.onrender.com scripts/integration/warmup.sh --loop                      # during class
```
Free tier: the backend sleeps after ~15 min idle (first request ~1 min) and its disk is ephemeral (demo writes reset on restart).
