# Manhattan bars - synthetic vs real evaluation

Real venues: 5,704  ·  high_noise base rate: 17.1%  ·  seeds: 3  ·  every score is measured on held-out REAL venues.

## Task A: predict high-noise venues (≥3 noise complaints in 3 years)

| Training data | Model | ROC AUC | PR AUC | F1 |
|---|---|---|---|---|
| TRTR | LogisticRegression | 0.723 ± 0.007 | 0.356 ± 0.010 | 0.192 ± 0.005 |
| TRTR | RandomForest | 0.730 ± 0.007 | 0.354 ± 0.006 | 0.126 ± 0.028 |
| TRTR | GradientBoosting | 0.723 ± 0.001 | 0.368 ± 0.009 | 0.281 ± 0.015 |
| TSTR:independent | LogisticRegression | 0.491 ± 0.064 | 0.173 ± 0.018 | 0.000 ± 0.000 |
| TSTR:independent | RandomForest | 0.504 ± 0.013 | 0.171 ± 0.006 | 0.000 ± 0.000 |
| TSTR:independent | GradientBoosting | 0.470 ± 0.014 | 0.158 ± 0.003 | 0.004 ± 0.006 |
| AUG:independent | LogisticRegression | 0.702 ± 0.006 | 0.325 ± 0.013 | 0.009 ± 0.003 |
| AUG:independent | RandomForest | 0.714 ± 0.009 | 0.341 ± 0.014 | 0.069 ± 0.012 |
| AUG:independent | GradientBoosting | 0.710 ± 0.011 | 0.330 ± 0.023 | 0.054 ± 0.008 |
| TSTR:copula | LogisticRegression | 0.624 ± 0.008 | 0.245 ± 0.003 | 0.007 ± 0.009 |
| TSTR:copula | RandomForest | 0.615 ± 0.019 | 0.238 ± 0.015 | 0.000 ± 0.000 |
| TSTR:copula | GradientBoosting | 0.574 ± 0.009 | 0.219 ± 0.012 | 0.049 ± 0.020 |
| AUG:copula | LogisticRegression | 0.705 ± 0.005 | 0.326 ± 0.016 | 0.030 ± 0.022 |
| AUG:copula | RandomForest | 0.708 ± 0.006 | 0.339 ± 0.009 | 0.057 ± 0.013 |
| AUG:copula | GradientBoosting | 0.715 ± 0.019 | 0.350 ± 0.020 | 0.045 ± 0.015 |
| TSTR:cart | LogisticRegression | 0.704 ± 0.003 | 0.325 ± 0.006 | 0.129 ± 0.020 |
| TSTR:cart | RandomForest | 0.694 ± 0.004 | 0.315 ± 0.013 | 0.095 ± 0.026 |
| TSTR:cart | GradientBoosting | 0.679 ± 0.015 | 0.294 ± 0.013 | 0.199 ± 0.021 |
| AUG:cart | LogisticRegression | 0.722 ± 0.003 | 0.354 ± 0.005 | 0.172 ± 0.001 |
| AUG:cart | RandomForest | 0.722 ± 0.005 | 0.339 ± 0.013 | 0.143 ± 0.015 |
| AUG:cart | GradientBoosting | 0.725 ± 0.007 | 0.340 ± 0.013 | 0.153 ± 0.013 |

## Task B: predict log(1 + noise complaints), gradient boosting

| Training data | MAE (log) | R² (log) | Spearman |
|---|---|---|---|
| TRTR | 0.634 ± 0.012 | 0.104 ± 0.011 | 0.354 ± 0.013 |
| TSTR:independent | 0.735 ± 0.008 | -0.090 ± 0.020 | -0.027 ± 0.015 |
| AUG:independent | 0.691 ± 0.009 | 0.084 ± 0.007 | 0.337 ± 0.012 |
| TSTR:copula | 0.712 ± 0.004 | -0.021 ± 0.019 | 0.132 ± 0.023 |
| AUG:copula | 0.672 ± 0.012 | 0.106 ± 0.009 | 0.339 ± 0.023 |
| TSTR:cart | 0.674 ± 0.027 | 0.013 ± 0.032 | 0.261 ± 0.031 |
| AUG:cart | 0.647 ± 0.015 | 0.109 ± 0.016 | 0.353 ± 0.015 |

## Fidelity and privacy of each generator

| Generator | mean KS ↓ | mean TVD ↓ | corr error ↓ | discriminator AUC (0.5 best) | DCR ratio (≈1 good, ≪1 copies) | exact copies |
|---|---|---|---|---|---|---|
| independent | 0.011 ± 0.001 | 0.008 ± 0.001 | 0.208 ± 0.001 | 0.999 ± 0.000 | 1.67 ± 0.04 | 0.0% |
| copula | 0.012 ± 0.002 | 0.007 ± 0.000 | 0.027 ± 0.004 | 0.993 ± 0.001 | 1.38 ± 0.03 | 0.0% |
| cart | 0.011 ± 0.001 | 0.008 ± 0.001 | 0.017 ± 0.003 | 0.424 ± 0.006 | 0.94 ± 0.01 | 0.1% |

## Worst-matched columns per generator (KS or TVD)

- **independent**: cuisine 0.020, neighborhood 0.018, years_licensed 0.015, noise_complaints 0.013, lat 0.013
- **copula**: neighborhood 0.022, cuisine 0.019, density_100m 0.017, max_score 0.015, n_violations 0.014
- **cart**: neighborhood 0.027, years_licensed 0.020, cuisine 0.017, lon 0.015, density_100m 0.015
