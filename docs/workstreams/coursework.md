# Workstream: coursework (as built)

Owner: Ryan Mehta. Branch: `nightlife/coursework` (not merged to main). Built Nov 17, 2026.
Folder: `coursework/` only. Plan: `docs/prd/coursework/`. Synthetic registry: `docs/synthetic/coursework.md`.

## What was built
- **(a) Tiny transformer** (`coursework/tiny_transformer/`): char-level GPT (2 layers, 4 heads, 64 dims,
  block 32, dropout 0.1, 107,307 params) trained from scratch on 4,986 cleaned venue names from
  `data/manhattan_bars.db`. Unigram/bigram baselines, a numpy hand-worked attention example, training
  with cosine LR and early stopping, sampling with temperature/top-k, a 3-run ablation, `NOTES.md` [N1–N12],
  notebook `tiny_transformer.ipynb`.
- **(b) Scout churn** (`coursework/churn/`): loader (live_sim.db or stand-in), stand-in generator,
  leakage-free dataset builder (two Thursday-noon snapshots), 5 models with repeated stratified CV and an
  out-of-time test, interpretation (odds ratios, tree text, permutation importance, targeting table, plots),
  evaluation-only truth check, `NOTES.md` [N1–N10], notebook `churn.ipynb`.
- `AI_USE.md` (drafted-with-Claude disclosure; Ryan must check the course policy), `README.md`,
  `run_coursework.sh`, `make_notebooks.py`, 22 pytest tests.

## How to run
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt -r coursework/requirements.txt
bash coursework/run_coursework.sh      # ~2.5 min, 4 CPU cores
python -m pytest coursework -q         # 22 passed in ~30 s
python -I coursework/make_notebooks.py # optional: rebuild/execute notebooks
```

## Results (seed 0)
| | metric | value | PRD target |
|---|---|---|---|
| transformer | best val loss | 2.113 nats/char (ppl 8.27), step 1,200 of 1,700 (early stop) | < bigram 2.643: met (20.0% lower, target 10%) |
| transformer | runtime | 39 s training (full run script ~2.5 min incl. ablation) | ≤ 10 min: met |
| transformer | novelty at T = 0.8 | 100% (20 saved), 100% of 200 | ≥ 70%: met |
| transformer | determinism | rerun gave 2.1131 again | within 1e-3: met |
| churn | data | live-sim `data/live_sim.db` (origin/nightlife/live-sim @ 0d2a26c, seed 42, 209 Scouts) | — |
| churn | snapshots | train Oct 1: 86 Scouts / 27 churned (31.4%); test Oct 22: 101 / 41 (40.6%) | ≥ 60 / ≥ 15: met |
| churn | selected model (by CV) | logistic regression, C = 0.1 (CV AUC 0.887 ± 0.045) | — |
| churn | test ROC AUC | 0.852 [0.77, 0.92] (forest 0.864, boosting 0.840, tree 0.788, majority 0.500) | ≥ 0.75: met |
| churn | test PR AUC | 0.780 vs base 0.406 (1.92×; max possible 2.46×) | ≥ 2×: **missed** (forest 2.08×, not selected: the test set doesn't choose) |
| churn | test Brier | 0.148 (best of all models) | ≤ logistic's: met |
| churn | targeting | riskiest 10% → 9 of 10 churned | — |
| churn | truth check | label agrees with simulator truth for 82%; AUC vs truth 0.710 | AUC < 0.95 (not too easy): ok |

The stand-in results (logistic test AUC 0.826, PR AUC 0.760) are kept as an appendix in `coursework/churn/NOTES.md`
and in full in `coursework/churn/outputs/standin/`.

## Assumptions and decisions (recorded instead of asking)
1. **Assignment sheets and AI-use policy were not provided.** I delivered heavily commented `.py` scripts (source of
   truth), plus a matching executed `.ipynb` and a `NOTES.md` for each exercise, and `coursework/AI_USE.md`. Ryan must
   check the rubric (PRD Q1) and the AI policy (Q2) before submitting.
2. **live-sim.** At first `origin/nightlife/live-sim` (b94468f) had no `simulator/`, so I built the planned stand-in (T11).
   live-sim then shipped (0d2a26c). I built `data/live_sim.db` from a separate worktree checkout of that branch with
   `python -m simulator --seed 42 --out data/live_sim.db` (no `-I`, per master; validation OK, 8.5 s) and reran the churn exercise.
   Neither `simulator/` nor the DB is committed here. `load.py` uses the DB when present and the stand-in otherwise.
   The stand-in results are kept as an appendix.
3. **Stand-in cohort sizes (stand-in only).** With 12 equal cohorts (about 12–13 Scouts each), the Oct 1 snapshot had only about 50 eligible
   Scouts and about 8 churners, which is too few. The stand-in uses a 30-Scout launch week and about 11 a week after that. It still has
   12 weekly cohorts, 150 Scouts, and 43% truth-churned by Nov 14 (contract target 40–60%).
4. **Removed reports.** OUTLINE T10 said to drop `status='removed'` in `load.py`. That would make `share_flagged_or_removed`
   impossible to compute, so `load.py` keeps them, and `build_dataset.py` excludes removed reports from activity counts,
   eligibility and the label, while counting them in the quality share.
5. **Validation loss** is computed on all 499 val names every eval (not 20 random batches). It is exact and deterministic.
6. **Overfit test.** The RULES target "8 names to loss < 0.1" is impossible as written: the first character is a 1-in-8
   choice (ln 8 = 2.08 nats), which is irreducible. The test excludes that one target. All other positions reach < 0.1.
7. **Sampling** never emits `<s>` in the middle of a name (found by the sampling test on an untrained model).
8. **Imports under `python -I`.** Each script adds the repo root to `sys.path` (isolated mode drops the script dir).
9. **Boosting** has no class weights (the grid only varies the learning rate, per the plan).
10. **live-sim formats.** `level` is a name (Rookie/Regular/Insider/Legend), so it is mapped to an ordinal 1–4. 47 Scouts signed up
   Aug 24–26, before the first night, and get cohort_week 0 (not negative). Status `disputed` counts as activity (only `removed` doesn't).
11. The **block_size = 16 ablation** truncates names longer than 15 characters, so it is only roughly comparable.
12. Deps were installed into the container's system Python. `nbformat`/`nbconvert`/`ipykernel` were added to
    `coursework/requirements.txt` only to build notebooks. `tabulate` is not used.
13. Timeline: delivered Nov 17, after the Nov 13 18:00 ET hand-off (CONTRACTS v2 §I).

## Open issues
- If live-sim changes its seed or parameters, rebuild `data/live_sim.db` and rerun `run_coursework.sh` and `make_notebooks.py churn`.
- The PR AUC lift target (2×) is missed at 1.92×. With a 41% base rate the ceiling is 2.46×, so the target may need to be lowered.
- PRD's "≥ 90% plausible by manual read of 50 samples" is not done. Ryan should read `generated_names.csv` himself.
- Small churn sample: CIs overlap between logistic, forest and boosting. Stacking snapshots with grouped CV (PRD Q7) is a stretch goal.
- Late-submission deadlines (Q4) unknown.

## Contract change requests
None. (The run script uses the contract build command without `-I`, matching CONTRACTS as updated for live-sim.)

## Files changed outside `coursework/`
`docs/workstreams/coursework.md`, `docs/synthetic/coursework.md` only.
