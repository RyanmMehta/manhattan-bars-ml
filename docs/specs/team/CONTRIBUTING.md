# Contributing — Nightlife Autopilot

Purpose: how the team works in this repo (integration copies this to the root `CONTRIBUTING.md`).
Status: agreed.
Last updated: 2026-11-17

## Setup
```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt               # pipeline + recs
pip install -r backend/requirements.txt       # backend (when present)
python -I -m simulator --seed 42 --out data/live_sim.db   # synthetic data (build-time, not committed)
cd frontend && npm ci && npm run dev          # Node 20 LTS
```
Run Python with `python -I` (isolated mode).

## Branches
- Workstreams: `nightlife/<workstream>` (e.g. `nightlife/backend`), branched from `nightlife/contracts`.
- First PRs: `fp/<handle>-<topic>` off the integration branch.
- Never push to `main`. Integration merges in the order in `docs/CONTRACTS.md` §I.

## Folder ownership
Each folder has one owner workstream (table in `docs/CONTRACTS.md`). Only change folders you own.
Need a contract change? Write it under "Contract change requests" in `docs/workstreams/<name>.md`;
do not edit `docs/CONTRACTS.md` on your branch.

## Commits and PRs
- Conventional prefixes: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, optionally scoped (`docs(specs): …`).
- Small PRs (≤ 300 changed lines). Use the PR template.
- 1 reviewer approval and green checks before merge. No force-push to shared branches.
- Never commit secrets, `.env` files or generated `.db` files.

## Synthetic data rule (summary)
1. Every synthetic row has `is_synthetic = 1`.
2. Synthetic files live under a path containing `synthetic`; synthetic DB tables start with `syn_`; synthetic ids start with `syn-`.
3. Code that reads synthetic data has `# SYNTHETIC: <real source>` (`// SYNTHETIC:` in TS).
4. List every synthetic dataset in `docs/synthetic/<workstream>.md` (file, imitates, how generated, real source, swap steps).
5. The UI shows a "demo data" badge on synthetic data.

## Checks
```bash
python -I docs/specs/tools/check_golden.py                 # scoring goldens
python -I -m unittest discover -s docs/specs/tools         # specs unit tests
python -I docs/specs/tools/check_docs.py                   # specs docs lint
pytest recs backend                                        # when present
cd frontend && npm test                                    # when present
```
Scoring changes must keep golden vectors passing (`docs/specs/golden_vectors.json`).
Constants come from `docs/specs/PARAMETERS.md`; change them there first.

## Questions
Ask in the team channel or open a note in your `docs/workstreams/<name>.md`; tag the owning workstream.
