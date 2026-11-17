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
- A7 Truth-table grep test uses a reviewed allowlist (recs eval/CLI/stub files); runtime modules `recs/{live_state,scoring,routing}.py` must not mention them.
- A8 Frontend `VITE_API_BASE` is the API base **including `/api`** (e.g. `http://127.0.0.1:8000/api`); e2e, `run_demo.py` and DEMO.md use that form.
- A9 e2e conftest/run_demo run `alembic upgrade head` on the temp app DB first (backend's `start.sh` does the same).
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

| 5 | live-sim | 9921e56 | `.gitignore` | union of both | simulator 27 pass; contract 72 pass / 10 skip / 1 xfail (snapshots vs stub engine) | `make data` 36 nights in ~11 s |
| 6 | backend (re-merge) | d66cde0 | none | — | backend 94 pass | G1–G8 tests |
| 7 | live-sim + backend (re-merge) | 0d2a26c, 9bb542c | `backend/scripts/build_sim.sh` | took backend (same contract command) | backend 96, simulator 28, contract 72 pass | integration fix to build_sim.sh now upstream |
| 8 | ml-recs | 5e10061 | none | — | recs 65, backend 96 (recs engine), contract 83/83, tableau 13 | snapshots regenerated with `python -m recs snapshots`; tableau extracts + stand-in PNG/PDF re-rendered (HH:30 rule checked: 245/245 cells match) |
| 9 | coursework | 9b8fb37 | none | — | coursework 22 pass (needs CPU torch); ownership audit 0 files outside `coursework/` | |
| 10 | backend (re-merge) | bd463d9 | none | — | backend 98, contract 83/83 | numeric complaint_risk accepted |
| 11 | frontend | 37fe0e7 | none | — | (pre-merge dry run of 616b593: 13/15; owner-dashboard auth fixed upstream) | ownership audit 0 outside `frontend/` |
| 12 | contracts, coursework, live-sim, ml-recs, backend, frontend finals | c3fd169, 1835e6f, c3edeba, 48d4ace, 0d02a83, c5caa97 | `demo_night_snapshots.csv` | took live-sim's, then regenerated | see below | `make data` alone now equals the API snapshots (525/525 rows identical) |
| 13 | specs, ml-recs, backend follow-ups | 008a064, c8f98b7, 7e3a4d3 | none | — | **final:** specs golden 9/9, recs 70, backend 119, simulator 31, frontend 81, coursework 22, research+tableau 35, contract 85, e2e 15/15 ×3, pipeline smoke OK | G9 energy penalty; cluster_description passthrough |

## Seeded demo data (US-7)
`make data` run twice from scratch → identical per-table fingerprints (`scripts/integration/db_fingerprint.py`):

| table | rows | sha256 (first 12) |
|---|---|---|
| syn_bounties | 2409 | 22aea4138a05 |
| syn_disputes | 250 | cc7ca2e73393 |
| syn_feedback | 1440 | a8f2e9865a4c |
| syn_points_ledger | 17702 | 362aa4c51519 |
| syn_scout_reports | 8147 | e4a85c248614 |
| syn_scout_reputation_history | 1644 | 1e2985d679c9 |
| syn_scout_truth | 209 | 26b40edaa437 |
| syn_scouts | 209 | cfe01215078a |
| syn_true_state | 35420 | de123e78babb |
| syn_users | 300 | b46e4545ecef |
| syn_venue_attributes | 35 | e076dce42932 |
| syn_venue_events | 65973 | 6661064a9441 |
| syn_venue_updates | 662 | 51f4b76dba2b |

## Fixes applied to other workstreams
| workstream | file | change | why |
|---|---|---|---|
| backend | `backend/Dockerfile.dockerignore` | + `data/manhattan_bars.db`, `data/synthetic` | BuildKit uses this file instead of root `.dockerignore`; v2 §D says the image excludes the 39 MB DB (backend reads `launch_venues_full.csv` first) |
| backend | `backend/scripts/build_sim.sh` | run exactly `python -m simulator --seed 42 --out …` (no `-I` attempt first) | contracts f5c95d2 / CR-15 |

## Open issues
- **Not deployed** (no Render/Vercel accounts). Root `render.yaml` + `frontend/vercel.json` are ready; steps in `DEMO.md` §Deploy. `make test-deployed` has never run.
- **Docker image not built locally** (no Docker daemon in this container); backend notes the same.
- Demo script: onboarding must set **Crowd = 4** — with the UI default (3) the #1 pick at 11:30 PM is a vibe-26 "Chill" venue. e2e sets 4 and asserts the #1 pick is vibe ≥ 35 (The Mayfly, vibe 78).
- Resolved during the build: snapshot divergence (live-sim c3edeba), owner dashboard 401 (frontend 37fe0e7), vibe-0 #1 ranking (ml-recs 48d4ace / specs G9).

## Contract change requests
None open.
