# research/: Nightlife Autopilot research workstream

Real desk research, ready-to-run interview and survey instruments, and a clearly
marked **synthetic** interview/survey dataset with the same shape the real data
will have. No real interviews or survey responses had been collected as of 2026-11-17.

| File | What | Real or synthetic |
|---|---|---|
| `competitors.csv` | 20 competitors and substitutes, each with `source_url` and `retrieved_at` | real (desk) |
| `competitive_matrix.md` | Feature matrix, failure hypotheses, positioning statement, 2×2 spec | real (desk) |
| `hypotheses.md` | H1–H12 with metrics and placeholder thresholds | plan |
| `interview_guide/` | consumer, scout, operator guides; note template; recruiting plan | instrument |
| `survey/questions.md`, `survey/codebook.csv` | 17-question survey and the column codebook | instrument |
| `interviews/` | real interview rows go here (`interviews.csv`, `quotes.csv`); empty for now | real (empty) |
| `synthetic/` | `syn_interviews`, `syn_interview_quotes`, `syn_survey_responses`, `summary_tables` | **synthetic** |
| `business_model.md` | Venue tiers, unit economics, falsification tests | hypotheses |
| `summary.md` | ≤ 10 tagged findings and hand-offs | mixed (tagged) |
| `presentation_notes.md` | Slide bullets for integration | mixed (tagged) |

```
python -I research/gen_synthetic.py --seed 42          # writes research/synthetic/*.csv
python -I research/analysis.py --source synthetic      # writes research/synthetic/summary_tables.csv
python -I research/validate.py                         # exit 0 = OK  (--real for real data)
python -I -m pytest research/tests -q                  # needs pytest (dev only)
```

Rules: `docs/prd/research/RULES.md`. Synthetic registry: `docs/synthetic/research.md`.
As-built notes: `docs/workstreams/research.md`.
