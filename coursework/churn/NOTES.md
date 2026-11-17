# Scout churn model: explanation notes

What this is: a model that predicts which **Scouts** (users who send 10-second vibe checks from
bars) will stop reporting. It compares a majority-class baseline, logistic regression and three
tree models, using a split by time so the model cannot see the future.

**All Scout data here is SYNTHETIC.** On Nov 17 the live-sim branch had no simulator code yet, so
`data/live_sim.db` could not be built. The planned fallback, `make_standin_data.py`, creates Scouts
with the same columns as the contract tables. When `data/live_sim.db` exists, the same scripts read
it instead with no code change (see `docs/synthetic/coursework.md`). Nothing here is evidence about
real people.

How to run (from the repo root):

```bash
python -I coursework/churn/make_standin_data.py --seed 0   # only while data/live_sim.db is missing
python -I coursework/churn/build_dataset.py                # one row per Scout, two snapshots
python -I coursework/churn/train_eval.py                   # 5 models, CV + out-of-time test
python -I coursework/churn/explain.py                      # odds ratios, tree, importance, plots
python -I coursework/churn/evaluate_truth.py               # sanity check vs the hidden truth table
```

Results are in `outputs/report.md` and `outputs/metrics.json`. Plots are in `outputs/*.png`.

---

## [N1] The business question

**What it does.** Nightlife Autopilot shows a `confidence` score for each venue's live state.
Confidence goes up with more fresh reports from trusted Scouts. If Scouts quietly stop reporting,
confidence falls, venues show "No fresh reports", and the app becomes less useful. So the question
is: **which currently active Scouts are likely to go quiet in the next 3 weeks?** Then we can aim
bounties or points at them *before* they leave. The model ranks Scouts by risk. It does not decide
anything by itself.

**Code.** `train_eval.py` docstring ("Goal"), `explain.py:top_risk_table`

**Example.** If the riskiest 10% of Scouts churn at 89% and the average Scout at 36%, a limited
bounty budget spent on that 10% reaches far more of the Scouts we are about to lose.

**Common mistake.** Predicting churn for Scouts who have *already* stopped. That is easy, and it is
useless. We only score Scouts who were active in the last 28 days (N2).

**Check yourself.** Why does Scout churn hurt the product even if the total number of users stays the same?

## [N2] The churn definition and the time windows

**What it does.** We take a **snapshot** at a cutoff time and ask two separate questions:

- **Eligible?** Joined before the cutoff **and** made at least 1 (non-removed) report in the
  **28 days before** the cutoff.
- **Churned (label = 1)?** Made **0 reports in the 21 days from** the cutoff (CONTRACTS v2.1 §B).

There are two snapshots, both on Thursdays at 12:00 ET, so no Thu–Sat night is cut in half:

| snapshot | features use | label window | Scouts | churned | base rate |
|---|---|---|---|---|---|
| train | reports before **Oct 1** | Oct 1 – Oct 21 | 64 | 19 | 29.7% |
| test | reports before **Oct 22** | Oct 22 – Nov 11 | 86 | 31 | 36.0% |

The train label window ends exactly where the test snapshot begins, so no test-period outcome is
used in training. Nov 12–14 is unused, because it is too short for a 21-day window. See
`outputs/timeline.png`.

A "night" runs from 6 pm to 4 am and belongs to its start date: a report at 01:30 on Sunday counts
as Saturday night (`night_of`).

**Code.** `build_dataset.py:build` (eligibility and label), `build_dataset.py:cutoff_ts`, `night_of`,
and `explain.py:plot_timeline`. Tests: `tests/test_churn_features.py:test_labels_and_eligibility`.

**Example (test fixture).** Scout 1 reports on Oct 3 → label 0. Scout 2's only report in the window
is `removed`, and the next one is on Oct 25 (after Oct 21) → label 1. Scout 3 joined on Oct 5 → not eligible.

**Common mistake.** Labelling everyone with no *future* activity as churned, including people who were
already inactive. That inflates the base rate and makes the model look smart for spotting people who had already left.

**Check yourself.** Why do the cutoffs fall on Thursdays at noon? What happens to a Scout who joined on Sep 29?

## [N3] Features, and why each might matter

All features use only rows with `ts < cutoff`. Removed reports do not count as activity, but they do
count toward the quality share.

| feature | meaning | why it might predict churn |
|---|---|---|
| tenure_days | days since joining | novelty wears off |
| cohort_week | week number of joining (0 = launch week) | early and late joiners may differ |
| reports_28d, reports_7d | reports in the last 28 / 7 days | low activity comes before stopping |
| days_since_last_report | recency | the strongest "going quiet" signal |
| active_nights_28d | distinct nights with a report (max 12) | habit strength |
| mean_gap_days | average gap between active nights | long gaps = weak habit |
| trend | reports_7d − (weekly rate of the 21 days before) | slowing down |
| share_verified_presence | share of reports with GPS presence | engaged Scouts are really there |
| share_flagged_or_removed | share of reports flagged/removed | bad experiences may push people out |
| median_distance_m | median distance to the venue when verified | data quality |
| distinct_venues_28d | different venues reported | breadth of use |
| share_saturday_reports | share on Saturday nights | weekend-only Scouts |
| points_28d, points_total | points earned (summed from `syn_points_ledger`) | rewards keep people |
| bounties_claimed_28d | bounties claimed in the last 28 days | rewards keep people |
| reputation_asof, points_asof, level_asof | from the reputation **history**, as of the day before the cutoff | standing in the community |

Missing values: `mean_gap_days` is missing for a Scout with only one active night, and
`median_distance_m` is missing for a Scout who was never verified. Both are filled with the training
median **inside** the model pipeline (`SimpleImputer`), so each CV fold computes its own median.

**Code.** `build_dataset.py:FEATURES`, `activity_features`, `asof_reputation`, `build`.
Test: `test_hand_computed_features`.

**Example (fixture Scout 1 at the Oct 1 cutoff).** Reports on Sep 10, Sep 25 and Sep 27 01:00 →
reports_28d = 3, reports_7d = 2, the Sep 27 report counts as a Saturday night, so
share_saturday_reports = 1/3, and 1 of its 3 reports was flagged → share_flagged_or_removed = 1/3.

**Common mistake.** Building features from the whole table and then splitting. The features would
include post-cutoff activity.

**Check yourself.** Pick two features and argue for opposite signs. Which one does the data support (N9)?

## [N4] Leakage and why we split by time

**What it does.** **Leakage** means the model sees information it would not have at prediction time.
It is the most common way churn models end up looking far better than they are. We guard against three kinds:

1. **Time leakage.** Features use `ts < cutoff`, and the label uses `[cutoff, cutoff + 21 d)`.
   `test_no_leakage_post_cutoff_rows_do_not_change_features` deletes every row after the cutoff and
   checks that the features do not change.
2. **Snapshot leakage.** `syn_scouts.reputation / points / level / reports_count / last_active_at`
   are values at the **end** of the simulation. A Scout who churned in October has a low
   `reports_count` and an early `last_active_at`. Using those columns would give away the label. They are never
   features (`test_snapshot_columns_never_features`). Reputation, points and level come from
   `syn_scout_reputation_history`, taking the latest row with `as_of_date < cutoff`
   (`test_asof_reputation_not_final_snapshot`: it must return 0.60 and not 0.90 or 0.99).
3. **Truth leakage.** The simulator's hidden table (archetype, true churn date) is read only by
   `evaluate_truth.py`. A test greps the other files to enforce this.

**Why split by time and not randomly.** In real use, we train on the past and predict the future.
A random split mixes Scouts from the same weeks into train and test, so the model gets credit for
learning that particular period. Our **out-of-time** test snapshot (Oct 22) is later than everything
used to train or choose the model, which is the honest version of "how will this do next month".

**Code.** `build_dataset.py:build` (`past` / `future`), `build_dataset.py:asof_reputation`,
`tests/test_churn_features.py`

**Common mistake.** Joining today's reputation onto old reports (CONTRACTS v2.1 §E warns about exactly this).

**Check yourself.** Why split churn data by time and not randomly? Give an example of a feature that would leak.

## [N5] Baselines and class imbalance

**What it does.** The **majority** baseline (`DummyClassifier(most_frequent)`) always predicts "stays".
Its ROC AUC is 0.5 by definition, and its PR AUC equals the base rate (0.30 in train, 0.36 in test). Every
real model has to beat it. Its "accuracy" would be 64% on test without learning anything, which is
why accuracy is not used (N8).

About 30–36% of Scouts churn, so the classes are **imbalanced**. Logistic regression, the tree and
the forest use `class_weight="balanced"`, which weights the minority class more in the loss so the
model does not just predict "stays". Gradient boosting was left at its defaults, with no class weights
(the plan's grid only varies the learning rate). That is one reason its probabilities are low and
its chosen threshold is 0.22. We do not oversample (no SMOTE). With so few rows, made-up rows
would mostly add noise.

Every model is a **Pipeline**: imputation (and for logistic regression, scaling) is fitted on the
training rows only, inside each CV fold.

**Code.** `train_eval.py:make_model`, `train_eval.py:GRIDS`

**Common mistake.** Comparing models without showing the baseline, or fitting the scaler on all data before CV.

**Check yourself.** What is the PR AUC of a model that guesses randomly?

## [N6] Logistic regression

**What it does.** Logistic regression models the **log-odds** of churn as a weighted sum of the
features: log(p / (1 − p)) = b₀ + b₁x₁ + … . The **odds ratio** e^b tells you how much the odds
multiply when a feature goes up by one unit. We **standardise** features first (mean 0, SD 1), so
"one unit" means one standard deviation, and coefficients can be compared. Standardising also matters
because the **L2 penalty** (`C` = inverse strength) shrinks all coefficients toward 0 equally, which
is only fair if they are on the same scale. CV chose **C = 0.1**, the strongest penalty in the grid,
which makes sense with only 64 rows and 19 features.

Biggest odds ratios (per +1 SD, from `report.md`):

| feature | odds ratio | reading |
|---|---|---|
| mean_gap_days | 1.72 | longer gaps between active nights → higher churn odds |
| days_since_last_report | 1.34 | quiet lately → higher odds |
| active_nights_28d | 0.75 | more active nights → lower odds |
| distinct_venues_28d | 0.76 | broader use → lower odds |
| median_distance_m | 0.71 | (see the warning below) |

Warning: with correlated features and only 64 rows, single coefficients are unstable. The
`median_distance_m` effect has no causal story in the simulator: distance does not drive quitting
there. It is probably standing in for "was verified often" or for activity. Read the *group* of
recency/frequency features, not any single sign.

**Code.** `train_eval.py:make_model("logistic")`, `explain.py:odds_ratio_table`

**Example.** Odds ratio 1.72: a Scout whose mean gap is 1 SD (about 4.5 days) longer has 1.72× the churn
odds, all else equal. With a base probability of 30% (odds 0.43), the new odds are 0.73, a probability of 42%.

**Common mistake.** Reading coefficients from an unscaled model as importance, or reading odds ratios as causes.

**Check yourself.** When would you pick logistic regression over gradient boosting even if its AUC were a bit lower?

## [N7] Trees, forests and boosting (bias–variance)

**What it does.**
- **Decision tree** (depth 2–4): asks yes/no questions ("mean_gap_days ≤ 4.8?"). It is easy to read,
  but it jumps a lot when the data changes slightly (**high variance**), and a shallow tree also misses
  smooth effects (**bias**). CV chose depth 3.
- **Random forest** (300 trees): many deep-ish trees, each grown on a bootstrap sample with random
  feature subsets, then averaged. Averaging cancels much of the variance. CV chose min_samples_leaf = 5.
- **Gradient boosting** (`HistGradientBoostingClassifier`): builds small trees one after another, each fixing the
  previous ones' errors. It is usually the strongest model on big tabular data, but it needs enough
  rows. With 64 Scouts it overfits easily.

The printed tree (in `report.md`) first splits on `mean_gap_days ≤ 4.8`, then on
`distinct_venues_28d` or `days_since_last_report`. The only clearly "stays" leaf is "short gaps,
more than one venue, and reported in the last 7 days", with weighted counts [24.9 stay, 0.0 churn].

**Code.** `train_eval.py:make_model`, `explain.py` (`export_text`)

**Common mistake.** Expecting the most complex model to win. On tiny data, simpler models often win.

**Check yourself.** Why does averaging many trees reduce variance but not bias?

## [N8] Metrics, threshold choice and validation

**What it does.**
- **Model selection:** for each family, every grid setting is scored by **repeated stratified 5-fold CV**
  (5 folds × 3 repeats = 15 ROC AUCs) on the **train snapshot only**. "Stratified" keeps the churn rate
  the same in every fold. The highest mean wins. The family chosen overall is also the one with the best
  mean CV AUC, so **the test set never chooses anything**.
- **ROC AUC:** the chance that a random churner gets a higher risk score than a random stayer. 0.5 = random.
- **PR AUC (average precision):** the area under precision vs recall. Its random baseline is the **base rate**,
  so it shows how well we find the minority class. That is more informative than ROC AUC when positives are rare.
- **Brier score:** the mean of (predicted probability − outcome)². Lower = better calibrated *and* sharper.
  `calibration_test.png` plots predicted risk against the actual churn share.
- **Threshold:** to turn risk into yes/no we pick the threshold that maximises F1 on the **out-of-fold**
  predictions from train, then apply it unchanged to test. It is not 0.5 by default and is never tuned on test.
- **Why not accuracy:** "everyone stays" already scores 64% on test. Accuracy rewards ignoring the class we care about.
- **Uncertainty:** test ROC/PR AUCs get bootstrap 95% CIs (resample the 86 Scouts 1,000 times).

**Results** (full table in `report.md`):

| model | CV ROC AUC (15 folds) | test ROC AUC [95% CI] | test PR AUC (base 0.36) | test Brier |
|---|---|---|---|---|
| majority | 0.500 | 0.500 | 0.360 | 0.360 |
| **logistic (C = 0.1, selected)** | **0.841 ± 0.134** | **0.826 [0.73, 0.91]** | **0.760** | **0.170** |
| tree (depth 3) | 0.740 | 0.719 [0.60, 0.82] | 0.496 | 0.228 |
| forest (leaf 5) | 0.804 | 0.787 [0.68, 0.88] | 0.651 | 0.180 |
| boosting (lr 0.1) | 0.738 | 0.755 [0.64, 0.86] | 0.602 | 0.201 |

Selected logistic regression at threshold 0.44 on test: precision 0.62, recall 0.77, F1 0.69
(24 churners caught, 7 missed, 15 false alarms). PRD targets: test ROC AUC ≥ 0.75 → **0.826, met**.
PR AUC lift ≥ 2× → **2.11×, met**. Best Brier ≤ logistic's → logistic *is* the best Brier.
The CIs overlap a lot (forest's interval contains logistic's estimate), so with under 100 Scouts we can
say "clearly better than the baseline", **not** "logistic beats the forest".

**Code.** `train_eval.py:cv_auc`, `choose_threshold`, `metrics_at`, `bootstrap_ci`, `evaluate_family`.
Test: `tests/test_churn_pipeline.py:test_metrics_match_sklearn`.

**Common mistake.** Choosing the threshold or the model on the test set. That makes the test score optimistic.

**Check yourself.** Why is PR AUC more informative than accuracy when about 30% of Scouts churn? Why is the CV ± so large?

## [N9] Interpretation and the action

**What it does.** Three views of what the model uses:
1. **Odds ratios** (N6): recency and frequency dominate.
2. **The printed tree** (N7): the same story as simple rules.
3. **Permutation importance** on the test snapshot: shuffle one feature, see how much test ROC AUC
   drops. Top: `days_since_last_report` (−0.040), then `mean_gap_days`, `distinct_venues_28d`,
   `reports_7d`, `active_nights_28d` (each about −0.015). See `permutation_importance.png`.

**Targeting view** (test snapshot): among the riskiest 10% of Scouts (9), **8 churned (89%)**,
2.5× the 36% base rate. Among the riskiest 25% (22), 16 churned (73%).

**The action:** each week, score active Scouts and send bounties or bonus points to the riskiest
~10–25%, prioritising venues where confidence would drop most. That keeps confidence up where it
matters. Whether a bounty actually *prevents* churn is a separate, causal question. It needs an
experiment (bounty vs no bounty for similar at-risk Scouts) and is not answered by this model (PRD stretch: uplift).

**Sanity check against the simulator's truth** (`evaluate_truth.py`, evaluation only): our label
agrees with the simulator's "quit for good" flag for 90% of test Scouts. Of the 9 disagreements, 8
reported once more inside the window and then quit (label 0, truth 1), and 1 was silent for 21 days without quitting.
The risk score's AUC against the truth flag is 0.840, close to the 0.826 against our label. AUC is below 0.95,
so the problem is not suspiciously easy.

**Code.** `explain.py:importance`, `explain.py:top_risk_table`, `evaluate_truth.py`

**Common mistake.** Saying "days since last report *causes* churn". It is a symptom we can see early, not a cause.

**Check yourself.** What would you need to show that bounties reduce churn?

## [N10] Limitations, and what changes with real data

- **Synthetic data.** The stand-in builds churn from a decaying-engagement process. The model mostly
  rediscovers "engagement decays, and quiet Scouts quit", which we put in ourselves. Real Scouts will churn
  for reasons we did not simulate (moving, a bad experience, a friend leaving).
- **Small sample.** 64 training Scouts and 19 churners. Wide CIs, unstable coefficients, and noisy CV (± 0.13).
  Stacking more snapshots (with grouped CV by `scout_id`) would help (PRD Q7).
- **Stand-in vs live-sim.** The launch week has 30 Scouts instead of about 12 so the Oct 1 snapshot has
  enough eligible Scouts. Equal 12-Scout cohorts left only about 50 eligible Scouts and about 8 churners. When live-sim's
  `data/live_sim.db` arrives, rerun everything: numbers will change.
- **Label choice.** "21 quiet days" mixes real quitting with long breaks (the truth check above).
- **With real data:** point `LIVE_SIM_DB` (or the loader) at the real tables, rerun, skip
  `evaluate_truth.py` (no truth table exists in real life), and keep monitoring the base rate.

**What I would say in a 2-minute presentation**
1. Scouts keep venue confidence scores alive, so I predicted which active Scouts go quiet for 21 days, using only data from before a cutoff date.
2. The split is by time: I train on the Oct 1 snapshot and test once on the later Oct 22 snapshot, and end-of-simulation columns are banned because they leak the future.
3. Logistic regression won CV and scored test ROC AUC 0.83 [0.73–0.91] and PR AUC 0.76 against a 0.36 base rate. The forest was close, and the CIs overlap.
4. Recency and gaps drive risk: the riskiest 10% of Scouts churned at 89%, so that is where bounties should go.
5. It is all synthetic and small, so the method is the result, not the numbers. Next steps are real data, more snapshots and a bounty experiment.

---

## Answers to the self-check questions (cover these up first)

- **Churn hurts with the same user count?** Confidence depends on *fresh* reports per venue. Losing active Scouts thins coverage even if sign-ups replace them later.
- **Thursday noon?** Nights run Thu–Sat, so a Thursday-noon cutoff never splits a night. A Scout who joined on Sep 29 is eligible at Oct 1 if they reported in those 2 days, and they have low tenure.
- **Two features with opposite signs?** More points might mean "engaged" (lower risk) or "already earned the reward" (higher risk). The data show a small negative coefficient (odds ratio 0.93).
- **Time vs random split?** Production predicts the future from the past. A time split tests exactly that and catches features that only work inside one period. A leaky feature: `syn_scouts.last_active_at`.
- **Random PR AUC?** About the base rate.
- **Logistic over boosting?** When you need to explain the model, need stable and calibrated probabilities, or have few rows, as here.
- **Averaging trees?** Errors from different trees partly cancel (variance falls), but if every tree is biased the same way, the average is biased too.
- **PR AUC vs accuracy?** "All stay" gets 64% accuracy and finds no churners. PR AUC measures how well we find the churners.
- **CV ± large?** Each fold has only about 13 Scouts and about 4 churners, so a single Scout moves the fold's AUC a lot.
- **Do bounties reduce churn?** A randomised experiment: give bounties to a random half of the at-risk Scouts and compare churn.
