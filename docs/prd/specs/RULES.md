# RULES — specs build session

CLAUDE.md-style rules for the session that builds the specs workstream.
Read these first, then `docs/CONTRACTS.md`, then `docs/prd/specs/PRD.md` and
`OUTLINE.md`. If these rules and CONTRACTS.md disagree, CONTRACTS.md wins and
you log the conflict under "Contract change requests" in
`docs/workstreams/specs.md`.

## 1. What this workstream is
Specs produces **documents and test fixtures**, not application code. Its
output is the exact definition that live-sim, ml-recs, backend and frontend
implement: architecture, requirements, scoring formulas, trust rules,
evaluation plan and team workflow.

## 2. Stack and versions
- Docs: GitHub-flavoured Markdown; diagrams in Mermaid fenced blocks
  (` ```mermaid `) that render on GitHub. No images that can't be regenerated.
- Fixtures: JSON (UTF-8, 2-space indent, sorted keys) and CSV (comma, header
  row, `\n` line endings).
- Tooling: **Python 3.12, standard library only** (`json`, `csv`, `math`,
  `datetime`, `zoneinfo`, `unittest`). No pandas/numpy in specs tools, so the
  checker runs anywhere without installing `requirements.txt`.
- Run Python with `python -I` (isolated mode), as the rest of the repo does.
- Target stack you are *specifying* (do not install): FastAPI ≥ 0.115,
  Pydantic 2, SQLAlchemy 2, SQLite 3 → Postgres 16, React 18, Vite 5,
  TypeScript 5, Node 20 LTS, Render, Vercel. Exact pins are backend/frontend's
  call; record what they choose in ARCHITECTURE.md.

## 3. Folders you own (write only here)
| Path | Contents |
|---|---|
| `docs/specs/` | ARCHITECTURE.md, REQUIREMENTS.md, SCORING.md, PARAMETERS.md, TRUST.md, EVALUATION.md, team/ |
| `docs/specs/golden_synthetic/` | golden test vectors (synthetic, JSON) |
| `docs/specs/tools/` | `reference_scoring.py` (test oracle), `check_golden.py`, `check_docs.py` |
| `docs/specs/team/` | PULL_REQUEST_TEMPLATE.md, CONTRIBUTING.md, GOOD_FIRST_PRS.md |
| `docs/prd/specs/` | this planning set (PRD, RULES, OUTLINE) — update if plans change |
| `docs/workstreams/specs.md` | what was built, how to run checks, open issues, Contract change requests |
| `docs/synthetic/specs.md` | registry of every synthetic dataset specs created |

## 4. Must not touch
- `docs/CONTRACTS.md` (propose changes instead).
- `src/`, `data/manhattan_bars.db`, `data/raw/`, `data/launch_venues.csv`,
  `reports/`, `run_all.sh`, `requirements.txt` — read only.
- Other workstreams' folders: `research/`, `analytics/`, `simulator/`,
  `data/synthetic_live/`, `recs/`, `backend/`, `frontend/`, `coursework/`,
  other `docs/workstreams/*.md` and `docs/synthetic/*.md` files.
- `.github/` and root `CONTRIBUTING.md`: draft under `docs/specs/team/`;
  integration copies them (Contracts v2 §C).
- `main` branch. No PRs. Push only `nightlife/specs`.

## 5. Conventions
- One concept per file; every doc starts with a 3-line header: purpose,
  status (draft/agreed), last updated (YYYY-MM-DD).
- Every number that is a guess is tagged **(placeholder)** and appears once in
  `PARAMETERS.md` with: name, value, unit, used in, rationale, how to tune.
  Other docs reference the parameter name, e.g. `H_crowd`, not the number,
  except in worked examples.
- Formulas are written in a code block, in a form that translates line by line
  to Python. Define every symbol. State rounding: compute unrounded, round
  only the output field (vibe integer, confidence 2 dp, crowd/dancing 1 dp).
- Field and table names exactly as in CONTRACTS.md (`venue_id`, `ts`,
  `crowd`, `line_minutes`, …). Times are ISO 8601 with America/New_York offset.
- User stories: `US-<AREA>-<n>`, Given/When/Then acceptance criteria, MVP or
  Later tag, linked screen (frontend) and endpoint (backend).
- Synthetic ids use the v2 `syn-` prefix (`syn-r-000001`, `syn-s-0001`);
  genres come from the shared v2 vocabulary; fixture `now` = `DEMO_NOW`
  (`2026-11-14T23:30:00-05:00`).
- Constants in Contracts v2 §A are canonical; change them only by updating
  PARAMETERS.md and telling master (they override other teams' values).
- `venue_id` in fixtures must be real launch venue ids from
  `data/launch_venues.csv` (e.g. `0370-24-138636`), so fixtures load against
  the real venue list.
- Python: type hints, docstrings, no globals except constants in CAPS read
  from `PARAMETERS.md`'s machine-readable block, functions ≤ 40 lines.
- Plain, short sentences. No marketing copy.

## 6. Synthetic-data marking (mandatory, from CONTRACTS.md)
1. Every synthetic JSON object / CSV row has `"is_synthetic": 1`.
2. Synthetic files live under a path containing `synthetic`
   (`docs/specs/golden_synthetic/`). Any table you describe as synthetic is
   named with the `syn_` prefix.
3. Code that reads synthetic data has `# SYNTHETIC: <real source that
   replaces this>` on the line above the read.
4. Every synthetic dataset is listed in `docs/synthetic/specs.md` with:
   file/table, what it imitates, how it was generated, real source that
   replaces it, swap steps.
5. Docs that show synthetic numbers (worked examples, evaluation targets)
   say so in the caption: "synthetic example".

## 7. Testing requirements
- `python -I docs/specs/tools/check_golden.py` must pass: recomputes every
  golden vector with `reference_scoring.py` and compares to the stored
  `expected` block (vibe ±0, confidence ±0.005, match ±0).
- `python -I -m unittest discover docs/specs/tools` must pass: unit tests
  for decay, weighted median, confidence edge cases (no reports, one scout,
  operator only), exclusion with unknown values, trend null cases.
- `python -I docs/specs/tools/check_docs.py` must pass: every
  `(placeholder)` parameter appears in PARAMETERS.md; every `US-` id is
  unique; every intra-repo link resolves; every Mermaid block has a known
  diagram type; every golden file has `is_synthetic: 1`; every synthetic file
  is listed in `docs/synthetic/specs.md`.
- Manually: paste each Mermaid block into GitHub preview once.

## 8. Definition of done
- [ ] All files in OUTLINE §2 exist and have the header.
- [ ] SCORING.md formulas match PRD §5 (or PRD updated with the reason).
- [ ] PARAMETERS.md has every placeholder, with a machine-readable JSON block.
- [ ] Golden vectors G1–G8 exist, pass `check_golden.py`, and cover: normal,
      stale, single scout, operator only, disputed/flagged, missing dancing,
      exclusion, trend rising/falling.
- [ ] All three checkers pass; outputs pasted in `docs/workstreams/specs.md`.
- [ ] `docs/synthetic/specs.md` lists every synthetic file.
- [ ] Contract change requests consolidated in `docs/workstreams/specs.md`.
- [ ] Team docs drafted; GOOD_FIRST_PRS.md has ≥ 1 PR per team member.
- [ ] Committed on `nightlife/specs`, pushed with
      `git push -u origin nightlife/specs`. No PR opened.
- [ ] Master session notified with a 5-line summary if `send_message` exists.
