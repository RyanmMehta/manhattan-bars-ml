# Workstream: research (as built, 2026-11-17)

Branch `nightlife/research`. Owner: research (project owner Ryan Mehta). Only
`research/`, `docs/prd/research/`, `docs/workstreams/research.md` and
`docs/synthetic/research.md` were changed.

## What was built

| Deliverable (PRD) | File | Status |
|---|---|---|
| G1/R1 Competitor refresh | `research/competitors.csv` (20 rows, all sourced, `retrieved_at` 2026-11-17) | done (real desk research) |
| G2/R2 Matrix + positioning + 2×2 | `research/competitive_matrix.md` | done (real) |
| Hypotheses | `research/hypotheses.md` (H1–H12) | done |
| G3/R3 Interview guides | `research/interview_guide/{consumer,scout,operator,note_template,recruiting_plan}.md` | done, ready for real use |
| G4/R4 Survey + codebook | `research/survey/questions.md` (17 Q), `research/survey/codebook.csv` | done, ready to build in Google Forms |
| G5/R5 Synthetic dataset | `research/gen_synthetic.py` → `research/synthetic/syn_*.csv` | done (**synthetic**) |
| Validator + tests | `research/validate.py`, `research/tests/` (21 pass, 1 skipped) | done |
| G6/R6 Business model | `research/business_model.md` | done (hypotheses) |
| G7/R7 Summary + hand-offs | `research/summary.md`, `research/synthetic/summary_tables.csv`, `research/presentation_notes.md` | done (tagged `[SYNTHETIC]` / `[REAL desk]`) |
| Phase E real data | `research/interviews/` (empty) | not started: 0 real interviews, 0 survey responses |

## How to run

```
python -I research/gen_synthetic.py --seed 42          # < 1 s, deterministic, CSV only
python -I research/analysis.py --source synthetic
python -I research/validate.py                         # exit 0
pip install pytest   # dev only, not in requirements.txt
python -I -m pytest research/tests -q
```

The tests cover: determinism (seed 42 twice gives the same SHA-256; seed 43
differs; the committed CSVs match seed 42); codebook ↔ columns; types, ranges and
allowed values; `is_synthetic = 1`; `syn-` IDs; `[SYNTHETIC] ` quote prefix;
venue_ids ∈ `data/launch_venues.csv`; genres ∈ the 17 contract slugs; a PII
regex scan of `research/**`; competitor rows sourced and dated within 7 days of
the demo; `data/*.db` unchanged after the generator runs. The validator's own
negative tests check that it rejects bad venue, flag, range, genre, ID prefix and quote prefix.

## Assumptions (made autonomously, per the build brief)

- No interview incentive budget. The guides and recruiting plan offer none.
- No real interviews done yet. All interview/survey numbers are synthetic, and
  `summary.md` says so on every row.
- Survey n = 300 synthetic (the PRD default). Real target n ≥ 100.
- `simulator/config/genres.json` is not on this branch. The generator uses the
  copied 17-slug constant (tested against the contract list), reads the JSON
  automatically when present, and a test checks it after merge (skipped now).
- Survey adds two columns beyond PRD §4.4: `favorite_genres` (Q10, pipe, may be
  empty) and `genre_no_pref` (0/1), following the OUTLINE note about a separate
  "no preference" checkbox. Both are in the codebook.
- Operator interview rows leave consumer-only fields null (`typical_group_size`,
  `bad_pick_last_month`, `top_factor_*`, `freshness_tolerance_min`,
  `would_scout`, `scout_motivator`). `age_band = na`. Codebook marks them nullable.
- `would_scout` is stored as an int 0–3 (0 no, 1 maybe, 2 yes, 3 already).
- `freshness_tolerance_min` is a fixed option set {15, 30, 45, 60, 90, 120} so the
  survey stays multiple choice.
- `nYtevibe` and `What's Playin` could not be verified as existing products.
  Their rows are `unknown`, citing the closest-name candidate, with the caveat in
  notes. Individual app developers' names were removed from notes (only
  company founders named in press are kept).
- Competitor statuses with weak evidence are listed in
  `research/competitive_matrix.md` and should be re-checked before external use.
- Synthetic quotes never name real venues or people, so no claims are invented
  about real LES bars.

## Open issues / follow-ups

1. Run real interviews (recruiting plan, from the week of Nov 17) and field the survey, then follow the swap steps in `docs/synthetic/research.md`.
2. Re-check the competitor rows with weak evidence: c01, c03, c04, c05, c12, c14, c18–c20.
3. Use the frontend mockup PNGs in the concept test once they are merged (the guides default to a verbal description).
4. The synthetic NPS is very negative (−51) because of the priors. It's harmless for the demo, but don't present it as a signal.

## Requests to other workstreams

- tableau: build the "voice of customer" view from `research/synthetic/summary_tables.csv`, with "demo data" in the title.
- ml-recs / specs: if you use the factor rank or freshness tolerance, mark it `# SYNTHETIC: research survey Q9 / Q11`.
- integration: put `research/presentation_notes.md` bullets into the deck. Slide 4 needs the demo-data badge.

## Contract change requests

None.
