"""Build (and run) the two walkthrough notebooks from the .py source of truth.

Outputs: coursework/tiny_transformer/tiny_transformer.ipynb, coursework/churn/churn.ipynb
Run    : python -I coursework/make_notebooks.py            (needs nbformat, nbconvert, ipykernel)
Run the exercises first (bash coursework/run_coursework.sh): the notebooks read their outputs.
The notebooks only CALL functions from the .py files, so the code you defend is the .py code.
"""
import sys
from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).resolve().parent
md, code = nbformat.v4.new_markdown_cell, nbformat.v4.new_code_cell
SETUP = """# Find the repo root (the folder that contains coursework/) and make it importable.
import os, sys
from pathlib import Path
root = Path.cwd()
while not (root / "coursework").is_dir():
    root = root.parent
sys.path.insert(0, str(root)); os.chdir(root)
print("repo root:", root)"""

TRANSFORMER = [
    md("# Tiny transformer on Manhattan venue names\n\nA walkthrough of `coursework/tiny_transformer/`. "
       "Each step points to a section of `NOTES.md` ([N1]…[N12]). The `.py` files are the source of truth; "
       "this notebook only calls them. Run `python -I coursework/tiny_transformer/train.py --ablation` first."),
    code(SETUP),
    md("## [N1]–[N2] Load, clean and split the names (real public SLA licence data, read-only)"),
    code("from coursework.tiny_transformer.data import load_names, clean_all, split_names, Tokenizer, make_examples\n"
         "raw = load_names()\nnames = clean_all(raw)\ntrain, val = split_names(names, val_frac=0.1, seed=0)\n"
         "print(len(raw), 'raw ->', len(names), 'clean;', len(train), 'train /', len(val), 'val')\nprint(names[:8])"),
    md("## [N3] Baselines in nats per character"),
    code("import math\nfrom coursework.tiny_transformer import baselines\ntok = Tokenizer(train + val)\n"
         "print('uniform', round(math.log(tok.vocab_size), 4))\n"
         "print('unigram', round(baselines.unigram_loss(train, val, tok), 4))\n"
         "print('bigram ', round(baselines.bigram_loss(train, val, tok), 4))"),
    md("## [N4] Tokens: x is the sequence, y is the same sequence shifted by one (-100 = ignored)"),
    code("x, y = make_examples(['BAR 54'], tok, block_size=12)\n"
         "print('x:', [tok.itos[i] for i in x[0]])\nprint('y:', [tok.itos[i] if i >= 0 else -100 for i in y[0]])"),
    md("## [N6]–[N7] Attention by hand (3 tokens, d = 2) and the same numbers from `model.Head`"),
    code("import numpy as np, torch\nfrom coursework.tiny_transformer.attention_by_hand import attention_by_hand, X, W_Q, W_K, W_V\n"
         "from coursework.tiny_transformer.model import Head\nnp.set_printoptions(precision=4, suppress=True)\n"
         "hand = attention_by_hand()\nprint('weights (rows sum to 1, future = 0):\\n', hand['weights'])\nprint('output:\\n', hand['out'])\n"
         "head = Head(2, 2, 3, dropout=0.0)\nwith torch.no_grad():\n"
         "    head.query.weight.copy_(torch.tensor(W_Q.T)); head.key.weight.copy_(torch.tensor(W_K.T)); head.value.weight.copy_(torch.tensor(W_V.T))\n"
         "    print('torch Head output:\\n', head(torch.tensor(X).float().unsqueeze(0))[0].numpy())"),
    md("## [N8]–[N9] The model and its size"),
    code("from coursework.tiny_transformer.model import TinyGPT, count_params\nmodel = TinyGPT(tok.vocab_size)\n"
         "print(f'{count_params(model):,} parameters')\nprint(model.blocks[0])"),
    md("## [N10] A short training demo (300 steps) — the full run is `train.py`"),
    code("from coursework.tiny_transformer.train import train_model\n"
         "cfg = dict(seed=0, n_layer=2, n_head=4, n_embd=64, block_size=32, dropout=0.1, batch_size=64,\n"
         "           max_steps=300, eval_every=100, patience=5, lr_max=3e-3, lr_min=3e-4)\n"
         "demo = train_model(cfg, {'train': train, 'val': val, 'tok': tok})"),
    md("## [N12] Results of the full run (`outputs/metrics.json`, `outputs/loss_curve.png`)"),
    code("import json\nfrom IPython.display import Image, display\n"
         "m = json.loads(Path('coursework/tiny_transformer/outputs/metrics.json').read_text())\n"
         "print({k: m[k] for k in ['params', 'steps_run', 'runtime_seconds', 'best_val_loss', 'val_perplexity_per_char', 'improvement_vs_bigram_pct']})\n"
         "print('ablation:', [(a['variant'], round(a['best_val_loss'], 4)) for a in m.get('ablation', [])])\n"
         "display(Image('coursework/tiny_transformer/outputs/loss_curve.png'))"),
    md("## [N11] Sampling at three temperatures (SYNTHETIC names — never real venues)"),
    code("from coursework.tiny_transformer.sample import load_model, sample_names, novelty_rate\n"
         "gpt, itos = load_model()\ntrain_set = set(train)\nfor t in (0.3, 0.8, 1.2):\n"
         "    s = sample_names(gpt, itos, 50, t, seed=2)\n"
         "    print(f'T={t}: novelty {novelty_rate(s, train_set):.0%}  e.g.', s[:4])"),
]

CHURN = [
    md("# Scout churn model (synthetic data)\n\nA walkthrough of `coursework/churn/`, with steps matching "
       "`NOTES.md` [N1]…[N10]. **All Scouts are synthetic** (live-sim's `data/live_sim.db`, seed 42, when present; otherwise the marked stand-in). Run `bash coursework/run_coursework.sh` first; "
       "this notebook reads its outputs and calls the same functions."),
    code(SETUP),
    md("## Load the tables (live_sim.db if present, else the marked stand-in CSVs)"),
    code("from coursework.churn.load import load\n# SYNTHETIC: replace with the real backend tables\n"
         "data = load()\nprint('source:', data['source'])\nfor k in ['scouts', 'reports', 'ledger', 'bounties', 'rep_history']:\n"
         "    print(f'{k:12s}', len(data[k]))"),
    md("## [N2]–[N3] Two snapshots: features before the cutoff, label in the 21 days after"),
    code("from coursework.churn.build_dataset import build, FEATURES, TRAIN_CUTOFF, TEST_CUTOFF\n"
         "train, test = build(data, TRAIN_CUTOFF), build(data, TEST_CUTOFF)\n"
         "for name, df in [('train', train), ('test', test)]:\n"
         "    print(f'{name}: {len(df)} Scouts, base rate {df.churned.mean():.1%}')\ntrain.head()"),
    code("from IPython.display import Image, display\ndisplay(Image('coursework/churn/outputs/timeline.png'))"),
    md("## [N4] Leakage check: delete everything after the cutoff, the features must not change"),
    code("import pandas as pd\ncut = pd.Timestamp(f'{TRAIN_CUTOFF} 12:00', tz='America/New_York')\n"
         "trimmed = dict(data, reports=data['reports'][data['reports'].ts < cut], ledger=data['ledger'][data['ledger'].ts < cut])\n"
         "print('features identical:', build(trimmed, TRAIN_CUTOFF)[FEATURES].equals(train[FEATURES]))"),
    md("## [N5]–[N8] Results: 5 models, CV on train, one out-of-time test (from `outputs/metrics.json`)"),
    code("import json\nm = json.loads(Path('coursework/churn/outputs/metrics.json').read_text())\n"
         "rows = [{'model': n, 'settings': r['params'], 'cv_auc': round(r['cv_auc_mean'], 3), 'test_auc': round(r['test']['roc_auc'], 3),\n"
         "         'test_auc_ci': [round(v, 2) for v in r['test_roc_auc_ci']], 'test_pr_auc': round(r['test']['pr_auc'], 3),\n"
         "         'base_rate': round(r['test']['base_rate'], 3), 'brier': round(r['test']['brier'], 3), 'f1': round(r['test']['f1'], 2)}\n"
         "        for n, r in m['models'].items()]\nprint('selected by CV:', m['selected_model'])\npd.DataFrame(rows)"),
    md("## [N6] Logistic regression odds ratios (per +1 SD), refit live"),
    code("from coursework.churn.train_eval import make_model\nfrom coursework.churn.explain import odds_ratio_table\n"
         "lr = make_model('logistic', m['models']['logistic']['params']).fit(train[FEATURES], train.churned)\n"
         "odds_ratio_table(lr).head(8)"),
    md("## [N7] The shallow tree as text"),
    code("from sklearn.tree import export_text\ntree = make_model('tree', m['models']['tree']['params']).fit(train[FEATURES], train.churned)\n"
         "print(export_text(tree[-1], feature_names=FEATURES, decimals=1, show_weights=True))"),
    md("## [N8]–[N9] Curves, calibration, importance and the targeting view"),
    code("for png in ['roc_pr_test', 'calibration_test', 'permutation_importance']:\n"
         "    display(Image(f'coursework/churn/outputs/{png}.png'))"),
    code("from coursework.churn.explain import top_risk_table\ntop_risk_table(lr, test)"),
    md("## Evaluation-only truth check and limitations\n\nSee the last section of `outputs/report.md` "
       "(written by `evaluate_truth.py`, the only file that reads the simulator's truth table) and `NOTES.md` [N10]."),
]


def build(cells: list, path: Path) -> None:
    nb = nbformat.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3",
                                                                          "language": "python"}})
    ExecutePreprocessor(timeout=600, kernel_name="python3").preprocess(nb, {"metadata": {"path": str(path.parent)}})
    nbformat.write(nb, path)
    print(f"wrote and executed {path.relative_to(HERE.parent)} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    which = sys.argv[1:] or ["tiny_transformer", "churn"]
    if "tiny_transformer" in which:
        build(TRANSFORMER, HERE / "tiny_transformer" / "tiny_transformer.ipynb")
    if "churn" in which:
        build(CHURN, HERE / "churn" / "churn.ipynb")
