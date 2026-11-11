# OUTLINE — specs build plan

Planning draft, 2026-11-11. Read with `PRD.md` (what) and `RULES.md` (how).
Sizes: **S** ≤ 1 h, **M** 1–3 h, **L** 3–6 h (one person / one Claude session).
Target: specs done by **Nov 13** so ml-recs, backend and frontend can build to
it before the **Nov 17** integration.

## 1. Ordered tasks

### Phase A — scaffolding (Nov 11)
- [ ] A1 **S** Create `docs/specs/` tree (§2), file headers, `docs/workstreams/specs.md` stub, `docs/synthetic/specs.md` stub.
- [ ] A2 **M** `PARAMETERS.md`: every placeholder from PRD §5, §7, §10 in a table plus one fenced ` ```json ` block (`{"H_crowd_min": 30, ...}`) that tools parse.

### Phase B — core specs (Nov 11–12)
- [ ] B1 **M** `ARCHITECTURE.md`: Mermaid flowchart (PRD §4.1), component table, request sequence diagram (`sequenceDiagram` for `/api/recommend`), environments, env vars, stack + rationale, caching rule, `now=` replay semantics.
- [ ] B2 **L** `SCORING.md`: eligibility, decay, weighting, field estimates, vibe, confidence + display, trend, exclusions, match, ranking, reasons/missing templates, Run My Night objective. Each section: formula block, symbols, edge cases, link to golden vectors.
- [ ] B3 **M** `tools/reference_scoring.py`: stdlib test oracle implementing SCORING.md exactly (`compute_state(reports, updates, now)`, `match(prefs, state, venue)`); not imported by the app.
- [ ] B4 **M** Golden vectors G1–G8 in `golden_synthetic/` + `tools/check_golden.py`.
- [ ] B5 **M** `TRUST.md`: reputation update, points table, levels, anti-gaming checks (which layer enforces each), report status state machine (`stateDiagram-v2`), disputes, bounties.
- [ ] B6 **L** `REQUIREMENTS.md`: every user story from PRD §6 with acceptance criteria, mapped to screen (frontend) and endpoint (backend) in a traceability table; non-functional requirements.

### Phase C — evaluation and team (Nov 12–13)
- [ ] C1 **M** `EVALUATION.md`: metric definitions with SQL/pseudo-code over `syn_` tables, protocol (temporal split, baselines, ablations, sensitivity), results table template, "synthetic" caveat.
- [ ] C2 **S** `team/PULL_REQUEST_TEMPLATE.md`.
- [ ] C3 **S** `team/CONTRIBUTING.md`: branch naming, folder ownership, commit style, synthetic rule, how to run checks, review rules (1 approval, CI green).
- [ ] C4 **S** `team/GOOD_FIRST_PRS.md` (draft list in §8 below; assign once roster known).

### Phase D — checks and handoff (Nov 13)
- [ ] D1 **M** `tools/check_docs.py` + unit tests (`tools/test_reference_scoring.py`).
- [ ] D2 **S** Run all checks; paste output into `docs/workstreams/specs.md`.
- [ ] D3 **S** Consolidate Contract change requests (PRD §13) into `docs/workstreams/specs.md`.
- [ ] D4 **S** Commit, `git push -u origin nightlife/specs`, notify master.

Total ≈ 22–30 h of work, parallelisable B2‖B5‖B6.

## 2. File tree to create

```
docs/
├── specs/
│   ├── ARCHITECTURE.md
│   ├── REQUIREMENTS.md
│   ├── SCORING.md
│   ├── PARAMETERS.md
│   ├── TRUST.md
│   ├── EVALUATION.md
│   ├── golden_synthetic/
│   │   ├── G1_normal_four_scouts.json
│   │   ├── G2_stale_reports.json
│   │   ├── G3_single_scout.json
│   │   ├── G4_operator_only.json
│   │   ├── G5_match_contract_prefs.json
│   │   ├── G6_exclusion_known_vs_unknown.json
│   │   ├── G7_disputed_and_flagged.json
│   │   ├── G8_trend_rising_falling.json
│   │   └── personas_synthetic.json
│   ├── tools/
│   │   ├── reference_scoring.py
│   │   ├── check_golden.py
│   │   ├── check_docs.py
│   │   └── test_reference_scoring.py
│   └── team/
│       ├── PULL_REQUEST_TEMPLATE.md
│       ├── CONTRIBUTING.md
│       └── GOOD_FIRST_PRS.md
├── workstreams/specs.md
└── synthetic/specs.md
```

## 3. Interfaces

### Provided (consumers in brackets)
| Interface | Where | Consumer |
|---|---|---|
| Scoring formulas + parameters | `SCORING.md`, `PARAMETERS.md` JSON block | ml-recs (`recs.live_state`, `recs.scoring`, `recs.routing`) |
| Golden vectors | `golden_synthetic/G*.json` (format below) | ml-recs pytest, backend contract tests |
| Display thresholds, copy for reasons/missing/badges | `SCORING.md` §display, `REQUIREMENTS.md` | frontend |
| Write-time trust rules (rate limits, geofence, status, points, owner ban) | `TRUST.md` | backend |
| Gaming-scout behaviours and truth table request | `TRUST.md`, `EVALUATION.md`, CCR-1 | live-sim |
| Metric definitions | `EVALUATION.md` | ml-recs (harness), tableau |
| Team workflow docs | `team/` | integration (copies to `.github/`, root) |

Golden vector format:
```json
{
  "id": "G1", "description": "...", "is_synthetic": 1,
  "now": "2026-11-14T23:00:00-05:00",
  "scouts":  [{"scout_id": "syn_s1", "reputation": 0.8, "is_synthetic": 1}],
  "reports": [{"report_id": "syn_r1", "venue_id": "0370-24-138636", "scout_id": "syn_s1",
               "ts": "2026-11-14T22:55:00-05:00", "crowd": 4, "dancing": 2,
               "line_minutes": 10, "cover_usd": null, "music_genre": "hip-hop",
               "verified_presence": 1, "status": "accepted", "is_synthetic": 1}],
  "updates": [],
  "prefs": null, "venue": null,
  "expected": {"state": {"crowd": 3.8, "dancing": 1.5, "line_minutes": 10,
               "vibe_score": 65, "confidence": 0.67, "trend": null, "display": "show"},
               "recommendation": null}
}
```

### Consumed (all from `docs/CONTRACTS.md`)
- Schemas: `syn_scout_reports`, `syn_venue_updates`, `syn_scouts`, `syn_users`,
  `syn_venue_attributes`, `syn_feedback`, `syn_bounties`.
- Preferences object, Live Venue State, Recommendation result.
- Python interface `live_state.compute[_all]`, `scoring.recommend`,
  `routing.plan_night` — SCORING.md maps each formula to one of these.
- HTTP API table — REQUIREMENTS.md maps each story to an endpoint.
- `data/launch_venues.csv` (venue ids, lat/lon for distance in fixtures).
- Read-only: `venues`, `osm_venues.opening_hours` in `manhattan_bars.db`.

## 4. Synthetic datasets specs needs

| Dataset | Imitates | How generated | Real source that replaces it | Swap steps |
|---|---|---|---|---|
| `golden_synthetic/G1–G8.json` | small slices of tonight's scout reports, operator updates and scouts at real launch venues | hand-written inputs; `expected` computed by `reference_scoring.py` and hand-checked for G1, G5 (PRD §5.8, §5.10) | **Not replaced** — they are test fixtures. Optionally add a G9 built from a real anonymised night once a pilot exists | keep; if parameters change, re-run `check_golden.py --regen`, review diff, commit |
| `golden_synthetic/personas_synthetic.json` | 5 group personas' Preferences (dancer group, cocktail pair, budget crew, big group of 8, no-prefs) for stories and eval examples | hand-written from PRD §3; lat/lon near Delancey/Essex | research interview results (10–15 interviews) → persona prefs | replace values, keep ids, set `is_synthetic: 0`, update registry |
| Placeholder parameters (`PARAMETERS.md`) | tuned values (half-lives, weights, thresholds) | first guesses (PRD §5) | tuning on live-sim nights 1–4, then real pilot data | edit JSON block, regen goldens, notify ml-recs; log change with date |
| Evaluation targets (PRD §10.1) | pilot goals | first guesses | course feedback / real pilot baseline | edit EVALUATION.md table |

Each row goes into `docs/synthetic/specs.md` with the five CONTRACTS fields.

## 5. Golden vector coverage
| ID | Case | Key expectations |
|---|---|---|
| G1 | 4 scouts, fresh, agree | vibe 65, conf 0.67, display show |
| G2 | same as G1 but ages +120 min | lower support, conf < 0.2, display none, nothing past 180 min counts |
| G3 | 3 reports from 1 scout | diverse = 0.6 cap |
| G4 | operator update only (cover 20, hip-hop) | vibe null, conf ≤ 0.25, cover 20, genres from update |
| G5 | G1 + contract Preferences | match 83, rank 76, reasons and missing strings |
| G6 | cover 25 known vs cover unknown, max 20 | first excluded with reason; second not excluded, `missing` has cover |
| G7 | one disputed (0.5 weight), one flagged (0), one future-dated (ignored) | state equals hand-computed |
| G8 | crowd 2→4 and 4→2 across windows; and thin prior window | rising / falling / null |

## 6. Team workflow drafts

**PULL_REQUEST_TEMPLATE.md** sections: What & why · Workstream / folder ·
Linked story or task (US-… / OUTLINE id) · How tested (commands + output) ·
Synthetic data touched (registry updated? badge?) · Contract impact (none /
CCR id) · Screenshots (UI) · Checklist (owns only its folder, tests pass, no
secrets, docs updated).

**CONTRIBUTING.md**: setup (`python -m venv .venv`, `pip install -r
requirements.txt`; `npm ci` in `frontend/`); branches `nightlife/<ws>` for
workstreams, `fp/<handle>-<topic>` for first PRs off the integration branch;
small PRs (≤ 300 lines); conventional commit prefixes (`docs:`, `feat:`,
`fix:`, `test:`); 1 reviewer approval; never commit secrets or `.env`;
synthetic rule summary; where to ask questions.

## 7. Test plan
| Level | What | How |
|---|---|---|
| Unit | decay, weighted mean/median, sd, confidence edges, exclusions, trend | `python -I -m unittest discover docs/specs/tools` |
| Golden | G1–G8 expected outputs from reference oracle | `python -I docs/specs/tools/check_golden.py` |
| Docs lint | placeholders registered, unique US ids, links, Mermaid types, synthetic registry | `python -I docs/specs/tools/check_docs.py` |
| Cross-workstream (owned by ml-recs/backend, specified here) | `recs` reproduces goldens; `/api/recommend` with G5 inputs returns match 83 | ml-recs pytest loads `docs/specs/golden_synthetic/*.json`; backend contract test |
| Review | each spec read by its main consumer | ask ml-recs (SCORING), backend (TRUST), frontend (REQUIREMENTS) sessions via master |

## 8. Good first PRs (one per member; assign when roster known)
1. Copy `team/PULL_REQUEST_TEMPLATE.md` to `.github/pull_request_template.md` (integration).
2. Add a golden vector G9: "line troll" (one report says 60 min) to prove the weighted median (specs).
3. Add `opening_hours` coverage stats for the 35 launch venues to `docs/workstreams/specs.md` (specs, reads DB).
4. Frontend: "demo data" badge component + story (frontend).
5. Frontend: confidence display component implementing the 3-band rule (frontend).
6. Backend: `/api/health` + pytest (backend).
7. Backend: 429 rate-limit message copy and test (backend).
8. ml-recs: haversine util + tests using two launch venues (ml-recs).
9. Tableau: export `launch_venues` extract with complaint count labelled "complaint risk" (tableau).
10. Research: add 2 competitor rows to the competitive matrix (research).
11. README: add "Nightlife Autopilot" section linking docs/specs (integration).
Each is ≤ 1 h, touches one owned folder, has a test or visible output.

## 9. Demo script (specs' part of the Nov 17 class demo, ~2 min)
1. Show `ARCHITECTURE.md` diagram: public DB → reports/updates → Live Venue
   State → recommendations (20 s).
2. Open G1 and walk the worked example: 4 reports → decay weights → vibe 65,
   confidence 0.67 → "show" (40 s).
3. Same venue two hours later (G2): confidence drops, UI says "No fresh
   reports" and posts a bounty — honesty over guessing (20 s).
4. G6: unknown cover doesn't exclude, known $25 does; `missing` tells the user
   (20 s).
5. Evaluation table: ours vs popularity baseline on synthetic nights 5–6,
   clearly labelled synthetic; gaming-scout ablation (20 s).

## 10. Assumptions recorded
- Planning docs live in `docs/prd/specs/` (brief); build output in
  `docs/specs/` (CONTRACTS). See CCR-8.
- Team roster unknown; good first PRs listed by area, assigned later.
- Reference oracle is a test tool only; ml-recs owns production code.
