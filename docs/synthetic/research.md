# Synthetic data registry: research workstream

All research synthetic data are CSV files in `research/synthetic/`. **No database
tables** (CONTRACTS v2 §E): nothing is loaded into `manhattan_bars.db` or
`live_sim.db`. Every row has `is_synthetic = 1`, every ID starts with `syn-`, and
every quote's text starts with `[SYNTHETIC] `. Generator:
`python -I research/gen_synthetic.py --seed 42` (deterministic, < 1 s, no network).
Every prior is in `PRIORS` at the top of the script, and each carries a
`# SYNTHETIC:` comment naming the real question that replaces it.
Validator: `python -I research/validate.py`. Tests: `python -I -m pytest research/tests -q`.

`research/competitors.csv` is **real** desk research, not synthetic, and is not listed here.

| File / table | What it imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `research/synthetic/syn_interviews.csv` (15 rows: 8 consumer, 3 scout, 4 operator) | Coded notes from semi-structured interviews | `gen_synthetic.make_interviews`, seed 42. Latent engagement z ~ N(0,1) (+1 for Scouts) drives nights out, bad pick, would_scout and concept reaction. Factors are drawn from the importance prior. `venue_mentions` are random launch `license_id`s. Operator WTP is drawn from `{0, 0, 25, 49, 49, 99, 150}` | `research/interviews/interviews.csv`, filled from `research/interview_guide/note_template.md` (IDs `int-r-###`, `is_synthetic=0`) | 1. Log real rows with the same columns. 2. `python -I research/validate.py --real`. 3. `python -I research/analysis.py --source real`. 4. Re-tag `research/summary.md` findings as `[REAL n=…]`. 5. Keep the synthetic CSV for demos or delete it; there's no DB to clean. |
| `research/synthetic/syn_interview_quotes.csv` (4–6 per interview; 75 rows) | Tagged, anonymized verbatim quotes | `gen_synthetic.make_quotes`: template sentences per theme × hypothesis × sentiment (`QUOTE_TEMPLATES`), filled with sampled numbers. No real venue or person named | `research/interviews/quotes.csv` (IDs `q-r-####`), transcribed from notes with no PII | Same as above. Remove the `[SYNTHETIC] ` prefix rule only for real rows (the validator checks it only for synthetic ones). |
| `research/synthetic/syn_survey_responses.csv` (300 rows) | Online survey export (Google Forms) mapped to the codebook | `gen_synthetic.make_survey`. z ~ N(0,1) drives nights out (Poisson), bad pick, would_use_weekly (logistic), would_scout (ordinal cuts) and NPS. Importance Likerts come from a Dirichlet over 8 factors. Tools are Bernoulli per tool. `submitted_at` is uniform over Oct 26 to Nov 12, 2026, ET | `research/survey/responses.csv`: the real export renamed and recoded per `research/survey/codebook.csv` (IDs `srv-r-####`, `is_synthetic=0`) | 1. Export the CSV. 2. Rename and recode columns per the codebook (see `research/survey/questions.md`, "Export → codebook mapping"). 3. `python -I research/validate.py --real`. 4. `python -I research/analysis.py --source real`. 5. Point the tableau extract at `research/survey/summary_tables.csv`. |
| `research/synthetic/summary_tables.csv` (145 rows: `metric, segment, value, n, is_synthetic`) | Aggregated findings for the voice-of-customer dashboard | `python -I research/analysis.py --source synthetic` over the three CSVs above | Same script with `--source real` → `research/survey/summary_tables.csv` | Re-run with `--source real`. Charts must drop the "demo data" title only once `is_synthetic = 0`. |

Downstream placeholders that come from this data (other workstreams should mark them `# SYNTHETIC: research survey …`):
- ml-recs default match-weight order ← `rank_importance_*` (survey Q9).
- specs freshness half-life / stale tag sanity check ← `median_freshness_tolerance_min` (Q11).
- live-sim Scout supply ← `pct_scout_ge1_report_per_night`, `pct_points_value_pref_*` (Q15–17).
- coursework label ← `would_use_weekly` (Q13).
