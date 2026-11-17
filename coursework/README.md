# coursework/: Ryan Mehta's individual exercises

Two course exercises tied to Nightlife Autopilot. This folder is **not** part of the deployed app.

| Exercise | What | Start here |
|---|---|---|
| (a) Tiny transformer (due Sept 22) | a 107k-parameter GPT trained from scratch on 4,986 real Manhattan liquor-licence names | `tiny_transformer/NOTES.md`, `tiny_transformer/tiny_transformer.ipynb` |
| (b) Churn model (due Oct 27) | predicts which (synthetic) Scouts stop reporting; majority vs logistic vs 3 tree models, split by time | `churn/NOTES.md`, `churn/outputs/report.md`, `churn/churn.ipynb` |

**Read `AI_USE.md` before submitting.** This code was drafted with Claude, and the course's AI-use
policy has to be checked.

## Run

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt -r coursework/requirements.txt
bash coursework/run_coursework.sh         # both exercises end to end, about 2.5 min on 4 CPU cores
python -m pytest coursework -q            # 22 tests, about 30 s
python -I coursework/make_notebooks.py    # rebuild + execute the two notebooks (after the run)
```

Every script has `--help`, a docstring with its steps, and `[N#]` tags pointing to its `NOTES.md` section.

## Headline results (seed 0)

- Transformer: val loss **2.113 nats/char** (perplexity 8.27) vs bigram baseline 2.643, so **20% lower**. 39 s of training on CPU.
  Novelty 100% at T = 0.8.
- Churn (synthetic): logistic regression selected by CV. Out-of-time test ROC AUC **0.826 [0.73, 0.91]**, PR AUC
  **0.760** vs base rate 0.36. The riskiest 10% of Scouts churned at 89%.

## Layout

```
common.py                ROOT path, seeding, read-only SQLite, report-section writer
run_coursework.sh        runs everything
make_notebooks.py        builds the .ipynb walkthroughs from the .py code
tiny_transformer/        data.py baselines.py attention_by_hand.py model.py train.py sample.py NOTES.md
churn/                   load.py make_standin_data.py build_dataset.py train_eval.py explain.py evaluate_truth.py NOTES.md
tests/                   22 pytest tests (+ fixtures/synthetic/)
```

## Data

- Transformer corpus: **real** public data (`data/manhattan_bars.db`, `venues.name`, read-only).
- Churn: **synthetic**. It reads `data/live_sim.db` (live-sim, seed 42) when that file exists. Until then
  it uses the stand-in generator `churn/make_standin_data.py` (seed 0). Every synthetic file has
  `is_synthetic=1` and a `synthetic` path. Registry: `docs/synthetic/coursework.md`.

## Versions used for the committed outputs

Python 3.13.18, torch 2.15.0+cpu, scikit-learn 1.9.1, pandas 3.0.5, numpy 2.5.3, matplotlib 3.11.2.
