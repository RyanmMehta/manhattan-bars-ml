# Workstream notes — integration (as built)

Owner: Ryan Mehta · Branch `nightlife/integration` · Plan: `docs/prd/integration/`

## What was built
- `Makefile`: `setup`, `launch-venues`, `data` (exactly `python -m simulator --seed 42 --out data/live_sim.db`, `DATA_NIGHTS=N` → `--nights N`), `test` (smoke → units → contract → e2e), `test-deployed`, `demo`, `synthetic-docs`, `audit`, `status`.
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
- A5 Backend's complaint_risk is an object `{label, noise_complaints_3y, level}` (label \"311 noise-complaint risk\"); contract tests accept number or object.
- A6 `POST` endpoints may return 201; tests accept 200/201.
- A4 Merge order from OUTLINE §2 is followed where branches are ready at the same time; a branch that signals done early is merged as soon as its dependencies are in.

## Merge log
| order | branch | sha | conflicts | resolution | tests after | notes |
|---|---|---|---|---|---|---|
| 0 | contracts | f5c95d2 | none | — | contract 2 pass | build command drops `-I` (CR-15); Makefile/render/docs updated |
| 1 | specs | fdcd327 | none | — | check_golden 8/8, unittest OK, check_docs OK | PR template → `.github/`, CONTRIBUTING → root; golden-vector test reads `expected.states` |
| 2 | research | 46d30bd | none | — | research+tableau pytest 34 pass / 1 skip | |
| 3 | tableau | 2b64854 | none | — | (same run) | extracts refresh after ml-recs |
| 4 | backend | c478d1b | none | — | backend 82 pass; contract 20 pass / 63 skip (stub engine + fixture sim until live-sim/ml-recs) | merged ahead of live-sim/ml-recs (they hadn't signalled done); root `render.yaml` = backend Docker blueprint on `nightlife/integration` |

## Fixes applied to other workstreams
| workstream | file | change | why |
|---|---|---|---|
| backend | `backend/Dockerfile.dockerignore` | + `data/manhattan_bars.db`, `data/synthetic` | BuildKit uses this file instead of root `.dockerignore`; v2 §D says the image excludes the 39 MB DB (backend reads `launch_venues_full.csv` first) |
| backend | `backend/scripts/build_sim.sh` | run exactly `python -m simulator --seed 42 --out …` (no `-I` attempt first) | contracts f5c95d2 / CR-15 |

## Open issues
- Deploy not run (no accounts). Steps in `DEMO.md` §Deploy.

## Contract change requests
None open.
