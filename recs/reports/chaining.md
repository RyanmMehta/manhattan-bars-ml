# Model chaining — ablation

> **Demo data — synthetic.** Trained/evaluated on live_sim synthetic nights (seed 42). Numbers describe the generator's structure, not real nightlife.

Chain: **clusters** (real public data) → crowd-model feature `cluster_id` → **crowd model** → `predicted_crowd` on live state + arrival-time forecasts in routing → **scoring** → **routing**.

## 1. Does the cluster feature help the crowd model? (holdout Nov 13–14, MAE vs reported crowd)

| variant | MAE |
|---|---|
| crowd model with cluster_id | 0.695 |
| crowd model without cluster_id | 0.696 |
| venue-hour baseline | 0.724 |

Clusters come from public licence/inspection data, which the synthetic generator doesn't use to make crowds, so a near-zero effect is expected here; the link is in place for real data, where venue type should matter.

## 2. Does the crowd forecast improve Run My Night? (holdout nights, plans re-scored on `crowd_true`)

| variant | mean realised objective | mean true-crowd fit of stops |
|---|---|---|
| current state only | 181.4 | 0.614 |
| with crowd model | 185.5 | 0.698 |

| night | start | variant | stops | realised objective | true-crowd fit |
|---|---|---|---|---|---|
| 2026-11-13 | 21:00 | current state only | 3 | 193.0 | 0.833 |
| 2026-11-13 | 21:00 | with crowd model | 3 | 196.0 | 0.833 |
| 2026-11-13 | 22:00 | current state only | 3 | 176.4 | 0.583 |
| 2026-11-13 | 22:00 | with crowd model | 3 | 177.4 | 0.75 |
| 2026-11-13 | 23:00 | current state only | 3 | 175.8 | 0.583 |
| 2026-11-13 | 23:00 | with crowd model | 3 | 183.1 | 0.667 |
| 2026-11-13 | 23:30 | current state only | 3 | 197.7 | 0.583 |
| 2026-11-13 | 23:30 | with crowd model | 3 | 204.6 | 0.75 |
| 2026-11-14 | 21:00 | current state only | 3 | 173.3 | 0.583 |
| 2026-11-14 | 21:00 | with crowd model | 3 | 173.5 | 0.667 |
| 2026-11-14 | 22:00 | current state only | 3 | 154.1 | 0.5 |
| 2026-11-14 | 22:00 | with crowd model | 3 | 173.1 | 0.833 |
| 2026-11-14 | 23:00 | current state only | 3 | 201.6 | 0.833 |
| 2026-11-14 | 23:00 | with crowd model | 3 | 196.8 | 0.667 |
| 2026-11-14 | 23:30 | current state only | 3 | 179.4 | 0.417 |
| 2026-11-14 | 23:30 | with crowd model | 3 | 179.4 | 0.417 |

Realised objective = each planned stop re-scored with the true crowd at its arrival time (evaluation only; `syn_true_state` never reaches the app). The forecast helps most for early starts, when later stops are hours away and current reports say little about them.
