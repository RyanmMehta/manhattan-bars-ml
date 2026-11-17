<!-- header -->
# Scout churn report (synthetic data)

Built by the scripts in `coursework/churn/` (see NOTES.md). All Scouts are SYNTHETIC; nothing here is evidence about real Scouts.
<!-- /header -->

<!-- results -->
## Results: 5 models x (CV on train snapshot, out-of-time test) (synthetic data)

Train snapshot cutoff 2026-10-01: 86 Scouts, base rate 31.4%. Test snapshot cutoff 2026-10-22: 101 Scouts, base rate 40.6%.

| model | settings | split | ROC AUC | PR AUC (base) | Brier | threshold | precision | recall | F1 |
|---|---|---|---|---|---|---|---|---|---|
| majority | {} | CV (OOF) | 0.500 (15-fold 0.500 ± 0.000) | 0.314 (0.31) | 0.314 | 0.00 | 0.31 | 1.00 | 0.48 |
| majority | {} | test | 0.500 [0.50, 0.50] | 0.406 (0.41) | 0.406 | 0.00 | 0.41 | 1.00 | 0.58 |
| logistic **(selected)** | {'C': 0.1} | CV (OOF) | 0.885 (15-fold 0.887 ± 0.045) | 0.706 (0.31) | 0.137 | 0.39 | 0.63 | 0.89 | 0.74 |
| logistic **(selected)** | {'C': 0.1} | test | 0.852 [0.77, 0.92] | 0.780 (0.41) | 0.148 | 0.39 | 0.70 | 0.78 | 0.74 |
| tree | {'max_depth': 4} | CV (OOF) | 0.829 (15-fold 0.811 ± 0.087) | 0.626 (0.31) | 0.166 | 0.35 | 0.62 | 0.89 | 0.73 |
| tree | {'max_depth': 4} | test | 0.788 [0.71, 0.87] | 0.646 (0.41) | 0.204 | 0.35 | 0.64 | 0.83 | 0.72 |
| forest | {'min_samples_leaf': 20} | CV (OOF) | 0.873 (15-fold 0.883 ± 0.052) | 0.754 (0.31) | 0.171 | 0.55 | 0.77 | 0.74 | 0.75 |
| forest | {'min_samples_leaf': 20} | test | 0.864 [0.79, 0.93] | 0.846 (0.41) | 0.165 | 0.55 | 0.77 | 0.73 | 0.75 |
| boosting | {'learning_rate': 0.1} | CV (OOF) | 0.845 (15-fold 0.859 ± 0.064) | 0.634 (0.31) | 0.150 | 0.51 | 0.74 | 0.74 | 0.74 |
| boosting | {'learning_rate': 0.1} | test | 0.840 [0.76, 0.91] | 0.787 (0.41) | 0.167 | 0.51 | 0.76 | 0.68 | 0.72 |

Threshold = max F1 on out-of-fold train predictions, then applied unchanged to test. Test ROC AUC brackets are bootstrap 95% CIs (1,000 resamples of Scouts). With only about 60-100 Scouts per snapshot the CIs overlap a lot, so the ranking between the non-baseline models is not reliable; only 'better than the majority baseline' is.

### PRD targets (placeholders) vs result

- Selected model test ROC AUC >= 0.75: **0.852** (met)
- PR AUC lift >= 2x base rate: **1.92x** (MISSED; the most any model can reach at this base rate is 1/0.406 = 2.46x)
- Best test Brier <= logistic regression's: best is logistic (0.148 vs logistic 0.148)
- Snapshot sizes: train 86 Scouts / 27 churners (plan wanted >= 60 / >= 15: met)
<!-- /results -->

<!-- interpretation -->
## Interpretation (synthetic data)

### Logistic regression odds ratios (per +1 standard deviation, sorted by size)

| feature | coef_per_sd | odds_ratio_per_sd |
|---|---|---|
| reports_7d | -0.438 | 0.645 |
| trend | -0.340 | 0.712 |
| points_28d | -0.273 | 0.761 |
| bounties_claimed_28d | -0.254 | 0.775 |
| cohort_week | -0.245 | 0.783 |
| days_since_last_report | 0.239 | 1.270 |
| reports_28d | -0.210 | 0.810 |
| points_total | -0.186 | 0.831 |
| points_asof | -0.185 | 0.831 |
| active_nights_28d | -0.134 | 0.874 |
| tenure_days | 0.120 | 1.128 |
| mean_gap_days | 0.118 | 1.125 |
| reputation_asof | 0.101 | 1.106 |
| distinct_venues_28d | -0.082 | 0.921 |
| share_flagged_or_removed | 0.082 | 1.085 |
| share_verified_presence | 0.046 | 1.047 |
| share_saturday_reports | -0.020 | 0.980 |
| level_asof | -0.018 | 0.982 |
| median_distance_m | 0.003 | 1.003 |

### Decision tree (depth 4), printed

Each leaf shows the class-weighted counts [stay, churn] and the predicted class (1 = churn). Two sibling leaves can both say 1: the split still made one of them purer.

```
|--- reports_7d <= 6.5
|   |--- reports_28d <= 35.5
|   |   |--- share_saturday_reports <= 0.7
|   |   |   |--- points_28d <= 615.0
|   |   |   |   |--- weights: [1.5, 31.9] class: 1
|   |   |   |--- points_28d >  615.0
|   |   |   |   |--- weights: [2.2, 3.2] class: 1
|   |   |--- share_saturday_reports >  0.7
|   |   |   |--- weights: [2.9, 3.2] class: 1
|   |--- reports_28d >  35.5
|   |   |--- weights: [4.4, 1.6] class: 0
|--- reports_7d >  6.5
|   |--- share_saturday_reports <= 0.5
|   |   |--- weights: [29.9, 0.0] class: 0
|   |--- share_saturday_reports >  0.5
|   |   |--- weights: [2.2, 3.2] class: 1
```

### Permutation importance on the test snapshot (logistic, 30 shuffles)

| feature | auc_drop_mean | auc_drop_sd |
|---|---|---|
| reports_7d | 0.017 | 0.018 |
| cohort_week | 0.015 | 0.013 |
| trend | 0.009 | 0.010 |
| points_asof | 0.008 | 0.005 |
| points_total | 0.008 | 0.005 |
| bounties_claimed_28d | 0.007 | 0.006 |
| points_28d | 0.007 | 0.007 |
| days_since_last_report | 0.006 | 0.008 |
| reports_28d | 0.003 | 0.007 |
| distinct_venues_28d | 0.002 | 0.003 |

### Targeting view: churn rate among the riskiest Scouts (test snapshot, logistic)

| riskiest share | scouts | churned | churn rate | lift vs base |
|---|---|---|---|---|
| 10% | 10 | 9 | 0.900 | 2.217 |
| 25% | 25 | 21 | 0.840 | 2.069 |
| 50% | 50 | 33 | 0.660 | 1.626 |

Plots: `timeline.png`, `roc_pr_test.png`, `calibration_test.png`, `permutation_importance.png`.
<!-- /interpretation -->

<!-- truth -->
## Sanity check against the simulator's truth table (evaluation only, synthetic data)

Test snapshot (cutoff 2026-10-22), 101 Scouts.

- Our report-based label (0 reports in 21 days) agrees with the truth 'quit for good before 2026-11-12' for **82%** of Scouts. Disagreements: 6 Scouts were silent for 21 days but had not quit (label 1, truth 0); 12 reported in the window and then quit (label 0, truth 1).
- ROC AUC of the risk score vs our label: 0.852; vs the truth quit flag: 0.710.
- Spearman correlation of risk with `true_accuracy`: +0.07 (near 0 means the risk score is not just tracking how accurate a Scout's reports are).
- AUC is below 0.95, so there is no sign of a 'too easy' leak.

### By archetype

| archetype | n | churn_rate | roc_auc |
|---|---|---|---|
| casual | 28 | 0.429 | 0.802 |
| gamer | 2 | 0.500 | n/a |
| honest | 60 | 0.417 | 0.893 |
| shill | 3 | 0.333 | n/a |
| sloppy | 8 | 0.250 | 0.917 |

### By cohort week

| cohort_week | n | churn_rate | roc_auc |
|---|---|---|---|
| 1 | 34 | 0.382 | 0.857 |
| 2 | 10 | 0.600 | 0.792 |
| 3 | 8 | 0.375 | 0.933 |
| 4 | 7 | 0.429 | 0.917 |
| 5 | 10 | 0.500 | 1.000 |
| 6 | 7 | 0.571 | 1.000 |
| 7 | 11 | 0.182 | 0.889 |
| 8 | 14 | 0.357 | 0.733 |
<!-- /truth -->
