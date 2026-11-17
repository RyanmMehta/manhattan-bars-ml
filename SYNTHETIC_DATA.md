# Synthetic data in this repo

> **Generated** by `scripts/integration/consolidate_synthetic.py` (`make synthetic-docs`) from
> every `docs/synthetic/<workstream>.md`. Edit those files, not this one.

Nightlife Autopilot has **no real live data yet**. Everything about "tonight" (scout reports,
venue updates, crowds, users, points, bounties, owner analytics, interview data) is
**synthetic**, generated deterministically (seed 42) for the Nov 17 class demo. The only real
data is the public-data pipeline: NY SLA licences, NYC DOHMH inspections, NYC 311 noise
complaints and OpenStreetMap (`data/manhattan_bars.db`, `data/launch_venues*.csv`).

How to spot it (CONTRACTS.md "Synthetic data rule"):
1. every synthetic table/CSV has `is_synthetic = 1`;
2. synthetic files live under a path containing `synthetic`; synthetic DB tables start with `syn_`;
   synthetic primary keys start with `syn-`;
3. code that reads synthetic data is marked `# SYNTHETIC: <real source>` / `// SYNTHETIC:`;
4. the UI shows a **demo data** badge wherever synthetic data is shown.

## The global swap switch (step 1 of every swap)

Every app table has a real twin without the `syn_` prefix (`scout_reports`, `venue_updates`,
`venue_events`, `feedback`, `bounties`, `disputes`, `points_ledger`), created empty by the
backend from day one. The backend reads `syn_x UNION ALL x`.

1. Start writing real rows into the un-prefixed twin (the app's POST endpoints already do).
2. When the real table has enough data, set `INCLUDE_SYNTHETIC=0` on the backend (Render env).
   `/api/health` then reports `"data": "real"` and lists return `X-Data: real`.
3. Stop running `python -I -m simulator --seed 42 --out data/live_sim.db` in the build and unset
   `DEMO_NOW` / `VITE_DEMO_NOW` so the app uses the wall clock.
4. Remove the dataset's `SYNTHETIC:` code paths listed below and its row in the owner's registry.

Checked by `tests/contract/test_isolation.py::test_include_synthetic_off`.

## Evaluation-only tables (never swapped into the app)

`syn_true_state` and `syn_scout_truth` are the simulator's hidden ground truth. They are read
only by evaluation/test code, never by `backend/`, `recs/` runtime or model features
(checked by `tests/contract/test_isolation.py`). With real data they simply disappear;
evaluation then uses post-visit feedback and audits instead.

## Master index

| owner | dataset (file/table) | imitates | real replacement | swap steps |
|---|---|---|---|---|
| integration | `DEMO_NOW` / `VITE_DEMO_NOW` pinned clock (`2026-11-14T23:30:00-05:00`) | "right now" on a busy Saturday | the wall clock | unset `DEMO_NOW` on Render and `VITE_DEMO_NOW` on Vercel; redeploy |
| integration | G1/G5 report fixtures inline in `tests/contract/test_recs_interface.py` | four scout reports at one venue | not replaced (unit-test fixture) | none; keep as regression tests |

### Pre-existing public-pipeline synthetic data

`data/synthetic/*` and the `synthetic_{independent,copula,cart}_10000` tables in `data/manhattan_bars.db` are synthetic *training* rows from `src/simulate.py` (see README §3). They imitate `venue_features` and are not used by the app.

## Per-workstream registries

### integration  (`docs/synthetic/integration.md`)

### Synthetic data registry — integration

| Dataset (file/table) | Imitates | How generated | Real replacement | Swap steps |
|---|---|---|---|---|
| `DEMO_NOW` / `VITE_DEMO_NOW` pinned clock (`2026-11-14T23:30:00-05:00`) | "right now" on a busy Saturday | config constant (CONTRACTS v2 §B) | the wall clock | unset `DEMO_NOW` on Render and `VITE_DEMO_NOW` on Vercel; redeploy |
| G1/G5 report fixtures inline in `tests/contract/test_recs_interface.py` | four scout reports at one venue | hand-copied from specs golden vector G1 | not replaced (unit-test fixture) | none; keep as regression tests |

No `data/synthetic_demo/` overrides or `tests/fixtures/synthetic/` fixture were needed so far
(updated at each merge; see `docs/workstreams/integration.md`).

## `SYNTHETIC:` code markers

| folder | count |
|---|---|
| `scripts/` | 1 |
| `tests/` | 1 |
| **total** | **2** |

_Generated from 1 registries at commit `f528ac8`._
