<!-- header -->
# Scout churn report (synthetic data)

Built by the scripts in `coursework/churn/` (see NOTES.md). All Scouts are SYNTHETIC; nothing here is evidence about real Scouts.
<!-- /header -->

<!-- results -->
## Results: 5 models x (CV on train snapshot, out-of-time test) (synthetic data)

Train snapshot cutoff 2026-10-01: 64 Scouts, base rate 29.7%. Test snapshot cutoff 2026-10-22: 86 Scouts, base rate 36.0%.

| model | settings | split | ROC AUC | PR AUC (base) | Brier | threshold | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|---|
| majority | {} | CV (OOF) | 0.500 (15-fold 0.500 ± 0.000) | 0.297 (0.30) | 0.297 | 0.00 | 0.30 | 1.00 | 0.46 |
| majority | {} | test | 0.500 [0.50, 0.50] | 0.360 (0.36) | 0.360 | 0.00 | 0.36 | 1.00 | 0.53 |
| logistic **(selected)** | {'C': 0.1} | CV (OOF) | 0.836 (15-fold 0.841 ± 0.134) | 0.648 (0.30) | 0.167 | 0.44 | 0.56 | 0.95 | 0.71 |
| logistic **(selected)** | {'C': 0.1} | test | 0.826 [0.73, 0.91] | 0.760 (0.36) | 0.170 | 0.44 | 0.62 | 0.77 | 0.69 |
| tree | {'max_depth': 3} | CV (OOF) | 0.753 (15-fold 0.740 ± 0.097) | 0.580 (0.30) | 0.204 | 0.55 | 0.54 | 0.74 | 0.62 |
| tree | {'max_depth': 3} | test | 0.719 [0.60, 0.82] | 0.496 (0.36) | 0.228 | 0.55 | 0.60 | 0.84 | 0.70 |
| forest | {'min_samples_leaf': 5} | CV (OOF) | 0.781 (15-fold 0.804 ± 0.134) | 0.542 (0.30) | 0.182 | 0.43 | 0.59 | 0.84 | 0.70 |
| forest | {'min_samples_leaf': 5} | test | 0.787 [0.68, 0.88] | 0.651 (0.36) | 0.180 | 0.43 | 0.60 | 0.77 | 0.68 |
| boosting | {'learning_rate': 0.1} | CV (OOF) | 0.667 (15-fold 0.738 ± 0.134) | 0.424 (0.30) | 0.214 | 0.22 | 0.43 | 0.84 | 0.57 |
| boosting | {'learning_rate': 0.1} | test | 0.755 [0.64, 0.86] | 0.602 (0.36) | 0.201 | 0.22 | 0.61 | 0.81 | 0.69 |

Threshold = max F1 on out-of-fold train predictions, then applied unchanged to test. Test ROC AUC brackets are bootstrap 95% CIs (1,000 resamples of Scouts). With under 100 Scouts per snapshot the CIs overlap a lot, so the ranking between the non-baseline models is not reliable; only 'better than the majority baseline' is.

### PRD targets (placeholders) vs result

- Selected model test ROC AUC >= 0.75: **0.826** (met)
- PR AUC lift >= 2x base rate: **2.11x** (met)
- Best test Brier <= logistic regression's: best is logistic (0.170 vs logistic 0.170)
- Snapshot sizes: train 64 Scouts / 19 churners (plan wanted >= 60 / >= 15: met)
<!-- /results -->

<!-- interpretation -->
## Interpretation (synthetic data)

### Logistic regression odds ratios (per +1 standard deviation, sorted by size)

| feature | coef_per_sd | odds_ratio_per_sd |
|---|---|---|
| mean_gap_days | 0.541 | 1.717 |
| median_distance_m | -0.336 | 0.714 |
| active_nights_28d | -0.291 | 0.748 |
| days_since_last_report | 0.290 | 1.336 |
| distinct_venues_28d | -0.272 | 0.762 |
| share_verified_presence | -0.214 | 0.807 |
| reports_7d | -0.208 | 0.812 |
| tenure_days | 0.197 | 1.218 |
| cohort_week | -0.148 | 0.862 |
| trend | -0.141 | 0.869 |
| share_saturday_reports | 0.133 | 1.143 |
| reports_28d | -0.118 | 0.889 |
| share_flagged_or_removed | -0.113 | 0.894 |
| bounties_claimed_28d | 0.098 | 1.103 |
| points_28d | -0.090 | 0.914 |
| reputation_asof | -0.084 | 0.919 |
| points_asof | -0.077 | 0.926 |
| points_total | -0.077 | 0.926 |
| level_asof | -0.034 | 0.966 |

### Decision tree (depth 3), printed

Each leaf shows the class-weighted counts [stay, churn] and the predicted class (1 = churn). Two sibling leaves can both say 1: the split still made one of them purer.

```
|--- mean_gap_days <= 4.8
|   |--- distinct_venues_28d <= 1.5
|   |   |--- weights: [1.4, 8.4] class: 1
|   |--- distinct_venues_28d >  1.5
|   |   |--- reports_7d <= 0.5
|   |   |   |--- weights: [4.3, 6.7] class: 1
|   |   |--- reports_7d >  0.5
|   |   |   |--- weights: [24.9, 0.0] class: 0
|--- mean_gap_days >  4.8
|   |--- days_since_last_report <= 6.5
|   |   |--- weights: [0.0, 11.8] class: 1
|   |--- days_since_last_report >  6.5
|   |   |--- weights: [1.4, 5.1] class: 1
```

### Permutation importance on the test snapshot (logistic, 30 shuffles)

| feature | auc_drop_mean | auc_drop_sd |
|---|---|---|
| days_since_last_report | 0.040 | 0.013 |
| mean_gap_days | 0.017 | 0.020 |
| distinct_venues_28d | 0.016 | 0.009 |
| reports_7d | 0.015 | 0.006 |
| active_nights_28d | 0.013 | 0.010 |
| trend | 0.010 | 0.004 |
| median_distance_m | 0.010 | 0.011 |
| share_flagged_or_removed | 0.007 | 0.003 |
| tenure_days | 0.006 | 0.012 |
| share_saturday_reports | 0.006 | 0.003 |

### Targeting view: churn rate among the riskiest Scouts (test snapshot, logistic)

| riskiest share | scouts | churned | churn rate | lift vs base |
|---|---|---|---|---|
| 10% | 9 | 8 | 0.889 | 2.466 |
| 25% | 22 | 16 | 0.727 | 2.018 |
| 50% | 43 | 26 | 0.605 | 1.677 |

Plots: `timeline.png`, `roc_pr_test.png`, `calibration_test.png`, `permutation_importance.png`.
<!-- /interpretation -->

<!-- truth -->
## Sanity check against the simulator's truth table (evaluation only, synthetic data)

Test snapshot (cutoff 2026-10-22), 86 Scouts.

- Our report-based label (0 reports in 21 days) agrees with the truth 'quit for good before 2026-11-12' for **90%** of Scouts. Disagreements: 1 Scouts were silent for 21 days but had not quit (label 1, truth 0); 8 reported in the window and then quit (label 0, truth 1).
- ROC AUC of the risk score vs our label: 0.826; vs the truth quit flag: 0.840.
- Spearman correlation of risk with `true_accuracy`: -0.15 (accuracy is not a churn driver in the simulator, so a value near 0 is expected).
- AUC is below 0.95, so there is no sign of a 'too easy' leak.

### By archetype

| archetype | n | churn_rate | roc_auc |
|---|---|---|---|
| casual | 32 | 0.312 | 0.823 |
| gamer | 13 | 0.308 | 0.889 |
| honest | 26 | 0.462 | 0.780 |
| shill | 6 | 0.333 | 0.875 |
| sloppy | 9 | 0.333 | 1.000 |

### By cohort week

| cohort_week | n | churn_rate | roc_auc |
|---|---|---|---|
| 0 | 22 | 0.318 | 0.867 |
| 1 | 9 | 0.667 | 0.889 |
| 2 | 9 | 0.556 | 0.900 |
| 3 | 11 | 0.364 | 0.964 |
| 4 | 11 | 0.364 | 0.857 |
| 5 | 10 | 0.200 | 0.750 |
| 6 | 10 | 0.200 | 0.250 |
| 7 | 4 | 0.250 | n/a |
<!-- /truth -->
