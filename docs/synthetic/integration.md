# Synthetic data registry — integration

| Dataset (file/table) | Imitates | How generated | Real replacement | Swap steps |
|---|---|---|---|---|
| `DEMO_NOW` / `VITE_DEMO_NOW` pinned clock (`2026-11-14T23:30:00-05:00`) | "right now" on a busy Saturday | config constant (CONTRACTS v2 §B) | the wall clock | unset `DEMO_NOW` on Render and `VITE_DEMO_NOW` on Vercel; redeploy |
| G1/G5 report fixtures inline in `tests/contract/test_recs_interface.py` | four scout reports at one venue | hand-copied from specs golden vector G1 | not replaced (unit-test fixture) | none; keep as regression tests |

No `data/synthetic_demo/` overrides or `tests/fixtures/synthetic/` fixture were needed so far
(updated at each merge; see `docs/workstreams/integration.md`).
