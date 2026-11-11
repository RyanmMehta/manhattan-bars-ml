# OUTLINE — coursework build plan

Read `PRD.md` and `RULES.md` first. Updated for CONTRACTS v2.1 (commit 0a5ba55). Push deadline **Fri Nov 13 18:00 ET**. Sizes: S ≤ 1 h, M 1–3 h, L 3–6 h (placeholders).
Total ≈ 2 working days for the build session. Ryan also needs time to read the NOTES.

## 1. File tree to create

```
coursework/
  README.md                      # what's here, how to run, links to NOTES
  requirements.txt               # torch (cpu), matplotlib, pytest (extra deps only)
  run_coursework.sh              # runs both exercises end to end
  common.py                      # ROOT path, seed helper, read-only DB connect (tiny)
  tiny_transformer/
    NOTES.md                     # [N1]..[N12] step-by-step explanation
    data.py                      # load + clean venue names, split, tokenizer
    baselines.py                 # unigram + bigram char models (val loss)
    model.py                     # Head, MultiHeadAttention, FeedForward, Block, TinyGPT
    train.py                     # training loop, eval, early stopping, metrics.json, loss curve
    sample.py                    # generation with temperature / top-k, novelty rate
    attention_by_hand.py         # numpy 3-token worked example (used in NOTES + test)
    outputs/                     # metrics.json, loss_curve.png, synthetic/generated_names.csv
  churn/
    NOTES.md                     # [N1]..[N10]
    load.py                      # read syn_* tables from data/live_sim.db (read-only) or CSV
    make_standin_data.py         # SYNTHETIC fallback with same schema (build ONLY if live-sim slips)
    evaluate_truth.py            # eval-only: compare predictions with syn_scout_truth (churned_at, archetype, cohort_week)
    build_dataset.py             # cutoff windows -> features + label, one row per scout
    train_eval.py                # 5 models, CV, out-of-time test, threshold, report.md
    explain.py                   # odds ratios, text tree, permutation importance, plots
    outputs/                     # report.md, metrics.json, *.png, synthetic/churn_dataset_*.csv
  tests/
    fixtures/synthetic/          # tiny hand-made scouts/reports CSVs (is_synthetic=1)
    test_tokenizer.py
    test_model.py
    test_attention_by_hand.py
    test_churn_features.py
    test_churn_pipeline.py
    test_notes_tags.py           # every [N#] tag in code has a NOTES section and vice versa
docs/workstreams/coursework.md
docs/synthetic/coursework.md
```
`.gitignore` additions go in `coursework/.gitignore`: `outputs/**/*.pt`, `outputs/**/synthetic/*.csv` except small samples.

## 2. Ordered tasks

### Setup
- [ ] **T0 (S)** Branch check, `coursework/README.md`, `requirements.txt`, `common.py`, `.gitignore`, empty `run_coursework.sh`.
  Install torch CPU, record the versions in the README.

### (a) Tiny transformer
- [ ] **T1 (S)** `data.py`: `load_names()` reads `SELECT DISTINCT name FROM venues` (read-only). `clean_name()` upper-cases,
  strips `LLC|INC|CORP|CO\.|LTD|#\d+|D/B/A.*`, removes characters outside `[A-Z0-9 &'\-.]`, collapses spaces, drops names
  < 3 or > 30 chars. Dedupe. Log count (expect ~5,000; placeholder).
- [ ] **T2 (S)** `data.py`: `split_names(names, val_frac=0.1, seed)`. Char vocab + `<s>`/`<e>` → `stoi/itos`, `encode/decode`.
  Training examples: `<s>` + name + `<e>`, padded with `<e>` to `block_size`. The loss ignores padding after the first `<e>`.
  Tests: round-trip, vocab size (~45, placeholder).
- [ ] **T3 (S)** `baselines.py`: unigram and bigram (add-1 smoothing) val loss in nats/char. This is the bar to beat. [N3]
- [ ] **T4 (M)** `attention_by_hand.py` + test: 3 tokens, d=2. Compute Q,K,V, scores, causal mask, softmax, output by hand in numpy.
  Assert it equals `model.Head` with the same weights. [N6]
- [ ] **T5 (M)** `model.py`: token emb + learned position emb → `n_layer` × Block(LN → MHA (causal) → residual,
  LN → MLP 4× GELU → residual) → LN → linear head. Defaults n_layer=2, n_head=4, n_embd=64, block_size=32, dropout=0.1.
  Print the param count. Tests: shapes, causal-mask property, overfit-8-names. [N4–N9]
- [ ] **T6 (M)** `train.py`: AdamW lr 3e-3 → cosine to 3e-4, batch 64, max 3,000 steps (placeholder), eval every 100 steps on
  val (20 batches). Early stop after 5 evals with no improvement. Save best `.pt`, `metrics.json`
  (train/val loss, perplexity, baselines, params, runtime, seed) and `loss_curve.png`. [N10]
- [ ] **T7 (S)** `sample.py`: autoregressive sampling from `<s>`, temperature, optional top-k, stop at `<e>`.
  Novelty rate vs the train set. Writes `outputs/synthetic/generated_names.csv` (`name, temperature, is_novel, is_synthetic=1`). [N11]
- [ ] **T8 (S)** Small ablation table (3 runs): n_layer 1 vs 2, block_size 16 vs 32, dropout 0 vs 0.1. Val loss only, in `metrics.json`.
- [ ] **T9 (M)** `tiny_transformer/NOTES.md` [N1]–[N12]:
  N1 task and corpus, N2 cleaning and split, N3 baselines and nats/char, N4 tokens and embeddings, N5 positional embeddings,
  N6 self-attention by hand, N7 causal mask, N8 multi-head + MLP, N9 residual + layer norm, N10 loss, AdamW, LR schedule,
  early stopping, N11 sampling and temperature, N12 results, limitations, 2-minute talk.

### (b) Churn
- [ ] **T10 (S)** `load.py`: read `syn_scouts`, `syn_scout_reports`, `syn_points_ledger`, `syn_bounties` from **`data/live_sim.db`**
  (`?mode=ro`, path overridable by env `LIVE_SIM_DB`) **or** `data/synthetic_live/*.csv`. Validate columns against CONTRACTS v2 §E
  (incl. `status`, `distance_m`, `last_active_at`, `claimed_at`). Parse `ts` as America/New_York. Drop reports with `status = 'removed'`.
  Never load `syn_scout_truth` here.
  `# SYNTHETIC: replace with backend scouts/scout_reports tables`.
- [ ] **T11 (M, CONDITIONAL)** `make_standin_data.py`: build only if `data/live_sim.db` is not available by Thu Nov 12 12:00 ET. Same dates as v2
  (Thu–Sat, Aug 27 → Nov 14 2026, 20:00–03:00 ET), IDs `syn-s-####` / `syn-r-######`, ~150 Scouts in 12 weekly cohorts (as in v2.1).
  Each Scout gets a latent engagement λ₀ ~ Gamma(2, 1) reports/week that decays by `exp(-t/τ)`, τ ~ LogNormal. Saturday
  ×1.5 vs Thu/Fri, and a bounty claim bumps λ by +30% for 2 weeks. Report fields (incl. `status`, `distance_m`) drawn per the v2.1 schema
  across the 35 launch venues. Writes `standin_scouts.csv`, `standin_scout_reports.csv`, `standin_points_ledger.csv`,
  `standin_bounties.csv`, `standin_scout_reputation_history.csv`, `standin_scout_truth.csv` under
  `coursework/churn/outputs/synthetic/` with `is_synthetic=1`, seed 0.
- [ ] **T12 (M)** `build_dataset.py`: `build(reports, scouts, ledger, bounties, rep_history, cutoff, lookback=28, horizon=21)`. Eligible = ≥ 1 report in
  [cutoff−28d, cutoff) and `joined_at < cutoff`. Features per PRD F4 from rows with `ts < cutoff` only. Points/reputation/level come from the latest
  `syn_scout_reputation_history` row with `as_of_date < cutoff` (cross-checked with the `syn_points_ledger` sum), **not** `syn_scouts`. Label = 0 reports in [cutoff, cutoff+21d).
  Two snapshots (Thursdays 12:00 ET): **train cutoff 2026-10-01** (label window Oct 1–21) and **test cutoff 2026-10-22** (out-of-time,
  label window Oct 22–Nov 11). Print the eligible count and churn base rate per snapshot. Warn if < 60 eligible Scouts, < 15 churners, or a base rate outside 5–60%
  (expected with ~150 Scouts: ~60–110 eligible per snapshot; placeholder).
  Tests: leakage (drop post-cutoff rows → same features), 3-Scout fixture labels, eligibility, end-of-sim snapshot columns absent from the feature list. [N2–N4]
- [ ] **T13 (M)** `train_eval.py`: models = DummyClassifier(most_frequent), LogisticRegression (StandardScaler, C grid {0.1,1,10},
  class_weight balanced), DecisionTree (max_depth {2,3,4}), RandomForest (300 trees, min_samples_leaf {5,20}),
  HistGradientBoosting (default + lr {0.05,0.1}). Model selection by **repeated** stratified 5-fold CV (3 repeats) ROC AUC on the train snapshot
  (small sample: ~60–110 Scouts). Test metrics get bootstrap 95% CIs (1,000 resamples).
  Threshold = max F1 on out-of-fold predictions. Refit on the full train snapshot and score once on the test snapshot.
  Metrics: ROC AUC, PR AUC, base rate, Brier, P/R/F1 at the threshold, confusion matrix. Writes `report.md` + `metrics.json`. [N5–N8]
- [ ] **T14 (S)** `explain.py`: LR odds ratios table, `export_text` of the depth-≤4 tree, permutation importance (test snapshot)
  for the best model, calibration curve PNG and ROC/PR PNGs, all titled "(synthetic data)". [N9]
- [ ] **T15 (S)** `evaluate_truth.py` (eval-only, the **only** file that reads `syn_scout_truth`): for the test snapshot, compare predicted risk
  with `churned_at` (does a high-risk Scout's true churn date fall inside [cutoff, cutoff+21d)? Does our report-based label agree with
  `churned_at`?). Break down AUC by `archetype` (honest/casual/sloppy/gamer/shill) and `cohort_week`. Check whether risk correlates with
  `true_accuracy` (it shouldn't need to). Flag AUC > 0.95 as "suspiciously easy, check for leakage". Results go to a separate section of `report.md`.
- [ ] **T16 (M)** `churn/NOTES.md` [N1]–[N10]: N1 business question (why Scout churn hurts confidence), N2 churn definition and
  windows, N3 features and why each might matter, N4 leakage and the time-based split, N5 baselines and class imbalance,
  N6 logistic regression (log-odds, scaling, regularisation), N7 trees / forests / boosting (bias–variance), N8 metrics (ROC vs PR AUC,
  Brier, threshold choice, why not accuracy), N9 interpretation and the action (target bounties at at-risk Scouts),
  N10 limitations of synthetic data + 2-minute talk.

### Wrap-up
- [ ] **T17 (S)** `run_coursework.sh`: install check → transformer train + sample → churn (stand-in if needed) build → train_eval → explain.
- [ ] **T18 (S)** `test_notes_tags.py`. Full `pytest coursework/`. `grep -rn "SYNTHETIC:" coursework/` review.
- [ ] **T19 (S)** `docs/synthetic/coursework.md`, `docs/workstreams/coursework.md` (with contract change requests CR1–CR3). Final push.

## 3. Interfaces

**Consumed** (see `docs/CONTRACTS.md`)
| Interface | From | Used for |
|---|---|---|
| `venues.name` in `data/manhattan_bars.db` (read-only) | existing pipeline | transformer corpus |
| `data/live_sim.db` (v2 §D; env `LIVE_SIM_DB`) | live-sim | container for all syn_ tables below, read-only |
| `syn_scouts(scout_id, display_name, joined_at, reputation, points, level, reports_count, last_active_at, is_synthetic)` | live-sim | churn: `scout_id`, `joined_at` only. reputation/points/level/reports_count/last_active_at are end-of-sim snapshots and would leak |
| `syn_scout_reports(…, verified_presence, status, distance_m, is_synthetic)` | live-sim | churn: all activity features + label (`status='removed'` dropped) |
| `syn_points_ledger(entry_id, scout_id, report_id, bounty_id, points, reason, ts, is_synthetic)` | live-sim | points before the cutoff |
| `syn_bounties(…, claimed_by, expires_at, claimed_at, is_synthetic)` | live-sim | feature `bounties_claimed_28d` |
| `syn_scout_reputation_history(scout_id, as_of_date, reputation, points, level, is_synthetic)` | live-sim (v2.1) | as-of reputation/points/level features (latest row with `as_of_date < cutoff`) |
| `syn_scout_truth(scout_id, archetype, home_venue_id, true_accuracy, cohort_week, churned_at, is_synthetic)` | live-sim | **evaluation only** (`evaluate_truth.py`), never a feature |
| `data/launch_venues.csv` | contracts | venue_ids for the stand-in generator |

**Provided**
| Output | Consumer | Contract status |
|---|---|---|
| `coursework/tiny_transformer/outputs/synthetic/generated_names.csv` (`name, temperature, is_novel, is_synthetic`) | optional: live-sim/frontend placeholder names | informal, not in CONTRACTS |
| `coursework/churn/outputs/synthetic/scout_churn_risk.csv` (`scout_id, cutoff, churn_prob, is_synthetic`) | optional: tableau tile, future backend internal view | informal; CR if adopted |
| `report.md` files | Ryan / grader | — |

No HTTP endpoints and no `recs/` functions are provided.

## 4. Synthetic datasets

| Dataset | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| live-sim `syn_scouts`, `syn_scout_reports`, `syn_points_ledger`, `syn_bounties`, `syn_scout_reputation_history`, `syn_scout_truth` in `data/live_sim.db` (owned and registered by live-sim; coursework only reads) | Scout accounts, reports, points, bounties; truth for eval | live-sim generator, seed 42 | real backend tables `scouts`, `scout_reports`, `points_ledger`, `bounties`, `scout_reputation_history` (v2 §E: same names without `syn_`); no truth table exists in real life | point `LIVE_SIM_DB`/the loader at the real DB, read with `INCLUDE_SYNTHETIC=0`, skip `evaluate_truth.py` |
| `coursework/churn/outputs/synthetic/standin_scouts.csv`, `standin_scout_reports.csv` (**fallback only**) | Scout accounts and their vibe-check reports over 12 weeks (Aug 27 → Nov 14), with drop-off | `make_standin_data.py --seed 0` (decaying Poisson engagement, weekend boost, bounty bump) | first live-sim `syn_` tables, then the real backend `scouts` / `scout_reports` tables | 1) set `--source db` (or `--source live-sim`) in `run_coursework.sh`; 2) `load.py` validates the columns; 3) rerun; 4) delete the stand-in files; 5) update the registry |
| `coursework/churn/outputs/synthetic/churn_dataset_<cutoff>.csv` | modelling table derived from the above | `build_dataset.py` | same table built from real reports | automatic once the inputs are swapped |
| `coursework/churn/outputs/synthetic/scout_churn_risk.csv` | churn predictions | `train_eval.py` | predictions on real Scouts | automatic |
| `coursework/tiny_transformer/outputs/synthetic/generated_names.csv` | venue names | `sample.py` from a model trained on **real** SLA names | n/a: by nature generated. Never shown as real venues | keep `is_synthetic=1`. Don't use as venue data |
| `coursework/tests/fixtures/synthetic/*.csv` | 3–5 Scouts / ~20 reports | hand-written | n/a (test fixtures) | none |

The transformer corpus itself is **real** public data (SLA license names), not synthetic.

## 5. Test plan

| Area | Test | Pass condition |
|---|---|---|
| tokenizer | round-trip, special tokens | exact equality |
| attention | numpy by hand == torch `Head` | max abs diff < 1e-6 |
| causal mask | perturb future tokens | logits at ≤ t unchanged (atol 1e-6) |
| learning | overfit 8 names | loss < 0.1 in ≤ 300 steps |
| training | full run | val loss < bigram baseline; `metrics.json` valid |
| sampling | n=50, T=0.8 | all end at `<e>` or max length; novelty reported |
| churn features | leakage test | features identical with/without post-cutoff rows |
| churn features | as-of test | reputation feature for a fixture Scout equals the history row just before the cutoff, not the final value |
| churn features | snapshot-column test | no `syn_scouts` end-of-sim column in the feature list; `syn_scout_truth` not referenced outside `evaluate_truth.py` (grep) |
| churn labels | fixture | expected labels [0,1,excluded] |
| churn pipeline | stand-in end to end | report.md has 5 models × both splits; AUC in [0,1]; best > dummy |
| notes | tag check | every `[N#]` in code ↔ NOTES heading |
| hygiene | grep | each synthetic read/write has `# SYNTHETIC:`; only owned paths changed |

Run: `pytest coursework/ -q` (< 60 s), then `bash coursework/run_coursework.sh` (≤ 15 min).

## 6. Demo script (≈ 5 min, for class or grader)

1. (30 s) "Two individual exercises tied to Nightlife Autopilot: a tiny transformer that learned what Manhattan bar names look like, and a model that flags Scouts likely to stop reporting."
2. (90 s) Transformer: show `NOTES.md` [N6] attention by hand, then run `python -I coursework/tiny_transformer/sample.py --n 10 --temperature 0.8`. Show the loss curve vs the bigram baseline line and the novelty rate. Then try T=0.3 vs T=1.2 to show the temperature effect.
3. (90 s) Churn: explain the cutoff timeline picture (Aug 27 … features … Oct 1 cutoff … label to Oct 21 | test cutoff Oct 22 … label to Nov 11). Show `report.md`: the dummy vs logistic vs trees table, with PR AUC against the base rate.
4. (60 s) Interpretation: LR odds ratios (e.g. days_since_last_report ↑ → churn ↑), the depth-3 tree printed, and the action: "send bounties to the top-10% risk Scouts to keep confidence scores up."
5. (30 s) Limitations: synthetic Scouts (marked, swappable), small corpus, CPU-only tiny model. What changes with real data.

## 7. Explanation-notes checklist (for Ryan)
Before submitting, Ryan should be able to answer without looking:
- Why does the bigram baseline matter, and what does "nats per character" mean?
- What would break if the causal mask were removed?
- Why is temperature < 1 more conservative?
- Why split churn data by time and not randomly?
- Why is PR AUC more informative than accuracy when ~20% of Scouts churn (placeholder rate)?
- When would you pick logistic regression over gradient boosting even if its AUC is a bit lower?
