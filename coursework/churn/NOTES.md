# Scout churn model: explanation notes

What this is: a model that predicts which **Scouts** (users who send 10-second vibe checks from
bars) will stop reporting. It compares a majority-class baseline, logistic regression and three
tree models, using a split by time so the model cannot see the future.

**All Scout data here is SYNTHETIC.** The results below come from live-sim's simulator
(`data/live_sim.db`, seed 42, 209 Scouts, built from `origin/nightlife/live-sim` @ 0d2a26c with
`python -m simulator --seed 42 --out data/live_sim.db`). The DB is not committed. Before the simulator
existed, a marked stand-in generator (`make_standin_data.py`) was used, and its results are kept in the
**Appendix**. The scripts pick `data/live_sim.db` when it exists and fall back to the stand-in otherwise
(see `docs/synthetic/coursework.md`). Nothing here is evidence about real people.

How to run (from the repo root):

```bash
python -m simulator --seed 42 --out data/live_sim.db       # from a live-sim checkout (no -I); or:
python -I coursework/churn/make_standin_data.py --seed 0   # fallback only, if data/live_sim.db is missing
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

**Example.** If the riskiest 10% of Scouts churn at 90% and the average Scout at 41%, a limited
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
| train | reports before **Oct 1** | Oct 1 – Oct 21 | 86 | 27 | 31.4% |
| test | reports before **Oct 22** | Oct 22 – Nov 11 | 101 | 41 | 40.6% |

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

Two small conversions for live-sim's data: `level` is stored as a name, so it is mapped to an
ordinal (Rookie 1 < Regular 2 < Insider 3 < Legend 4, matching its points bands), and Scouts who
signed up before the first night (47 Scouts, Aug 24–26) count as cohort week 0.

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
Its ROC AUC is 0.5 by definition, and its PR AUC equals the base rate (0.31 in train, 0.41 in test). Every
real model has to beat it. Its "accuracy" would be 59% on test without learning anything, which is
why accuracy is not used (N8).

About 31–41% of Scouts churn, so the classes are **imbalanced**. Logistic regression, the tree and
the forest use `class_weight="balanced"`, which weights the minority class more in the loss so the
model does not just predict "stays". Gradient boosting was left at its defaults, with no class weights
(the plan's grid only varies the learning rate), so its probabilities are not re-weighted. Its threshold
is still chosen on out-of-fold predictions (0.51). We do not oversample (no SMOTE). With so few rows, made-up rows
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
which makes sense with only 86 rows and 19 features.

Biggest odds ratios (per +1 SD, from `report.md`):

| feature | odds ratio | reading |
|---|---|---|
| reports_7d | 0.65 | more reports in the last week → lower churn odds |
| trend | 0.71 | speeding up → lower odds; slowing down → higher |
| points_28d | 0.76 | recent rewards go with staying |
| bounties_claimed_28d | 0.78 | claimed bounties go with staying |
| cohort_week | 0.78 | later joiners churn a bit less (they have had less time to fade) |
| days_since_last_report | 1.27 | quiet lately → higher odds |

Warning: many of these features are strongly correlated (reports, points, bounties all measure
activity). With 86 rows, a single coefficient can swap sign or size between runs. Read the *group*
("recent activity and rewards protect, silence and slowing down predict churn"), not any single
number, and not as a cause.

**Code.** `train_eval.py:make_model("logistic")`, `explain.py:odds_ratio_table`

**Example.** Odds ratio 0.65 for `reports_7d`: a Scout with 1 SD (about 6) more reports in the last week
has 0.65× the churn odds, all else equal. With a base probability of 31% (odds 0.45), the new odds are
0.29, a probability of 23%.

**Common mistake.** Reading coefficients from an unscaled model as importance, or reading odds ratios as causes.

**Check yourself.** When would you pick logistic regression over gradient boosting even if its AUC were a bit lower?

## [N7] Trees, forests and boosting (bias–variance)

**What it does.**
- **Decision tree** (depth 2–4): asks yes/no questions ("reports_7d ≤ 6.5?"). It is easy to read,
  but it jumps a lot when the data changes slightly (**high variance**), and a shallow tree also misses
  smooth effects (**bias**). CV chose depth 4.
- **Random forest** (300 trees): many deep-ish trees, each grown on a bootstrap sample with random
  feature subsets, then averaged. Averaging cancels much of the variance. CV chose min_samples_leaf = 20.
- **Gradient boosting** (`HistGradientBoostingClassifier`): builds small trees one after another, each fixing the
  previous ones' errors. It is usually the strongest model on big tabular data, but it needs enough
  rows. With 86 Scouts it can overfit easily.

The printed tree (in `report.md`) first splits on `reports_7d ≤ 6.5`. The clearest leaves are
"more than 6 reports last week and mostly not Saturday-only", with weighted counts [29.9 stay, 0.0 churn],
and "6 or fewer reports last week, at most 35 in 28 days, mostly not Saturday-only, at most 615 recent
points", with [1.5 stay, 31.9 churn].

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
- **Why not accuracy:** "everyone stays" already scores 59% on test. Accuracy rewards ignoring the class we care about.
- **Uncertainty:** test ROC/PR AUCs get bootstrap 95% CIs (resample the 101 Scouts 1,000 times).

**Results** (full table in `report.md`):

| model | CV ROC AUC (15 folds) | test ROC AUC [95% CI] | test PR AUC (base 0.41) | test Brier |
|---|---|---|---|---|
| majority | 0.500 | 0.500 | 0.406 | 0.406 |
| **logistic (C = 0.1, selected)** | **0.887 ± 0.045** | **0.852 [0.77, 0.92]** | **0.780** | **0.148** |
| tree (depth 4) | 0.811 | 0.788 [0.71, 0.87] | 0.646 | 0.204 |
| forest (leaf 20) | 0.883 | 0.864 [0.79, 0.93] | 0.846 | 0.165 |
| boosting (lr 0.1) | 0.859 | 0.840 [0.76, 0.91] | 0.787 | 0.167 |

Selected logistic regression at threshold 0.39 on test: precision 0.70, recall 0.78, F1 0.74
(32 churners caught, 9 missed, 14 false alarms). PRD targets: test ROC AUC ≥ 0.75 → **0.852, met**.
PR AUC lift ≥ 2× → **1.92×, missed**. At a 40.6% base rate the highest lift *any* model can reach is
1 / 0.406 = 2.46×, so a 2× target is hard when churn is this common. The forest reaches 2.08×, but we
do not switch models after seeing the test set. Best Brier ≤ logistic's → logistic *is* the best Brier.
The forest scored slightly higher on test ROC AUC (0.864) than the selected logistic (0.852), and the
CIs overlap almost completely. That is exactly why the test set does not choose: with about 100 Scouts we can
say "clearly better than the baseline", **not** "logistic beats the forest" or the reverse.

**Code.** `train_eval.py:cv_auc`, `choose_threshold`, `metrics_at`, `bootstrap_ci`, `evaluate_family`.
Test: `tests/test_churn_pipeline.py:test_metrics_match_sklearn`.

**Common mistake.** Choosing the threshold or the model on the test set. That makes the test score optimistic.

**Check yourself.** Why is PR AUC more informative than accuracy when about 30–40% of Scouts churn? Why is there a CV ± at all?

## [N9] Interpretation and the action

**What it does.** Three views of what the model uses:
1. **Odds ratios** (N6): recent activity, trend and rewards dominate.
2. **The printed tree** (N7): the same story as simple rules, led by `reports_7d`.
3. **Permutation importance** on the test snapshot: shuffle one feature, see how much test ROC AUC
   drops. Top: `reports_7d` (−0.017), `cohort_week` (−0.015), `trend` (−0.009), then the points
   features (about −0.008). The drops are small and noisy (SDs about the same size), because correlated
   features cover for each other: shuffle one and the others still carry the signal. See `permutation_importance.png`.

**Targeting view** (test snapshot): among the riskiest 10% of Scouts (10), **9 churned (90%)**,
2.2× the 41% base rate. Among the riskiest 25% (25), 21 churned (84%).

**The action:** each week, score active Scouts and send bounties or bonus points to the riskiest
~10–25%, prioritising venues where confidence would drop most. That keeps confidence up where it
matters. Whether a bounty actually *prevents* churn is a separate, causal question. It needs an
experiment (bounty vs no bounty for similar at-risk Scouts) and is not answered by this model (PRD stretch: uplift).

**Sanity check against the simulator's truth** (`evaluate_truth.py`, evaluation only): our label
agrees with the simulator's "quit for good" flag for 82% of test Scouts. Of the 18 disagreements, 12
reported once more inside the window and then quit (label 0, truth 1), and 6 were silent for 21 days
without quitting (label 1, truth 0). The risk score's AUC is 0.852 against our label but only **0.710**
against the truth flag. The model predicts "21 quiet days" well, but that label is only a rough proxy for
"gone for good". AUC is below 0.95, so the problem is not suspiciously easy.

**Code.** `explain.py:importance`, `explain.py:top_risk_table`, `evaluate_truth.py`

**Common mistake.** Saying "days since last report *causes* churn". It is a symptom we can see early, not a cause.

**Check yourself.** What would you need to show that bounties reduce churn?

## [N10] Limitations, and what changes with real data

- **Synthetic data.** live-sim's Scouts follow an engagement process with drop-off that the team designed.
  The model mostly rediscovers "activity fades before Scouts quit". Real Scouts will churn for reasons
  nobody simulated (moving, a bad experience, a friend leaving).
- **Small sample.** 86 training Scouts and 27 churners. Wide CIs, correlated features, and unstable
  single coefficients. Stacking more snapshots (with grouped CV by `scout_id`) would help (PRD Q7).
- **Label vs truth.** "21 quiet days" agrees with the simulator's true quit date for only 82% of Scouts.
  A longer horizon or survival analysis (time to churn) would follow real quitting more closely.
- **One seed.** Results are for live-sim seed 42 only. A different seed would move the numbers by about the CI widths.
- **With real data:** point `LIVE_SIM_DB` (or the loader) at the real tables, rerun, skip
  `evaluate_truth.py` (no truth table exists in real life), and keep monitoring the base rate.

**What I would say in a 2-minute presentation**
1. Scouts keep venue confidence scores alive, so I predicted which active Scouts go quiet for 21 days, using only data from before a cutoff date.
2. The split is by time: I train on the Oct 1 snapshot (86 Scouts) and test once on the later Oct 22 snapshot (101), and end-of-simulation columns are banned because they leak the future.
3. Logistic regression won CV and scored test ROC AUC 0.85 [0.77–0.92] and PR AUC 0.78 against a 0.41 base rate. The forest and boosting were close, and the CIs overlap.
4. Recent activity and trend drive risk: the riskiest 10% of Scouts churned at 90%, so that is where bounties should go.
5. It is synthetic and small, and the label only matches true quitting 82% of the time, so the method is the result, not the numbers.

---

## Answers to the self-check questions (cover these up first)

- **Churn hurts with the same user count?** Confidence depends on *fresh* reports per venue. Losing active Scouts thins coverage even if sign-ups replace them later.
- **Thursday noon?** Nights run Thu–Sat, so a Thursday-noon cutoff never splits a night. A Scout who joined on Sep 29 is eligible at Oct 1 if they reported in those 2 days, and they have low tenure.
- **Two features with opposite signs?** More points might mean "engaged" (lower risk) or "already earned the reward" (higher risk). The data show negative coefficients (points_28d odds ratio 0.76): rewarded Scouts stay.
- **Time vs random split?** Production predicts the future from the past. A time split tests exactly that and catches features that only work inside one period. A leaky feature: `syn_scouts.last_active_at`.
- **Random PR AUC?** About the base rate.
- **Logistic over boosting?** When you need to explain the model, need stable and calibrated probabilities, or have few rows, as here.
- **Averaging trees?** Errors from different trees partly cancel (variance falls), but if every tree is biased the same way, the average is biased too.
- **PR AUC vs accuracy?** "All stay" gets 59% accuracy and finds no churners. PR AUC measures how well we find the churners.
- **CV ±?** Each fold has only about 17 Scouts and about 5 churners, so a single Scout moves that fold's AUC noticeably.
- **Do bounties reduce churn?** A randomised experiment: give bounties to a random half of the at-risk Scouts and compare churn.

---

## Appendix: stand-in results (before live-sim shipped)

Before `simulator/` existed, the same pipeline ran on `make_standin_data.py --seed 0` (150 Scouts,
decaying Poisson engagement, 30-Scout launch week). Full report: `outputs/standin/report.md`,
metrics `outputs/standin/metrics.json`, and plots in `outputs/standin/`.

| | stand-in | live-sim (seed 42) |
|---|---|---|
| train / test Scouts | 64 / 86 | 86 / 101 |
| base rate train / test | 29.7% / 36.0% | 31.4% / 40.6% |
| selected model (CV) | logistic, C = 0.1 | logistic, C = 0.1 |
| selected test ROC AUC [95% CI] | 0.826 [0.73, 0.91] | 0.852 [0.77, 0.92] |
| selected test PR AUC (lift) | 0.760 (2.11×) | 0.780 (1.92×) |
| forest / boosting / tree test ROC AUC | 0.787 / 0.755 / 0.719 | 0.864 / 0.840 / 0.788 |
| top-10% risk churn rate | 89% | 90% |
| label agrees with truth | 90% | 82% |
| strongest signals | mean_gap_days, days_since_last_report | reports_7d, trend, points/bounties |

Same method, same winner. The stand-in's strongest signals were gaps and recency, because that is how
it was built (smooth decay). live-sim's Scouts respond to rewards, so points and bounties show up.

