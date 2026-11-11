# RULES — integration build session

Read this before touching anything. These rules bind the future session that builds
the integration workstream. `docs/CONTRACTS.md` overrides this file if they disagree.

## 1. Mission
Merge all `nightlife/*` branches, wire backend ↔ recs ↔ live-sim data ↔ frontend,
test end to end, seed a demo night, deploy (Render + Vercel), consolidate synthetic-data
docs, update README, write the demo script. You are a **glue** workstream: you connect
and verify; you do not re-implement other workstreams' features.

## 2. Branching and git
- Work only on `nightlife/integration` (created from `nightlife/contracts`).
- Bring in workstreams with `git merge --no-ff origin/nightlife/<name>` in the order in
  OUTLINE §2. Never rebase or force-push another workstream's branch. Never push to `main`.
  No PRs.
- One merge commit per workstream; message: `Merge nightlife/<name> (<short sha>) into integration`.
- Fixes after a merge go in separate commits: `integration: <what> (<which workstream>)`.
- Re-merge (not cherry-pick) when a workstream pushes updates.
- Push with `git push -u origin nightlife/integration`; retry network failures 4× with 2/4/8/16 s backoff.
- Commit messages end with the attribution lines the harness provides.

## 3. Stack and versions
| Layer | Choice | Version (pin) |
|---|---|---|
| Python | CPython | 3.12 on Render (`PYTHON_VERSION=3.12.7`, placeholder); 3.13 locally is OK |
| Existing pipeline | pandas ≥ 3.0, numpy ≥ 2.0, scipy ≥ 1.14, scikit-learn ≥ 1.6 | as in root `requirements.txt` |
| API | FastAPI + Uvicorn, SQLAlchemy, SQLite | versions whatever backend pins; do not bump |
| Recs | `recs/` package | whatever ml-recs pins |
| Frontend | Node 20 LTS, Vite, React, TypeScript | whatever frontend pins (`package-lock.json` wins) |
| Tests | pytest, httpx (TestClient), jsonschema; Playwright (Python, pre-installed in container — do **not** `playwright install`) | pytest ≥ 8 |
| Deploy | Render (Docker web service from `backend/Dockerfile` + `render.yaml`), Vercel (static Vite build of `frontend/`) | — |
- If two workstreams pin different versions of the same package, pick the higher one
  that passes both test suites, record it in the merge log.
- Integration adds dependencies only to `requirements-dev.txt` (test tools). Never add
  runtime deps to another workstream's requirement file without filing a CR.

## 4. Folders integration owns (may create/edit freely)
- `tests/contract/`, `tests/e2e/`, `tests/conftest.py` (root-level test glue only)
- `scripts/` (v2 §C; integration's own scripts under `scripts/integration/`, plus `scripts/build_launch_venues_full.py`)
- `data/launch_venues_full.csv` (v2 §D; real public data, `is_synthetic` not needed)
- root `CONTRIBUTING.md`, root `render.yaml`, `.dockerignore`, `.github/` (v2 §C)
- `Makefile`, `requirements-dev.txt`
- `SYNTHETIC_DATA.md`, `DEMO.md`, `README.md` (root; preserve existing pipeline sections)
- `docs/prd/integration/`, `docs/workstreams/integration.md`, `docs/synthetic/integration.md`
- `.gitignore` (append only)

## 5. What integration must NOT touch
- `docs/CONTRACTS.md` — never edit. Proposals go in PRD §12 / `docs/workstreams/integration.md` "Contract change requests".
- `src/`, `data/manhattan_bars.db`, `data/raw/`, `data/launch_venues.csv`, `reports/` — do not modify. Regenerate the DB only with the existing scripts if a merge corrupts it, then restore the `nightlife/contracts` version.
- Other workstreams' folders (`docs/specs/`, `research/`, `analytics/tableau/`, `simulator/`, `data/synthetic_live/`, `recs/`, `backend/`, `frontend/`, `coursework/`, their `docs/workstreams/*.md`, `docs/synthetic/*.md`) — **except** for merge-conflict resolution, and minimal wiring fixes (≤ ~20 lines, e.g. an env var name or import path) that are:
  1. clearly blocking the end-to-end path,
  2. committed separately as `integration: fix <x> in <workstream>`,
  3. listed in `docs/workstreams/integration.md` → "Fixes applied to other workstreams" so the owner can upstream them.
  Anything larger: stop, record it as a blocker for that workstream, use a fallback (stub/mock/feature flag).
- No secrets, tokens or account emails in the repo. Render/Vercel env vars are set in their dashboards; document names only.

## 6. Conflict resolution policy
1. Ownership wins: in a conflict inside folder X, take X's owner's version.
2. Root shared files: `requirements.txt` → union, sorted, highest compatible pin;
   `.gitignore` → union; `README.md` → integration rewrites last (others' text moved into
   their own docs, linked).
3. Binary files (`*.db`, images): never hand-merge. Take `nightlife/contracts` for
   `manhattan_bars.db`. `data/live_sim.db` is never committed (v2 §D) — if a branch
   commits it, `git rm --cached` it, gitignore it, and regenerate with seed 42.
4. Contract disagreements: CONTRACTS.md wins; if the producer is wrong, write an
   adapter in `scripts/integration/` or the consumer only as a last resort, and file a CR.
5. Record every non-trivial resolution in `docs/workstreams/integration.md` → "Merge log".

## 7. Coding conventions
- Python: PEP 8, type hints on public functions, module docstring with usage line,
  `pathlib` paths relative to repo root, run scripts with `python -I`. No notebooks.
- Scripts are idempotent and take `--seed` / `--now` where relevant; default seed **42** and `--now` default `DEMO_NOW = 2026-11-14T23:30:00-05:00` (v2 §B).
- Timestamps: ISO 8601 with offset, America/New_York (contract). Never naive datetimes in tests.
- TS (only for wiring fixes): follow frontend's lint/prettier config.
- Small functions, no frameworks beyond the stack above. Config via env vars with defaults
  documented in README's env table.
- Logging: `print` to stderr in scripts is fine; backend uses its own logger.

## 8. Synthetic-data marking (mandatory, from CONTRACTS.md)
- Any table/CSV integration creates (e.g. demo-night overrides, e2e fixtures) has
  `is_synthetic = 1`, lives under a path containing `synthetic`
  (e.g. `data/synthetic_demo/`, `tests/fixtures/synthetic/`), and DB tables are prefixed `syn_`.
- Every code line that reads synthetic data carries `# SYNTHETIC: <real source that replaces this>`
  (`// SYNTHETIC:` in TS).
- Register each dataset in `docs/synthetic/integration.md` with: file/table, imitates,
  how generated, real replacement, swap steps.
- `SYNTHETIC_DATA.md` (root) is generated by `scripts/integration/consolidate_synthetic.py`
  from all `docs/synthetic/*.md` plus a hand-written intro; re-run it after every merge.
  Never edit the generated table by hand — fix the source registry instead.
- UI badge check: Playwright asserts the "demo data" badge on every screen showing synthetic data.
- Complaint-risk scores are always labelled "311 noise-complaint risk" (v2 §F), never "quality" or "vibe".
- Evaluation-only tables (`syn_true_state`, `syn_scout_truth`) are read only by tests/evaluation code, never by app, API or model features.
- Synthetic primary keys start with `syn-` (v2 §D).
- The swap path is the `INCLUDE_SYNTHETIC` switch + un-prefixed real twin tables (v2 §E); document it, test it, don't invent another.

## 9. Testing requirements
- `make test` runs, in order: existing smoke (`src` import + `simulate.py --n 100` into a temp DB),
  each workstream's own tests (`pytest recs/ backend/`, `npm test --prefix frontend` if present),
  `pytest tests/contract`, then `pytest tests/e2e` (local servers).
- `make test-deployed BASE_URL=... API_URL=...` runs contract + e2e against the deploy.
- Contract tests derive expectations from CONTRACTS.md schemas transcribed into
  `tests/contract/schemas.py` — one place; update only when CONTRACTS.md changes.
- Every bug found during integration gets a regression test before the fix commit.
- Tests are deterministic: pass `now=` and seeds; no wall-clock dependence; no network
  except in `test-deployed`.
- A merge is not "done" until `make test` is green on the integration branch.

## 10. Definition of done (Nov 17)
- [ ] All 8 branches merged (or a documented reason per skipped branch); merge log written.
- [ ] `make test` green locally; `make test-deployed` green 3× in a row.
- [ ] Backend live on Render, frontend live on Vercel, mock mode off, CORS locked to Vercel + localhost.
- [ ] Demo seeded reproducibly (`make seed-demo`, seed 42 → `data/live_sim.db`, row counts + hashes recorded); `DEMO_NOW` 2026-11-14T23:30:00-05:00 shown in the UI clock and `/api/health`.
- [ ] `data/launch_venues_full.csv` committed; Render image excludes `manhattan_bars.db`.
- [ ] G1/G5 golden vectors pass through the API; truth-leak and `INCLUDE_SYNTHETIC=0` tests green.
- [ ] `SYNTHETIC_DATA.md` complete; every `SYNTHETIC:` comment maps to a row; badge on every synthetic screen.
- [ ] README updated (URLs, quickstart, folder map, env table, synthetic warning), original pipeline docs intact.
- [ ] `DEMO.md` demo script rehearsed twice, with fallback (local + recording).
- [ ] `docs/workstreams/integration.md` has: what was built, how to run, merge log,
      fixes applied to others, open issues, contract change requests.
- [ ] Branch pushed; master session notified.
