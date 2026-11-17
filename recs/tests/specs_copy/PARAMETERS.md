# PARAMETERS — every tunable constant in one place

Purpose: single source for scoring, trust and UI constants used by ml-recs, backend and frontend.
Status: agreed (canonical per Contracts v2 §A; values are placeholders until pilot data).
Last updated: 2026-11-17

Every value below is a **(placeholder)**: a first guess, not a finding. Other docs refer to
the name (e.g. `H_crowd_min`), not the number. Tools parse the JSON block at the bottom
(first ` ```json ` block in this file). If you change a value: edit the table **and** the JSON,
run `python -I docs/specs/tools/check_golden.py --regen`, review the diff, commit, tell master.

## Freshness and eligibility
| Name | Value | Unit | Used in | Rationale | How to tune |
|---|---|---|---|---|---|
| `H_crowd_min` | 30 | min | SCORING §2 (crowd, dancing, line) | energy changes fast | sensitivity 15/30/60 on live-sim training nights |
| `H_scout_cover_genre_min` | 60 | min | SCORING §2 (scout cover, music_genre) | changes a few times a night | same |
| `H_operator_min` | 120 | min | SCORING §2 (operator cover/genres/dj; offers without expiry) | posted on purpose, event-scoped | compare to `syn_true_state.cover_usd_true` |
| `cutoff_age_min` | 180 | min | SCORING §1 | 6 half-lives; older inputs are noise | keep ≥ 4·`H_crowd_min` |
| `future_skew_min` | 2 | min | SCORING §1 | phone clock skew | — |

## Weighting
| Name | Value | Unit | Used in | Rationale | How to tune |
|---|---|---|---|---|---|
| `rep_base` | 0.25 | – | `w_rep = rep_base + rep_slope·r` | a 0-rep scout still counts a little | gaming ablation (pilot-metrics §3) |
| `rep_slope` | 0.75 | – | same | a 1.0 scout counts 4× a 0.0 scout | same |
| `rep_new_scout` | 0.5 | – | default `r` | neutral start | — |
| `w_unverified` | 0.6 | – | `w_ver` when `verified_presence=0` | GPS not confirmed | MAE by verified vs not |
| `w_disputed` | 0.5 | – | `w_status` | contested until resolved | — |
| `w_operator` | 0.8 | – | `w_src` for operator updates | self-interest discount | cover MAE |
| `min_field_weight` | 0.30 | – | a field with total weight below this is `null` | too thin to state | coverage vs MAE trade-off |
| `genre_share_min` | 0.30 | – | genre vote inclusion | drop one-off genre calls | — |

## Vibe and confidence
| Name | Value | Unit | Used in | Rationale | How to tune |
|---|---|---|---|---|---|
| `vibe_w_crowd` | 0.50 | – | SCORING §4 | crowd is the anchor | research interviews |
| `vibe_w_dance` | 0.35 | – | SCORING §4 | dancing = energy | same |
| `vibe_w_line` | 0.15 | – | SCORING §4 | line = demand | same |
| `line_cap_min` | 30 | min | `line_n` | lines over 30 min all mean "packed" | — |
| `conf_k` | 1.5 | weight | `support = 1 − exp(−W/k)` | ~2 fresh good reports → 0.6 support | sensitivity 1.0/1.5/2.5 |
| `agree_sd_scale` | 1.5 | crowd pts | `agree` | sd of 1.5 = total disagreement | — |
| `agree_penalty` | 0.5 | – | `agree` | disagreement at most halves conf | — |
| `diverse_single_scout` | 0.6 | – | `diverse` | one person can be wrong | — |
| `operator_conf_cap` | 0.25 | – | operator-only confidence | operators can't vouch for crowd | — |
| `display_show_min` | 0.40 | conf | display band "show" | | user test |
| `display_low_min` | 0.20 | conf | display band "low" | | user test |
| `stale_tag_min` | 60 | min | UI "stale" tag | §J | — |
| `vibe_band_lively_min` | 35 | vibe | "Lively" from 35 | §J | — |
| `vibe_band_packed_min` | 65 | vibe | "Packed" from 65 | §J | — |

## Trend
| Name | Value | Unit | Used in | Rationale | How to tune |
|---|---|---|---|---|---|
| `trend_recent_min` | 30 | min | recent window `[now−30, now]` | | — |
| `trend_prior_min` | 90 | min | prior window `(now−90, now−30)` | | — |
| `trend_min_weight` | 0.5 | weight | either window below → `null` | | — |
| `trend_delta` | 0.4 | crowd pts | rising/falling threshold | | — |

## Match and ranking
| Name | Value | Unit | Used in | Rationale | How to tune |
|---|---|---|---|---|---|
| `match_w_genre` | 0.25 | – | SCORING §7 | music is the top stated need | interviews |
| `match_w_dancing` | 0.20 | – | SCORING §7 | | |
| `match_w_crowd` | 0.15 | – | SCORING §7 | | |
| `match_w_line` | 0.10 | – | SCORING §7 | | |
| `match_w_cover` | 0.10 | – | SCORING §7 | | |
| `match_w_distance` | 0.15 | – | SCORING §7 | | |
| `match_w_group` | 0.05 | – | SCORING §7 | | |
| `unknown_component` | 0.4 | – | score for an unknown component | below neutral: confirmed info beats none | — |
| `static_genre_score` | 0.6 | – | genre overlap only via venue attributes | | — |
| `group_capacity_per_person` | 10 | people | `min(1, capacity/(10·group_size))` | | — |
| `rank_conf_base` | 0.75 | – | `rank_score = match·(0.75 + 0.25·conf)` | | NDCG@5 |
| `rank_conf_slope` | 0.25 | – | same | | |
| `energy_fit_min` | 0.5 | – | SCORING §9 energy penalty: applies when fit < this | quiet venue must not top a busy-dancing request (Contracts c3fd169) | NDCG@5 |
| `energy_penalty_base` | 0.5 | – | rank_score × (0.5 + fit) | fit 0 halves rank_score | NDCG@5 |
| `max_reasons` | 3 | – | reasons list length | | — |
| `reason_min_component` | 0.6 | – | a component must score ≥ this to be a reason | | — |

## Trust, rewards, bounties
| Name | Value | Unit | Used in | Rationale |
|---|---|---|---|---|
| `presence_radius_m` | 150 | m | `verified_presence` | v2 §A |
| `rate_venue_window_min` | 20 | min | 1 report / venue / scout | |
| `rate_hour_max` | 6 | reports | per scout per hour | |
| `consensus_window_min` | 20 | min | ±window for consensus/outlier | |
| `consensus_min_others` | 2 | reports | consensus needs ≥ 2 other scouts | |
| `rep_lr` | 0.05 | – | reputation step | |
| `rep_target_agreement` | 0.7 | – | agreement neutral point | |
| `rep_verified_bonus` | 0.005 | – | per verified consensus report | |
| `rep_dispute_upheld` | -0.10 | – | penalty | |
| `rep_min` | 0.05 | – | clip | |
| `rep_max` | 0.98 | – | clip | |
| `velocity_kmh_max` | 15 | km/h | flag implausible hops | |
| `outlier_min_others` | 3 | reports | outlier check needs ≥ 3 others | |
| `outlier_crowd_gap` | 2.5 | crowd pts | flag outlier | |
| `new_scout_reports` | 3 | reports | below this, `r` fixed at 0.5 | |
| `points_hold_min` | 30 | min | pending → accepted | |
| `dispute_autoreject_h` | 48 | h | | |
| `pts_accepted` | 10 | pts | | |
| `pts_verified` | 5 | pts | | |
| `pts_first_tonight` | 5 | pts | | |
| `pts_clawback_penalty` | -10 | pts | on top of clawback | |
| `level_regular` | 100 | pts | | |
| `level_insider` | 500 | pts | | |
| `level_legend` | 1500 | pts | | |
| `bounty_conf_max` | 0.30 | conf | create bounty below | |
| `bounty_base_pts` | 20 | pts | | |
| `bounty_step_pts` | 10 | pts | per 30 min of staleness, max 3 steps | |
| `bounty_null_fresh_pts` | 50 | pts | freshness null | |
| `bounty_ttl_min` | 60 | min | | |
| `bounty_max_open` | 8 | bounties | | |
| `bounty_agree_conflict` | 0.6 | – | reason "conflicting reports" below | |

## Routing and UI defaults
| Name | Value | Unit | Used in |
|---|---|---|---|
| `dwell_min` | 60 | min | plan_night |
| `walk_kmh` | 4.5 | km/h | plan_night |
| `walk_penalty_per_km` | 10 | rank pts | plan_night objective |
| `default_crowd_pref` | 3 | 1–5 | onboarding |
| `default_max_cover_usd` | 30 | USD | onboarding |
| `default_max_line_minutes` | 20 | min | onboarding |
| `default_max_distance_km` | 1.5 | km | onboarding |
| `default_group_size` | 2 | people | onboarding |
| `default_lat` | 40.7185 | deg | Delancey/Essex fallback |
| `default_lon` | -73.9878 | deg | same |
| `earth_radius_km` | 6371.0 | km | haversine |

## Machine-readable block
```json
{
  "H_crowd_min": 30, "H_scout_cover_genre_min": 60, "H_operator_min": 120,
  "cutoff_age_min": 180, "future_skew_min": 2,
  "rep_base": 0.25, "rep_slope": 0.75, "rep_new_scout": 0.5,
  "w_unverified": 0.6, "w_disputed": 0.5, "w_operator": 0.8,
  "min_field_weight": 0.30, "genre_share_min": 0.30,
  "vibe_w_crowd": 0.50, "vibe_w_dance": 0.35, "vibe_w_line": 0.15, "line_cap_min": 30,
  "conf_k": 1.5, "agree_sd_scale": 1.5, "agree_penalty": 0.5, "diverse_single_scout": 0.6,
  "operator_conf_cap": 0.25,
  "display_show_min": 0.40, "display_low_min": 0.20, "stale_tag_min": 60,
  "vibe_band_lively_min": 35, "vibe_band_packed_min": 65,
  "trend_recent_min": 30, "trend_prior_min": 90, "trend_min_weight": 0.5, "trend_delta": 0.4,
  "match_w_genre": 0.25, "match_w_dancing": 0.20, "match_w_crowd": 0.15, "match_w_line": 0.10,
  "match_w_cover": 0.10, "match_w_distance": 0.15, "match_w_group": 0.05,
  "unknown_component": 0.4, "static_genre_score": 0.6, "group_capacity_per_person": 10,
  "rank_conf_base": 0.75, "rank_conf_slope": 0.25,
  "energy_fit_min": 0.5, "energy_penalty_base": 0.5, "max_reasons": 3, "reason_min_component": 0.6,
  "presence_radius_m": 150, "rate_venue_window_min": 20, "rate_hour_max": 6,
  "consensus_window_min": 20, "consensus_min_others": 2,
  "rep_lr": 0.05, "rep_target_agreement": 0.7, "rep_verified_bonus": 0.005,
  "rep_dispute_upheld": -0.10, "rep_min": 0.05, "rep_max": 0.98,
  "velocity_kmh_max": 15, "outlier_min_others": 3, "outlier_crowd_gap": 2.5, "new_scout_reports": 3,
  "points_hold_min": 30, "dispute_autoreject_h": 48,
  "pts_accepted": 10, "pts_verified": 5, "pts_first_tonight": 5, "pts_clawback_penalty": -10,
  "level_regular": 100, "level_insider": 500, "level_legend": 1500,
  "bounty_conf_max": 0.30, "bounty_base_pts": 20, "bounty_step_pts": 10, "bounty_null_fresh_pts": 50,
  "bounty_ttl_min": 60, "bounty_max_open": 8, "bounty_agree_conflict": 0.6,
  "dwell_min": 60, "walk_kmh": 4.5, "walk_penalty_per_km": 10,
  "default_crowd_pref": 3, "default_max_cover_usd": 30, "default_max_line_minutes": 20,
  "default_max_distance_km": 1.5, "default_group_size": 2,
  "default_lat": 40.7185, "default_lon": -73.9878, "earth_radius_km": 6371.0
}
```
