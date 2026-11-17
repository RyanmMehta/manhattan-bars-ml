# Synthetic data registry: ml-recs

Every synthetic dataset or artifact that `recs/` creates or consumes. Code spots carry `# SYNTHETIC:` comments.

| File / table | Imitates | How generated | Real replacement | Swap steps |
|---|---|---|---|---|
| `data/live_sim.db` `syn_scout_reports`, `syn_scouts`, `syn_scout_reputation_history`, `syn_venue_updates`, `syn_venue_attributes` (live-sim, consumed) | scout vibe checks, reputation, operator posts, venue facts, 36 Thu–Sat nights | live-sim, `python -m simulator --seed 42` | app tables `scout_reports`, `scouts`, `scout_reputation_history`, `venue_updates`; `data/venue_attributes_manual.csv` | backend passes real rows (`INCLUDE_SYNTHETIC=0`); recs code unchanged; `python -m recs eval` to retrain |
| `data/live_sim.db` `syn_true_state`, `syn_scout_truth` (live-sim, evaluation only) | ground truth | live-sim | none in production (field audits) | read only by `crowd_model.evaluate` / `true_crowd_lookup` / `chain.ablation`; drop truth metrics from reports |
| `recs/synthetic/stub_nights.py` output (in memory) | the same syn_* tables, used only when no `live_sim.db` | Poisson report arrivals ∝ true crowd; style-specific hour curves; scout archetypes (honest/casual/sloppy/gamer/shill); nightly reputation update; seed 42 | `data/live_sim.db`, then real tables | build `live_sim.db` (`make data`) or set `LIVE_SIM_DB`; recs prefers it automatically; delete the stub when live data is permanent |
| `recs/artifacts/synthetic/crowd_model.joblib` + `.json` (`is_synthetic: true`) | demand model (crowd by venue × hour) | `python -m recs train-crowd` on live-sim data (origin/nightlife/live-sim beaa382) | retrain on ≥ 4 weeks of real `scout_reports` | `python -m recs train-crowd` with real data; move out of `synthetic/`; set `is_synthetic: false` |
| `recs/reports/crowd_model.md`, `chaining.md`, `routing.md` | evaluation write-ups | `python -m recs eval` | re-run on real data | each starts with a "Demo data — synthetic" banner |
| `data/synthetic_live/demo_night_snapshots.csv` (live-sim writes; values come from `recs.chain.snapshots`) | Live State every 30 min, Sat Nov 14 20:00–03:00 | `python -m recs snapshots --out …` | not needed with real data (backend computes live) | regenerate after any `live_state` change |
| `recs/tests/golden_recs_derived/G1–G8.json` | worked examples | hand-derived by ml-recs from specs PRD §5 before specs pushed theirs | stays synthetic (tests) | none |
| `recs/tests/specs_copy/` (copy of specs' `golden_synthetic/`, `PARAMETERS.md`, `tools/reference_scoring.py`) | specs' golden vectors + oracle | specs | stays synthetic (tests) | re-copy when specs changes; tests use `docs/specs/` when present |
| `recs/tests/fixtures/synthetic/*.csv` (`syn-v-*`, `syn-s-*`, `syn-r-*`, `syn-u-*`) | a tiny night: 5 venues, 3 scouts, 40 reports, 4 updates | one-off seeded script (seed 42) | stays synthetic (tests) | none |
| `recs/examples/prefs_*.json` | a group's preferences | hand-written | real user prefs from the request | none |

Not synthetic: `recs/artifacts/clusters.*` and `recs/artifacts/complaint_risk.*` are trained on real public data
(`data/manhattan_bars.db`), `is_synthetic: false`.
