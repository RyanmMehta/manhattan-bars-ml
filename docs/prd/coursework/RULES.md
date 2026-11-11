# RULES — coursework build session

Read this before writing any code in the coursework workstream. It works like a
CLAUDE.md. Also follow `docs/CONTRACTS.md`. If the two conflict, CONTRACTS.md wins.

## 1. What this workstream is
Ryan Mehta's two individual course exercises: (a) a tiny character-level
transformer trained on Manhattan venue names, and (b) a Scout churn model. They are
**individual assignments**. Ryan must be able to explain every line, so simplicity
beats cleverness every time.

## 2. Stack and versions
- Python 3.13 (repo uses `python -I` and `.venv`, see `run_all.sh`).
- Existing deps from `requirements.txt`: pandas ≥ 3.0, numpy ≥ 2.0, scipy ≥ 1.14, scikit-learn ≥ 1.6.
- Added for coursework only, in `coursework/requirements.txt` (do **not** edit the root file):
  `torch>=2.5` (CPU wheel: `--index-url https://download.pytorch.org/whl/cpu`), `matplotlib>=3.9`, `pytest>=8`.
- No other libraries (no Hugging Face, Lightning, XGBoost, LightGBM, Optuna, SHAP). Use scikit-learn's
  `HistGradientBoostingClassifier` and `permutation_importance`.
- CPU only. Don't use `.cuda()`. Use `torch.manual_seed`, `numpy.random.default_rng(seed)`, and sklearn `random_state`.
- SQLite via the standard-library `sqlite3`, read-only: `sqlite3.connect("file:data/manhattan_bars.db?mode=ro", uri=True)`.

## 3. Folder ownership
You own and may write only:
- `coursework/**`
- `docs/workstreams/coursework.md`
- `docs/synthetic/coursework.md`
- `docs/prd/coursework/**` (update the plan if it changes)

Read-only: `data/manhattan_bars.db`, `data/live_sim.db` (live-sim output, CONTRACTS v2 §D; path via env `LIVE_SIM_DB`),
`data/launch_venues.csv` (header `license_id`, alias it `AS venue_id`), `data/synthetic_live/**`, `src/**`.

**Evaluation-only tables** (`syn_scout_truth`, `syn_true_state`): read them only in `churn/evaluate_truth.py`. Never use them as features.
Also never use `syn_scouts` end-of-sim snapshot columns (`reputation`, `points`, `level`, `reports_count`, `last_active_at`) as features.

**Must not touch:** `docs/CONTRACTS.md`, `src/`, root `requirements.txt`, `run_all.sh`, `data/manhattan_bars.db`
(never write tables into it), `simulator/`, `recs/`, `backend/`, `frontend/`, `research/`, `analytics/`,
`docs/specs/`, other workstreams' docs, `main` branch. No PRs. Push only `nightlife/coursework`.

## 4. Coding conventions (made for learning)
- Each script starts with a docstring: purpose, inputs, outputs, how to run, and the step list.
- Plain functions and at most one small class per concept (e.g. `Head`, `MultiHeadAttention`, `Block`, `TinyGPT`).
  No inheritance trees, decorators, metaprogramming or config frameworks. Use `argparse` and module-level constants.
- Write explicit loops and shapes. Write a shape comment on every tensor line in the model, e.g. `# (B, T, C)`.
- Name things in full words: `block_size`, `n_embd`, `days_since_last_report`. Avoid one-letter names except
  `B, T, C` in the model, where they get explained once.
- Each function ≤ ~40 lines. Each file ≤ ~250 lines.
- Comments explain **why**, not only what. Every comment that a NOTES.md section depends on carries a tag like `# [N3]`.
- No notebooks as the source of truth. A notebook may be exported later from the `.py` files.
- Formatting: PEP 8, 100-char lines. Type hints on function signatures.
- Paths via `pathlib`, relative to the repo root (`ROOT = Path(__file__).resolve().parents[2]`).
- Outputs go to `coursework/<exercise>/outputs/`, which is git-ignored except `report.md`, `metrics.json` and small PNGs (< 300 KB).
  Model checkpoints (`*.pt`) are **not** committed.

## 5. Explanation notes (required)
- Each exercise has `NOTES.md` with numbered sections `[N1]…[Nk]`, one per step, in the order the code runs.
- Each section has: what the step does in one plain paragraph, the code location (`file.py:function`),
  a small worked example or picture in words, a "common mistake" line, and 1–2 self-check questions.
- Keep the voice plain. No hype. Define each term the first time it appears.
- End each NOTES.md with "What I would say in a 2-minute presentation" (5 bullets) and "Limitations".

## 6. Testing requirements
- `pytest coursework/` must pass in < 60 s on CPU (use tiny configs in tests).
- Transformer tests: tokenizer round-trip (`decode(encode(s)) == s`); causal mask (output at position t does not change
  when tokens > t change); hand-worked attention example matches to 1e-6; one training step lowers the loss on a fixed
  batch; overfit test (the model memorises 8 names to loss < 0.1 within 300 steps); sampling stops at `<e>` or max length.
- Churn tests: **no leakage** (deleting all reports after the cutoff leaves features unchanged); label correctness on a
  hand-made 3-Scout fixture; Scouts who are not active before the cutoff are excluded; metrics function matches sklearn on a fixture;
  the pipeline runs end to end on the stand-in data.
- Fixtures are tiny inline DataFrames or CSVs under `coursework/tests/fixtures/synthetic/` with `is_synthetic=1`.

## 7. Synthetic-data marking (mandatory, from CONTRACTS.md)
- Every synthetic CSV/table has an `is_synthetic` column = 1.
- Synthetic files live under a path containing `synthetic` (e.g. `coursework/churn/outputs/synthetic/`).
  Never create DB tables. If one ever becomes necessary, prefix it `syn_`. Synthetic IDs in the stand-in start with `syn-`
  (`syn-s-0042`, `syn-r-000123`), per CONTRACTS v2 §D.
- Every code line that reads or creates synthetic data has a comment
  `# SYNTHETIC: <real source that replaces this>`, e.g.
  `# SYNTHETIC: replace with real scout_reports table from backend DB once Scouts are live`.
- Register every synthetic dataset in `docs/synthetic/coursework.md` with: file/table, what it imitates, how it was
  generated (script + seed), real source that replaces it, swap steps.
- Generated venue names from the transformer count as synthetic: `is_synthetic=1` and listed in the registry.
- Every report/plot built on synthetic data has the title suffix "(synthetic data)".

## 8. Honesty rules
- Report every model, including ones that lose. Never pick the threshold or the model on the test set.
- Always show the baseline (bigram / majority class) next to the model.
- Don't call synthetic churn results evidence about real Scouts.
- If a target in the PRD is missed, say so in `report.md`. Don't tune until it passes.

## 9. Git
- Branch `nightlife/coursework` only. Small commits, one per OUTLINE task, with messages like `coursework: T3 tokenizer + tests`.
- `git push -u origin nightlife/coursework`. No force-push unless the only change is a rebase of your own commits.

## 10. Definition of done
- [ ] `pip install -r coursework/requirements.txt` then `bash coursework/run_coursework.sh` runs both exercises end to end on CPU.
- [ ] `pytest coursework/` green.
- [ ] Transformer beats the bigram baseline on val loss. `metrics.json`, loss curve and 20 samples saved.
- [ ] Churn `report.md` has all 5 models × (CV, out-of-time test) × (ROC AUC, PR AUC, Brier, P/R/F1 at the chosen threshold).
- [ ] Both `NOTES.md` complete (every `[N#]` tag in code has a section and vice versa: a test or script checks this).
- [ ] `docs/synthetic/coursework.md` and `docs/workstreams/coursework.md` written (with how to run, results, open issues, contract change requests).
- [ ] Every synthetic touchpoint has `is_synthetic`, a `synthetic` path, and a `# SYNTHETIC:` comment (`grep` check passes).
- [ ] Nothing outside the owned folders changed (`git diff --name-only nightlife/contracts` shows only owned paths).
- [ ] Branch pushed by **Fri Nov 13 18:00 ET** (CONTRACTS v2 §I).
