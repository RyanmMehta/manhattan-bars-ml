# RULES — research build session

Read this before doing anything in the research workstream. It is binding for
the build session (CLAUDE.md style). If a rule conflicts with
`docs/CONTRACTS.md`, the contract wins.

## 1. Branch and git
- Work only on `nightlife/research` (branched from `nightlife/contracts`).
- Push with `git push -u origin nightlife/research`. No PRs, no pushes to `main`,
  no force-pushes, no history rewriting.
- Small commits, imperative subject (`research: add survey codebook`).
- Never edit `docs/CONTRACTS.md`. Proposed changes go under
  "Contract change requests" in `docs/workstreams/research.md`.

## 2. Folders you own (write only here)
- `research/` — all outputs, generator, validator, tests.
- `research/synthetic/` — synthetic CSVs.
- `docs/prd/research/` — these planning docs.
- `docs/workstreams/research.md` — what was built, how to run, open issues.
- `docs/synthetic/research.md` — synthetic registry.
- In `data/manhattan_bars.db`: only create/replace tables named `syn_interviews`,
  `syn_interview_quotes`, `syn_survey_responses`. The competitor list is real
  desk research (see §5) and is stored as CSV only, not in the DB.

## 3. Must not touch
- `src/`, existing DB tables/views (`venues`, `v_bars`, `venue_features`,
  `synthetic_*`, other workstreams' `syn_*` tables), `data/raw/`,
  `data/launch_venues.csv`, `run_all.sh`, `requirements.txt`.
- Other workstreams' folders (`docs/specs/`, `analytics/`, `simulator/`,
  `data/synthetic_live/`, `recs/`, `backend/`, `frontend/`, `coursework/`).
- If you need something from them, write it in `docs/workstreams/research.md`
  → "Requests to other workstreams".

## 4. Stack and versions
- Python 3.13, run scripts with `python -I`.
- Allowed libs: stdlib, `numpy>=2.0`, `pandas>=3.0` (already in
  requirements.txt). `pytest` for tests (dev only, not added to requirements.txt;
  note it in the workstream doc). No new runtime dependencies.
- SQLite via stdlib `sqlite3`. Markdown for docs. CSV: UTF-8, comma, header row,
  `\n` line endings, ISO 8601 dates (`America/New_York` for timestamps).

## 5. Data rules
- **Synthetic marking (mandatory, per contract):**
  1. Every synthetic CSV/table has `is_synthetic` (1 = synthetic, 0 = real).
  2. Synthetic files only under `research/synthetic/`; DB tables prefixed `syn_`.
  3. Code that creates/uses synthetic data carries
     `# SYNTHETIC: <real source that replaces this>` at the spot.
  4. Every synthetic dataset is listed in `docs/synthetic/research.md` with:
     file/table, what it imitates, how generated (script + seed), real source
     that replaces it, swap steps.
  5. Any chart/figure made from synthetic rows has "demo data" in its title.
  6. Synthetic quote text starts with `[SYNTHETIC] `.
- Real interview rows use the same schema with `is_synthetic = 0` and live in
  `research/interviews/` (not under `synthetic/`).
- **Desk research is real data**, not synthetic: `research/competitors.csv` has
  no `is_synthetic` column but every row needs `source_url` and `retrieved_at`.
  Unknown → `unknown`. Never invent a funding amount, user count or date.
- **No PII in the repo**: no names, emails, phone numbers, handles or photos of
  interviewees. IDs only (`INT-R-001`, `SRV-R-0001`). Venue operator rows name
  the venue (public) but not the person.
- `venue_id` = SLA `license_id` from `data/launch_venues.csv`; validator rejects
  others.
- Complaint risk (311 model) is never presented as a quality or vibe signal.
- No scraping of sites whose ToS forbid it (Instagram, Google, Yelp, Resy, DICE).
  Read public pages manually and cite them.

## 6. Coding conventions
- One generator `research/gen_synthetic.py` with `--seed` (default 42),
  `--n-interviews` (15), `--n-survey` (300), `--no-db`. Pure functions per
  dataset; `main()` only wires I/O.
- Use `numpy.random.default_rng(seed)`; no global random state; output must be
  byte-identical for the same seed.
- Constants (distributions, priors) at top of file in one dict `PRIORS`, each
  with a `# SYNTHETIC:` comment saying which real result replaces it.
- Column names snake_case and identical to `research/survey/codebook.csv`.
- Docstring at top of each script: purpose, usage, outputs.
- Paths via `pathlib`, relative to repo root (`ROOT = Path(__file__).resolve().parents[1]`).

## 7. Testing requirements
- `research/tests/` with pytest; run `python -I -m pytest research/tests -q`.
- Required tests:
  - determinism: two runs with seed 42 → identical CSV hashes;
  - schema: every column in codebook present, types/ranges/allowed values hold;
  - `is_synthetic == 1` for every generated row;
  - every `venue_id` mentioned ∈ launch venues;
  - no PII: regex scan of all `research/**` CSV/MD for emails/phone numbers;
  - competitors.csv: required columns non-empty, `retrieved_at` parses as a date;
  - DB load: `syn_*` tables row counts match CSVs and no non-research table changed
    (compare table list + row counts of `venues`, `v_bars` before/after).
- `python -I research/validate.py` must exit 0.

## 8. Definition of done
- All OUTLINE.md tasks for the phase checked off.
- Generator + validator + tests pass locally; commands documented in
  `docs/workstreams/research.md`.
- `docs/synthetic/research.md` lists every synthetic dataset (5 fields each).
- `research/summary.md` findings tagged `[SYNTHETIC]` or `[REAL n=…]`.
- Competitor rows all sourced and dated within 7 days of the demo.
- No files changed outside owned folders (`git diff --stat nightlife/contracts`).
- Branch pushed; master session notified.
