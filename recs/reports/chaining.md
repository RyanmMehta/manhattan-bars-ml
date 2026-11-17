# Model chaining — ablation

> **Demo data — synthetic.** Trained/evaluated on stub synthetic nights (seed 42). Numbers describe the generator's structure, not real nightlife.

Chain: **clusters** (real public data) → crowd-model feature `cluster_id` → **crowd model** → `predicted_crowd` on live state + arrival-time forecasts in routing → **scoring** → **routing**.

## 1. Does the cluster feature help the crowd model? (holdout Nov 13–14, MAE vs reported crowd)

| variant | MAE |
|---|---|
| crowd model with cluster_id | 0.609 |
| crowd model without cluster_id | 0.606 |
| venue-hour baseline | 0.627 |

Clusters come from public licence/inspection data, which the synthetic generator doesn't use to make crowds, so a near-zero effect is expected here; the link is in place for real data, where venue type should matter.

## 2. Does the crowd forecast improve Run My Night? (holdout nights, plans re-scored on `crowd_true`)

| variant | mean realised objective | mean true-crowd fit of stops |
|---|---|---|
| current state only | 226.2 | 0.747 |
| with crowd model | 228.4 | 0.768 |

| night | start | variant | stops | realised objective | true-crowd fit |
|---|---|---|---|---|---|
| 2026-11-13 | 21:00 | current state only | 3 | 219.9 | 0.927 |
| 2026-11-13 | 21:00 | with crowd model | 3 | 224.5 | 0.941 |
| 2026-11-13 | 22:00 | current state only | 3 | 225.5 | 0.792 |
| 2026-11-13 | 22:00 | with crowd model | 3 | 228.3 | 0.858 |
| 2026-11-13 | 23:00 | current state only | 3 | 225.8 | 0.653 |
| 2026-11-13 | 23:00 | with crowd model | 3 | 232.2 | 0.752 |
| 2026-11-13 | 23:30 | current state only | 3 | 241.8 | 0.616 |
| 2026-11-13 | 23:30 | with crowd model | 3 | 241.8 | 0.616 |
| 2026-11-14 | 21:00 | current state only | 3 | 215.3 | 0.836 |
| 2026-11-14 | 21:00 | with crowd model | 3 | 219.4 | 0.827 |
| 2026-11-14 | 22:00 | current state only | 3 | 220.2 | 0.765 |
| 2026-11-14 | 22:00 | with crowd model | 3 | 220.2 | 0.765 |
| 2026-11-14 | 23:00 | current state only | 3 | 227.2 | 0.728 |
| 2026-11-14 | 23:00 | with crowd model | 3 | 227.2 | 0.728 |
| 2026-11-14 | 23:30 | current state only | 3 | 234.0 | 0.658 |
| 2026-11-14 | 23:30 | with crowd model | 3 | 234.0 | 0.658 |

Realised objective = each planned stop re-scored with the true crowd at its arrival time (evaluation only; `syn_true_state` never reaches the app). The forecast helps most for early starts, when later stops are hours away and current reports say little about them.
