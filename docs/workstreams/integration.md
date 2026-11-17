# Workstream notes — integration (as built)

Owner: Ryan Mehta · Branch `nightlife/integration` · Plan: `docs/prd/integration/`

## What was built
- `Makefile`: `setup`, `launch-venues`, `data` (exactly `python -I -m simulator --seed 42 --out data/live_sim.db`, `DATA_NIGHTS=N` → `--nights N`), `test` (smoke → units → contract → e2e), `test-deployed`, `demo`, `synthetic-docs`, `audit`, `status`.
- `scripts/build_launch_venues_full.py` → committed `data/launch_venues_full.csv` (35 venues + OSM display name, hours, website flag, neighbourhood).
- `scripts/integration/`: `consolidate_synthetic.py` (→ `SYNTHETIC_DATA.md`), `ownership_audit.py`, `merge_status.py`, `pipeline_smoke.py`, `run_demo.py`, `backend_app.py`, `warmup.sh`.
- `tests/contract/`: `schemas.py` + `constants.py` (CONTRACTS transcribed once), `test_syn_tables.py`, `test_recs_interface.py` (G1/G5), `test_api.py`, `test_isolation.py` (INCLUDE_SYNTHETIC=0, truth tables dropped, grep), `test_demo_snapshots.py`, `test_launch_venues.py`. Each skips cleanly until its workstream is merged.
- `tests/e2e/`: pytest starts uvicorn + `vite preview` (live API, `VITE_DEMO_NOW`), then runs `smoke.cjs` (Node Playwright, preinstalled Chromium, 390×844).
- Root `render.yaml`, `.dockerignore`, `requirements-dev.txt`, `DEMO.md`, README section, `SYNTHETIC_DATA.md`.

## How to run
```
make setup && make data && make test   # full local check
make demo                              # backend :8000 + frontend :5173 at DEMO_NOW
make status                            # which workstreams are done / merged
```

## Assumptions (recorded, not asked)
- A1 Python Playwright is not installed in the container; only Node `playwright` is. e2e is therefore a Node script (`tests/e2e/smoke.cjs`) wrapped by pytest, rather than Python Playwright as in RULES §3. Same browser, same assertions.
- A2 No Render/Vercel accounts: deploy is prepared (root `render.yaml`, Vercel steps in `DEMO.md`) but not run (instruction for this build session).
- A3 Backend app import path unknown until merge; tests and scripts auto-detect `backend.app.main:app`, `backend.main:app`, … or `BACKEND_APP`.
- A4 Merge order from OUTLINE §2 is followed where branches are ready at the same time; a branch that signals done early is merged as soon as its dependencies are in.

## Merge log
| order | branch | sha | conflicts | resolution | tests after | notes |
|---|---|---|---|---|---|---|

## Fixes applied to other workstreams
_None yet._

## Open issues
- Deploy not run (no accounts). Steps in `DEMO.md` §Deploy.

## Contract change requests
None open.
