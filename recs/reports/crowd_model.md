# Crowd model — baseline vs gradient boosting

> **Demo data — synthetic.** Trained/evaluated on stub synthetic nights (seed 42). Numbers describe the generator's structure, not real nightlife.

Rows: venue × night × hour slot with ≥ 1 eligible report (5356 rows, 36 Thu–Sat nights). Target: reputation-weighted mean reported crowd (1–5); report weights use reputation **as of the report night** (`syn_scout_reputation_history`).

Model: `HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=42)`; features: slot, weekday, week, style, has_dance_floor, capacity, price_level, typical_cover_usd, density_100m, osm_closes_late, years_licensed, liquor_tier, cluster_id, venue_te. `venue_te` is a train-nights-only venue mean. `syn_true_state` / `syn_scout_truth` are never features.

Split: train Aug 27 → Nov 12, **hold out Nov 13–14** (CONTRACTS §B) + 3 rolling-origin folds of 2 nights.

## Results (MAE / RMSE / Spearman)

| fold | train nights | reference | model | venue-hour baseline | global slot mean |
|---|---|---|---|---|---|
| holdout | 34 | reported | 0.609 / 0.768 / 0.75 | 0.627 / 0.768 / 0.77 | 0.778 / 0.970 / 0.59 |
| holdout | 34 | true | 0.358 / 0.451 / 0.91 | 0.353 / 0.434 / 0.93 | 0.630 / 0.791 / 0.71 |
| rolling_1 | 28 | reported | 0.611 / 0.786 / 0.76 | 0.617 / 0.809 / 0.76 | 0.788 / 0.989 / 0.60 |
| rolling_1 | 28 | true | 0.344 / 0.426 / 0.93 | 0.339 / 0.419 / 0.93 | 0.598 / 0.765 / 0.73 |
| rolling_2 | 30 | reported | 0.554 / 0.704 / 0.79 | 0.573 / 0.750 / 0.77 | 0.768 / 0.942 / 0.60 |
| rolling_2 | 30 | true | 0.315 / 0.396 / 0.94 | 0.326 / 0.411 / 0.92 | 0.623 / 0.782 / 0.69 |
| rolling_3 | 32 | reported | 0.605 / 0.742 / 0.81 | 0.617 / 0.777 / 0.80 | 0.848 / 1.032 / 0.57 |
| rolling_3 | 32 | true | 0.333 / 0.422 / 0.93 | 0.374 / 0.469 / 0.92 | 0.662 / 0.819 / 0.68 |

Holdout MAE ratio model / baseline = **0.971** (target ≤ 0.9, placeholder): the model does **not** meet the target. The baseline is strong because the generator's crowd is mostly venue × hour; the model's edge comes from weekday/week effects and pooling across similar venues for thin venue-slots.

Against `crowd_true` (evaluation only) errors are lower than against reports, because reports add scout noise the model cannot predict.

Artifact: `recs/artifacts/synthetic/crowd_model.joblib` (+ `.json`), trained on all nights before the holdout. Regenerate: `python -m recs train-crowd`.
