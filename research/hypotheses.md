# Research hypotheses (H1–H12)

Each hypothesis names the metric that tests it and a pass threshold. **All
thresholds are `[PLACEHOLDER]`** guesses set before any real data. Survey Q-numbers
refer to `research/survey/questions.md`; guide sections refer to
`research/interview_guide/`. `summary_tables.csv` metric names are in `code`.

| ID | Hypothesis | Evidence (survey Q / interview) | Metric | Pass if `[PLACEHOLDER]` |
|---|---|---|---|---|
| H1 | Picking a bar that turns out wrong (empty, packed, long line, wrong music, surprise cover) is common | Q8; consumer core 1–3 | `pct_bad_pick_last_month` | ≥ 60% |
| H2 | Deciding takes long enough to hurt (group-chat back-and-forth) | Q6; consumer core 4 | `median_decision_minutes` | ≥ 15 min |
| H3 | People stitch together ≥ 2 tools and none gives tonight's state | Q7; consumer core 5–6, operator core 3 | `pct_use_2plus_tools` | ≥ 70% |
| H4 | Live info goes stale fast: most won't trust info older than ~60 min | Q11; consumer core 7, scout core 5 | `median_freshness_tolerance_min`, `pct_freshness_tolerance_le_60` | median ≤ 60 and ≥ 60% at ≤ 60 |
| H5 | Line, music and crowd matter more than distance and price | Q9a–h; consumer core 8 | `rank_importance_*` | line, genres, crowd in top 4 |
| H6 | Recency and number of reports earn more trust than the venue's own post | Q12; consumer concept 2 | `pct_trust_cue_pref_*` | recency + n_reports ≥ 50%; venue_official ≤ 20% |
| H7 | Enough people would send a 10-second vibe check | Q15–16; scout core 1–4 | `pct_scout_ge1_report_per_night` | ≥ 20% |
| H8 | Tangible perks (skip line, free drink, cover waiver) motivate more than status | Q17; scout concept 1 | `pct_points_value_pref_status` | status ≤ 25% |
| H9 | One person usually picks for the group (so we design for the planner) | Q5; consumer warm-up 3 | `pct_planner_is_one_person` | ≥ 60% |
| H10 | Operators would pay for demand analytics | operator concept 3–4 | `operators_wtp_ge_49` | ≥ 2 of 5 operators at ≥ $49/mo |
| H11 | Operators will post cover/DJ/offer updates at least weekly | operator core 4, concept 2 | count of operators saying "weekly or more" | ≥ 3 of 5 |
| H12 | The concept is wanted on a regular basis | Q13–14; all concept tests | `pct_would_use_weekly`, `nps_concept`, `mean_concept_reaction` | ≥ 40% weekly; reaction ≥ 3.5 |

Kill criteria: if H1 **and** H4 both fail on real data (n ≥ 100 survey), the
"right now" premise is weak and positioning should move to planning ahead
(events/reservations) instead of live state. If H7 fails, Scout supply must come
from venues/staff, not patrons.
