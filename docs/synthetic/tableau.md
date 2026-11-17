# Synthetic data registry: tableau

Every synthetic file this workstream creates. All have `is_synthetic = 1` on every row, live
under `analytics/tableau/extracts/synthetic/`, and start with `syn_`. Code spots are marked
`# SYNTHETIC:` (`grep -rn "SYNTHETIC:" analytics/tableau`).

| ID | File | Imitates | How it was generated | Real replacement | Swap steps |
|---|---|---|---|---|---|
| SYN-T1 | `analytics/tableau/extracts/synthetic/syn_tonight_reports.csv` | Scout vibe checks (`syn_scout_reports` v2 columns) at the 35 launch venues, Sat Nov 14 2026 20:00-03:00 ET | `python -I analytics/tableau/export_extracts.py` (or `--placeholder`), `make_placeholder_reports`, seed 42: per venue peak hour from {22,23,0,1}, popularity ~U(0.6,1.4), Poisson reports/hour mean 4 × bell(σ 1.5 h) × popularity, crowd ~ clip(round(N(1+4·curve,0.7)),1,5), dancing 1-2 only at crowd ≥ 4 for 20% of venues, line ~ Gamma(2,4) at crowd ≥ 4 else 0, cover/genre null, 80% verified, status accepted, 60 scouts `syn-s-T1-0001…`, ids `syn-r-T1-000001…`, reputation 0.5 (new-scout default). 523 rows. Only written when no live-sim source exists; when live-sim's `data/live_sim.db` exists it holds the live-sim rows instead (header only if just the snapshot CSV exists) | 1) live-sim `data/live_sim.db` `syn_scout_reports`; 2) real `scout_reports` via backend (`INCLUDE_SYNTHETIC=0`) | Generate `python -I -m simulator --seed 42 --out data/live_sim.db` (or set `LIVE_SIM_DB`), rerun the exporter, check `tonight_source = live-sim`, Tableau Data → Refresh, republish, rerun `render_standin.py` |
| SYN-T2 | `analytics/tableau/extracts/synthetic/syn_tonight_heatmap.csv` | Hourly Live Venue State per launch venue (35 × 7 = 245 rows; cell HH = HH:30 snapshot, v2.2 §J) | Precedence: (1) live-sim `data/synthetic_live/demo_night_snapshots.csv` HH:30 rows; (2) `recs.live_state.compute_all` over live-sim reports if `recs` is importable; (3) local fallback scorer `fallback_state` = specs PRD §5.2-5.6 with v2 §A constants (passes golden vector G1: vibe 65 / conf 0.67) over SYN-T1 or live-sim reports. `display`/`vibe_band` derived per v2 §A / v2.2 §J. Column `source` = `placeholder` or `live-sim` | `GET /api/heatmap?now=2026-11-14T23:30:00-05:00&by=hour` from backend over real reports | Same as SYN-T1; for real data, fetch the API into the same columns (exporter `--tonight-source api` is a later item, see workstream doc) |

Not synthetic (public data, `is_synthetic = 0`): `bars.csv`, `venue_features_slim.csv`,
`launch_venues.csv`, `neighborhood_summary.csv`, `grade_by_neighborhood.csv`.
Evaluation-only tables `syn_true_state` / `syn_scout_truth` are never read.
