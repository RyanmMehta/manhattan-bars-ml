# Research findings summary and hand-offs

As of **2026-11-17**: **0 real interviews and 0 real survey responses.** Findings
tagged `[SYNTHETIC]` come from placeholder data (`research/synthetic/`, seed 42,
n_survey = 300, n_interviews = 15). They show what the analysis will produce and
are **not evidence**. Their numbers mostly echo the `PRIORS` we set in
`research/gen_synthetic.py`. Findings tagged `[REAL desk]` come from sourced
desk research (`research/competitors.csv`). Re-run
`python -I research/analysis.py --source real` once real rows exist, and re-tag
each finding as `[REAL n=…]`.

| # | Finding | Tag | Source metric | Consumer → action |
|---|---|---|---|---|
| 1 | None of the 20 products we reviewed shows confidence or freshness on live venue info. That is our clearest differentiator. | `[REAL desk]` | competitive_matrix.md "Shows confidence" column | frontend: keep the freshness text ("12 min ago") and the confidence badge prominent on every card; integration: lead the pitch with it |
| 2 | Live-crowd apps exist (BarHopper, Rally, LinePal, Sense), but none matches group preferences. Rally is the closest model (venue pages can't override user reports). | `[REAL desk]` | competitors.csv c05, c18–c20 | specs/backend: keep "operators can dispute, not edit, Scout reports" (§G, `syn_disputes`) |
| 3 | 61% report a bad pick in the last month. This would pass H1 (≥ 60%) if real. | `[SYNTHETIC]` | `pct_bad_pick_last_month` = 60.67 | integration: slide shows the H1 threshold and says "to be measured" |
| 4 | Median freshness tolerance is 30 min, and 87% won't trust info older than 60 min. That is consistent with the 30-min half-life and the 60-min "stale" tag. | `[SYNTHETIC]` | `median_freshness_tolerance_min`, `pct_freshness_tolerance_le_60` | specs: keep half-life 30 min and stale > 60 min (§A, §J) as placeholders; revisit with real Q11 |
| 5 | Factor importance rank: line > genres > crowd > cover > dancing > price > distance > friends there | `[SYNTHETIC]` | `rank_importance_*` | ml-recs: placeholder match weights in that order; frontend: put line, genre and crowd filters first |
| 6 | Recency (39%) and number of reports (26%) beat venue-official posts (14%) as trust cues | `[SYNTHETIC]` | `pct_trust_cue_pref_*` | frontend: badge copy "4 reports · 12 min ago" ahead of "Official"; specs: keep operator updates on a separate, longer half-life |
| 7 | 31% would send ≥ 1 vibe check per night. This would pass H7 (≥ 20%) if real. | `[SYNTHETIC]` | `pct_scout_ge1_report_per_night` | live-sim: Scout supply assumptions stay placeholders; replace with real Q15–16 |
| 8 | Free drink (35%) and skip the line (29%) motivate more than status (11%) | `[SYNTHETIC]` | `pct_points_value_pref_*` | frontend/backend: perk-first bounty copy ("skip the line at X") over leaderboard-first |
| 9 | 47% would use it weekly, but concept NPS is −51 (most answers fall in 0–6 under the priors) | `[SYNTHETIC]` | `pct_would_use_weekly`, `nps_concept` | coursework: `would_use_weekly` is a balanced binary label usable for a classifier demo |
| 10 | Only 1 of 4 synthetic operators would pay ≥ $49/mo (median $12.50), so H10 fails on placeholder data and the Pro price needs real testing | `[SYNTHETIC]` | `operators_wtp_ge_49`, `operator_median_wtp_usd_month` | backend: the owner dashboard is the test artifact for T2 in business_model.md |

## Hand-off table

| Workstream | What to take | File |
|---|---|---|
| specs | Freshness tolerance (finding 4), trust cues (6); both placeholders | `research/synthetic/summary_tables.csv` |
| ml-recs | Factor rank for default weights (5); label as placeholder in code with `# SYNTHETIC: research survey Q9` | same |
| frontend | Filter order (5), badge wording (1, 6), perk-first Scout copy (8); always show the "demo data" badge on research charts | `research/summary.md` |
| tableau | Voice-of-customer dashboard from `summary_tables.csv` (`metric, segment, value, n, is_synthetic`); the title must include "demo data"; competitor matrix and 2×2 from `competitors.csv` / `competitive_matrix.md` | `research/synthetic/`, `research/competitors.csv` |
| live-sim | Placeholder Scout supply rates (7) and motivators (8) | `summary_tables.csv` |
| coursework | `syn_survey_responses.csv` with binary target `would_use_weekly` (47% positive) | `research/synthetic/syn_survey_responses.csv` |
| backend | Operator wants and WTP (10); no API work needed | `research/synthetic/syn_interviews.csv` |
| integration | Slide content | `research/presentation_notes.md` |
