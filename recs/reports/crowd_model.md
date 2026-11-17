# Crowd model — baseline vs gradient boosting

> **Demo data — synthetic.** Trained/evaluated on live_sim synthetic nights (seed 42). Numbers describe the generator's structure, not real nightlife.

Rows: venue × night × hour slot with ≥ 1 eligible report (4479 rows, 36 Thu–Sat nights). Target: reputation-weighted mean reported crowd (1–5); report weights use reputation **as of the report night** (`syn_scout_reputation_history`).

Model: `HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=42)`; features: slot, weekday, style, has_dance_floor, capacity, density_100m, osm_closes_late, cluster_id, venue_te, venue_slot_te, venue_weekday_te. The `*_te` features are train-nights-only target means (venue, venue×slot, venue×weekday). `week` was dropped: it extrapolated badly into the holdout weeks. `syn_true_state` / `syn_scout_truth` are never features.

Split: train Aug 27 → Nov 12, **hold out Nov 13–14** (CONTRACTS §B) + 3 rolling-origin folds of 2 nights.

## Results (MAE / RMSE / Spearman)

| fold | train nights | reference | model | venue-hour baseline | global slot mean |
|---|---|---|---|---|---|
| holdout | 34 | reported | 0.695 / 0.893 / 0.74 | 0.724 / 0.930 / 0.72 | 1.068 / 1.250 / 0.37 |
| holdout | 34 | true | 0.568 / 0.719 / 0.85 | 0.603 / 0.771 / 0.83 | 1.049 / 1.229 / 0.45 |
| rolling_1 | 28 | reported | 0.710 / 0.950 / 0.73 | 0.759 / 1.005 / 0.69 | 1.172 / 1.352 / 0.33 |
| rolling_1 | 28 | true | 0.561 / 0.729 / 0.87 | 0.596 / 0.783 / 0.84 | 1.141 / 1.315 / 0.42 |
| rolling_2 | 30 | reported | 0.698 / 0.893 / 0.73 | 0.767 / 0.982 / 0.68 | 1.076 / 1.252 / 0.32 |
| rolling_2 | 30 | true | 0.564 / 0.721 / 0.83 | 0.629 / 0.801 / 0.78 | 1.032 / 1.192 / 0.37 |
| rolling_3 | 32 | reported | 0.574 / 0.771 / 0.81 | 0.615 / 0.811 / 0.79 | 1.018 / 1.216 / 0.36 |
| rolling_3 | 32 | true | 0.468 / 0.589 / 0.91 | 0.506 / 0.655 / 0.89 | 1.003 / 1.186 / 0.44 |

Holdout MAE ratio model / baseline = **0.960** (target ≤ 0.9, placeholder): the model does **not** meet the target. The baseline is strong because the generator's crowd is mostly venue × hour; the model's edge comes from pooling across similar venues and slots where a venue's own history is thin.

Against `crowd_true` (evaluation only) errors are lower than against reports, because reports add scout noise the model cannot predict.

Artifact: `recs/artifacts/synthetic/crowd_model.joblib` (+ `.json`), trained on all nights before the holdout. Regenerate: `python -m recs train-crowd`.
