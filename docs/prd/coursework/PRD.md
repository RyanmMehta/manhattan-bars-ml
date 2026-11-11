# PRD — coursework workstream

Owner: Ryan Mehta (individual assignments). Folder: `coursework/`. Branch: `nightlife/coursework`.
Status: planning only. No code yet.

## 1. Problem

Two of Ryan's individual course exercises are still open:

| Exercise | Original due date | Status |
|---|---|---|
| (a) Tiny transformer: a character-level language model trained from scratch | Sept 22 | not started |
| (b) Churn model: predict which customers stop being active | Oct 27 | not started |

Both are late, so they need to be small, finished, and easy to explain. Each one
should also tie into Nightlife Autopilot so the work feeds the class project:

- (a) trains on **venue names** from `data/manhattan_bars.db` (real public data: SLA
  license names). The model writes new names that sound like Manhattan bars. This
  can later produce placeholder names for synthetic venues, or test the search box.
- (b) predicts **which Scouts stop reporting**, using `syn_scouts` and
  `syn_scout_reports` from live-sim. Scout retention matters because the
  `confidence` score depends on fresh reports. Losing Scouts lowers confidence.

These are individual assignments, so Ryan has to understand every line. Each
exercise comes with written explanation notes, and the code stays simple and
commented. Clever code is out of scope.

## 2. Goals

1. G1: one runnable, documented tiny transformer that trains on CPU in under ~10 minutes
   (placeholder target) and beats a bigram baseline on held-out validation loss.
2. G2: one runnable churn analysis that compares logistic regression to tree models
   (decision tree, random forest, gradient boosting) with a leakage-free time-based
   split and reports ROC AUC, PR AUC, precision/recall at a chosen threshold, and calibration.
3. G3: an explanation notebook-style markdown file per exercise (`NOTES.md`) that walks
   through every step in plain words, so Ryan can present and defend it.
4. G4: everything reproducible from one command per exercise, with fixed seeds.
5. G5: all synthetic inputs marked and swappable per the CONTRACTS.md synthetic-data rule.

## 3. Non-goals

- No contribution to the deployed app (backend/frontend do not import `coursework/`).
- No GPU, no large models, no pretrained weights, no Hugging Face. The model is written from scratch.
- No hyperparameter sweeps beyond a small, listed grid.
- No claim that the churn model reflects real Scout behaviour. The data is synthetic until real Scouts exist.
- Not changing `src/`, `recs/`, `simulator/` or any other workstream's folder.

## 4. Users

| User | Need |
|---|---|
| Ryan (student, author) | finish both assignments, understand and explain each step, submit on time |
| Course grader / instructor | clear method, correct validation, honest metrics, readable code |
| Project team (later) | optional: churn insights (what predicts Scout drop-off) feed bounty/points design; generated names as demo placeholders |

## 5. User stories and acceptance criteria

**US1: train the tiny transformer.** As Ryan, I run one command and get a trained model.
- AC1.1 `python -I coursework/tiny_transformer/train.py` runs on CPU with default settings and finishes in ≤ 10 min (placeholder; measure).
- AC1.2 Prints train/val loss every N steps and writes `coursework/tiny_transformer/outputs/metrics.json` and a loss-curve PNG.
- AC1.3 Final val loss (nats/char) is lower than both the unigram and the bigram baseline computed on the same split.
- AC1.4 Same seed gives the same final val loss to within 1e-3 on the same machine.

**US2: sample from the model.** As Ryan, I can generate new venue names.
- AC2.1 `sample.py --n 20 --temperature 0.8` prints 20 names.
- AC2.2 Reports the novelty rate (share of samples that don't appear exactly in the training names). Target ≥ 70% (placeholder).
- AC2.3 Outputs are labelled as generated/synthetic. Any CSV of samples has `is_synthetic=1` and lives under a `synthetic` path.

**US3: understand the transformer.** As Ryan, I can explain every component.
- AC3.1 `tiny_transformer/NOTES.md` covers tokenisation, embeddings, positional encoding, self-attention (with the causal mask), multi-head, MLP, residual + layer norm, the loss, the optimizer, train/val split, and sampling/temperature. Each section has a one-paragraph explanation and points to the code lines.
- AC3.2 It includes a hand-worked tiny attention example (3 tokens, d=2) that a unit test checks.

**US4: build the churn dataset.** As Ryan, I turn raw Scout reports into one row per Scout with features and a label.
- AC4.1 `churn/build_dataset.py` reads `syn_scouts` + `syn_scout_reports` (SQLite or CSV) and writes `coursework/churn/outputs/synthetic/churn_dataset.csv` with `is_synthetic=1`.
- AC4.2 Features use only reports **before** the cutoff date. The label uses only the window **after** it. A unit test checks there is no leakage.
- AC4.3 Churn label definition is written down: a Scout active before the cutoff (≥ 1 report in the 28 days before) who makes **0 reports in the 21 days after** (placeholder windows) is churned (1).

**US5: compare models.** As Ryan, I compare logistic regression against trees fairly.
- AC5.1 `churn/train_eval.py` trains: majority baseline, logistic regression (scaled, L2), decision tree (depth ≤ 4, for interpretability), random forest, gradient boosting.
- AC5.2 Validation: stratified 5-fold CV on the training cutoff for model selection, plus a final test on a **later** cutoff (out-of-time) that the models never saw.
- AC5.3 Reports ROC AUC, PR AUC (with base rate), Brier score, and precision/recall/F1 at a threshold chosen on validation (not 0.5 by default). Writes a markdown table to `outputs/report.md`.
- AC5.4 Shows interpretable output: logistic coefficients (odds ratios), the depth-≤4 tree drawn as text, and permutation importance for the best model.

**US6: understand the churn work.** As Ryan, I can defend the method.
- AC6.1 `churn/NOTES.md` explains the churn definition, why a time-based split, why PR AUC with a low base rate, why not accuracy, class imbalance handling, calibration, and what the business action would be (e.g. bounties for at-risk Scouts).
- AC6.2 States plainly that results come from synthetic data and what would change with real data.

## 6. Scope

**MVP (by Nov 17, placeholder; the course may accept earlier)**
- Tiny transformer: data prep, model, train, sample, baselines, notes, tests.
- Churn: dataset builder, 5 models, CV + out-of-time test, report, notes, tests.
- Synthetic registry `docs/synthetic/coursework.md` and workstream doc `docs/workstreams/coursework.md`.

**Later / stretch**
- Tiny transformer: a numpy-only forward pass that checks the PyTorch one (educational). Training on nightlife review text if a licensed corpus appears. A word-level tokenizer comparison.
- Churn: survival analysis (time to churn, Kaplan–Meier / Cox) and uplift framing (does a bounty reduce churn?). Export a `scout_churn_risk` score the backend could show on an internal dashboard (needs a contract change).

## 7. Requirements

**Functional**
- F1 Corpus = distinct venue names from `venues.name` in `data/manhattan_bars.db` (5,351 distinct upper-cased names; mean length ~16 chars). Normalise: strip legal suffixes (`LLC`, `INC`, `CORP`, `#1234`), collapse spaces, title or upper case (decision: upper case, keeps the vocab small). Read-only access to the DB.
- F2 Split names 90/10 train/val **by name** (not by character), seeded.
- F3 Model: decoder-only transformer, defaults `n_layer=2, n_head=4, d_model=64, block_size=32, dropout=0.1` (~100k params, placeholder). Special tokens `<s>` (start) and `<e>` (end/pad).
- F4 Churn features per Scout (all computed before the cutoff): tenure_days, reports_28d, reports_7d, days_since_last_report, active_nights_28d, mean_gap_days, trend (reports_7d vs the prior 21d rate), share_verified_presence, distinct_venues_28d, share_weekend_reports, reputation, points, level. Plus optional `bounties_claimed_28d` if `syn_bounties` exists.
- F5 Configurable windows (`--cutoff`, `--lookback-days 28`, `--horizon-days 21`).
- F6 Each script has `--help` and sensible defaults. No hidden state.

**Non-functional**
- N1 CPU only. Total runtime for both exercises ≤ 15 min (placeholder).
- N2 Every file starts with a docstring saying what it does and how to run it. Every non-obvious line has a comment.
- N3 Deterministic with `--seed` (default 0).
- N4 Python 3.13, the repo's existing `requirements.txt` stack plus `torch` (CPU) and `matplotlib`.

## 8. Dependencies on other workstreams

| Workstream | Dependency | Needed by | Fallback |
|---|---|---|---|
| live-sim | `syn_scouts`, `syn_scout_reports` (and optionally `syn_bounties`) covering **≥ 10 weeks** of nights with realistic Scout drop-off | churn build | coursework writes a small stand-in generator `churn/make_standin_data.py` (marked SYNTHETIC) with the same schema. It is swapped out as soon as live-sim lands. |
| specs | definition of an "active Scout" if specs defines one; report freshness half-life (only for context) | churn notes | use the definition in AC4.3 |
| research | interview findings on why Scouts would stop (motivation) to guide feature ideas | churn notes (nice-to-have) | list hypotheses as assumptions |
| ml-recs | none required; churn findings may inform reputation weighting | — | — |
| backend | none for MVP (stretch: internal churn-risk endpoint) | — | — |
| frontend | none | — | — |
| tableau | optional: a CSV of churn predictions/feature importances for a dashboard tile | after MVP | — |
| integration | coursework is **not** part of the deployed app; integration should merge the branch without wiring it in | Nov 17 | — |
| existing (`src/`, DB) | read-only `venues.name` | transformer | — |

## 9. Success metrics

| Metric | Target (placeholder) |
|---|---|
| Transformer val loss vs bigram baseline | ≥ 10% lower nats/char |
| Transformer val perplexity per char | report it; expect ~5–8 |
| Novelty rate of samples (T=0.8) | ≥ 70% not in training set, ≥ 90% "plausible" by a quick manual read of 50 |
| Churn: best model ROC AUC on out-of-time test | ≥ 0.75 on synthetic data. Beats majority baseline (0.5) and is reported next to logistic regression |
| Churn: PR AUC | report next to base rate. Lift ≥ 2× base rate |
| Calibration (Brier) | best model ≤ logistic regression's Brier, or explain why not |
| Ryan can explain each step | self-check list in each NOTES.md all answered |
| Submission | both exercises submitted by the course's late deadline (ask instructor) |

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| live-sim data late, or has no churn signal (e.g. every Scout reports forever) | churn exercise blocked or meaningless | stand-in generator with a known drop-off hazard. Contract change request (below) asks live-sim to model drop-off |
| Synthetic churn is "too easy" (label leaks from how the simulator works, AUC ~0.99) | misleading results | check feature/label overlap. Compare against the stand-in's known hazard. State it in the notes |
| Time-window leakage (features computed with post-cutoff reports) | inflated metrics | unit test that drops all post-cutoff rows and checks features are unchanged |
| Venue names include personal names / LLC noise | odd samples | normalisation rules in F1. Names are public license data anyway |
| Model memorises names (small corpus) | low novelty | dropout, early stopping on val loss, report novelty |
| `torch` install heavy / unavailable in some env | can't train | CPU wheel. Stretch numpy forward pass. Keep model tiny |
| Ryan doesn't understand code written for him | academic-integrity / learning risk | NOTES.md per step, self-check questions, simple code, no hidden helpers. Ryan should retype or annotate key parts himself and check the course's AI-use policy |
| Assignment spec differs from these assumptions | rework | Open question Q1. Keep the scripts modular so the rubric can be mapped |

## 11. Assumptions

- A1 The course accepts PyTorch for (a). (The brief allows PyTorch or numpy. PyTorch was picked because autograd keeps the code short.)
- A2 The course accepts the churn exercise on a project-relevant synthetic dataset instead of a given dataset (e.g. Telco churn). If a given dataset is required, the same `train_eval.py` runs on it with a column map.
- A3 Venue names are fine as a corpus (public data, no reviews needed).
- A4 live-sim will produce `syn_scout_reports` in `data/synthetic_live/` CSVs and/or `syn_` tables in `data/manhattan_bars.db`. The builder accepts either.
- A5 Time zone America/New_York. "Night" = 6pm–4am, assigned to the start date.

## 12. Open questions

- Q1 What exactly do the Sept 22 and Oct 27 assignment sheets require (rubric, required dataset, required deliverable format, e.g. notebook vs scripts, write-up length)? **Top blocker for grading fit.**
- Q2 Is AI help allowed, and how must it be disclosed? Affects how much code the build session writes vs Ryan writes.
- Q3 Will live-sim simulate ≥ 10 weeks with Scout drop-off, or only a few demo nights?
- Q4 Late-submission deadline for each exercise?
- Q5 Should churn include `syn_bounties` as a feature (bounties claimed) or treat bounties as an intervention (stretch, uplift)?
- Q6 Notebook (`.ipynb`) or `.py` + `NOTES.md` for submission? Default: `.py` + `NOTES.md`, with an optional notebook export.

## 13. Contract change requests

(Also to be copied into `docs/workstreams/coursework.md` at build time, per CONTRACTS.md.)

- CR1 (live-sim): simulate Scouts over **≥ 10 weeks** (placeholder) with a realistic drop-off process. Each Scout has a latent engagement level that decays, and activity rises after rewards/bounties, so a churn label exists.
- CR2 (live-sim, optional): publish a ground-truth table `syn_scout_truth(scout_id, latent_churn_date, is_synthetic)` used **only** to sanity-check the churn model, never as a feature.
- CR3 (contracts): add `syn_scouts.last_active_at` (nullable) or confirm it is derived from reports. Coursework will derive it if not added.
- No changes requested to the HTTP API or `recs/` interface.
