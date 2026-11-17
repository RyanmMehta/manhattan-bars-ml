# Pilot metrics and offline evaluation

Purpose: success metrics for the (synthetic, then real) pilot and the offline evaluation protocol on live-sim data.
Status: agreed definitions; targets are placeholders.
Last updated: 2026-11-17

All results on live-sim data are **synthetic**: they test the pipeline, not real-world value.
Every chart or table built from them must say "synthetic".

## 1. Metrics
| Metric | Definition | Target (placeholder) |
|---|---|---|
| Coverage | share of 35 launch venues with `confidence ≥ 0.40`, sampled every 15 min, Fri/Sat 22:00–01:00 | ≥ 60% |
| Freshness | median `freshness_minutes` over covered venues, same samples | ≤ 30 min |
| State accuracy | MAE of state `crowd` vs `syn_true_state.crowd_true` (same venue, nearest 15-min slot) | ≤ 0.6 |
| Rec quality | Hit@3: truth-best venue under the user's limits is in our top 3 | ≥ 0.6 and ≥ +0.15 over popularity |
| Ranking | NDCG@5 with gain = truth match (match formula on `syn_true_state`) | report |
| Limit safety | share of top-3 recs that truly break a hard limit (truth cover/line) | ≤ 5% |
| Visit rate | `Σ syn_feedback.visited / count(syn_feedback)` | ≥ 30% |
| Satisfaction | share of visited feedback with `rating ≥ 4` | ≥ 70% |
| Scout retention | 1 − churn; churn = no report in 21 days; per weekly cohort at 4 weeks | ≥ 40% |
| Time to decide | onboarding → pick tapped (real users only) | ≤ 3 min median |
| Operator adoption | claimed launch venues (real pilot) | ≥ 5 of 35 |

## 2. Metric pseudo-SQL (over `data/live_sim.db`)
```sql
-- Coverage / freshness: states from recs at each sample time t
-- (ml-recs harness writes eval_states(venue_id, t, confidence, freshness_minutes, crowd))
SELECT t, AVG(confidence >= 0.40) AS coverage FROM eval_states GROUP BY t;
-- Freshness: median(freshness_minutes) WHERE confidence >= 0.40, per t, then median over t

-- State accuracy
SELECT AVG(ABS(s.crowd - ts.crowd_true)) AS crowd_mae
FROM eval_states s JOIN syn_true_state ts
  ON ts.venue_id = s.venue_id AND ts.ts = s.t_slot   -- t floored to 15 min
WHERE s.crowd IS NOT NULL;

-- Visit rate / satisfaction
SELECT AVG(visited) AS visit_rate,
       AVG(CASE WHEN visited = 1 THEN rating >= 4 END) AS satisfaction
FROM syn_feedback;

-- Scout churn (label for coursework): last report + 21 days < window end
SELECT s.scout_id,
       (julianday('2026-11-14') - julianday(MAX(r.ts))) > 21 AS churned
FROM syn_scouts s LEFT JOIN syn_scout_reports r ON r.scout_id = s.scout_id
GROUP BY s.scout_id;
```

## 3. Offline protocol
1. Data: `python -I -m simulator --seed 42 --out data/live_sim.db` — 36 Thu–Sat nights,
   Thu Aug 27 → Sat Nov 14 2026, 20:00–03:00 ET.
2. Split: tune on nights before Nov 13; **test = Nov 13–14** (DEMO_NOW is in test). No tuning on test.
3. Sampling: each test night, every 15 min 21:00–02:00, 50 users from `syn_users` request recs.
4. Baselines: random; distance-only; popularity (venue × hour mean crowd on training nights); ours.
5. Report Hit@3, NDCG@5, limit safety, coverage, freshness, crowd MAE with 95% bootstrap CIs
   over (user, time) samples (1,000 resamples, seed 42).
6. Ablations: no decay; no reputation weighting; no outlier flagging; gamer + shill share at
   live-sim default and at 25%. Expectation: reputation + flagging keep crowd MAE within +0.2 of
   the clean run at 10% gaming.
7. Sensitivity: `H_crowd_min` 15/30/60; `conf_k` 1.0/1.5/2.5.
8. Leakage guard: replayed reports use `syn_scout_reputation_history` at the report date; truth
   tables are used only for scoring the evaluation, never as features or app inputs.

## 4. Results table template (fill from ml-recs harness; label synthetic)
| Method | Hit@3 | NDCG@5 | Limit safety | Coverage | Freshness | Crowd MAE |
|---|---|---|---|---|---|---|
| random | | | | | | |
| distance-only | | | | | | |
| popularity | | | | | | |
| ours | | | | | | |
| ours, no reputation | | | | | | |
| ours, 25% gamers | | | | | | |

## 5. Owners
Definitions: specs. Harness and numbers: ml-recs. Dashboards: tableau. Churn model: coursework.
