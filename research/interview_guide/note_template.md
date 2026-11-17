# Interview note template

Fill one copy per interview right after the call, from your off-repo notes.
Then add one row to `research/interviews/interviews.csv` and one row per quote
to `research/interviews/quotes.csv`. Field names and allowed values match
`research/survey/codebook.csv` (`syn_interviews`, `syn_interview_quotes`);
the real CSVs use the same columns in the same order.

Rules
- No names, emails, phone numbers or social handles anywhere: not in fields,
  not in quotes. Replace any name in a quote with a role, e.g. "[my friend]".
- Venues are public and may be named, but record them only by `license_id`
  from `data/launch_venues.csv` in `venue_mentions`. Venues not on the launch
  list are left out of `venue_mentions` (you may write the venue type in a
  quote, e.g. "[a bar on Orchard]").
- Raw notes and any audio stay off-repo (personal drive). Only this
  template's fields go into the repo.
- Real IDs: interviews `int-r-001`, `int-r-002`, …; quotes `q-r-0001`,
  `q-r-0002`, … (never reuse an ID). `is_synthetic` is always `0`.
- Multi-value fields are pipe-separated, e.g. `google_maps|instagram`.
- "Empty allowed" fields may be left blank (blank cell in the CSV). All other
  fields must be filled.
- After adding rows: `python -I research/validate.py --real`.

## Interview fields (`research/interviews/interviews.csv`)

| Field | Allowed values | Empty allowed | Value |
|---|---|---|---|
| `interview_id` | `int-r-###` (e.g. int-r-001) | no | |
| `segment` | consumer; scout; operator | no | |
| `date` | YYYY-MM-DD | no | |
| `age_band` | 18-20; 21-24; 25-29; 30-34; 35+; na | no | |
| `nights_out_per_month` | integer 0..30 (operators: nights they work the floor) | no | |
| `typical_group_size` | integer 1..12 | yes (operators) | |
| `neighborhoods` | les; east_village; soho; williamsburg; west_village; chinatown; bushwick; midtown (pipe-separated) | no | |
| `current_tools` | google_maps; instagram; group_chat; partiful; resy; dice; yelp; tiktok; none (pipe-separated; `none` alone if nothing; operators: tools they post to) | no | |
| `bad_pick_last_month` | 0; 1 | yes (operators) | |
| `favorite_genres` | hip-hop; r&b; afrobeats; latin; reggaeton; house; techno; edm; disco; pop; top-40; throwbacks; indie; rock; punk; jazz; soul-funk (pipe-separated; operators: genres they book) | yes | |
| `top_factor_1` | genres; want_dancing; crowd_pref; max_cover_usd; max_line_minutes; max_distance_km; price; friends_there | yes (operators) | |
| `top_factor_2` | same as top_factor_1 | yes | |
| `top_factor_3` | same as top_factor_1 | yes | |
| `freshness_tolerance_min` | 15; 30; 45; 60; 90; 120 (round to nearest) | yes (operators) | |
| `would_scout` | 0 = no; 1 = maybe; 2 = yes; 3 = already does something like this | yes (operators) | |
| `scout_motivator` | points; perks; status; helping; none | yes (operators) | |
| `operator_role` | owner; gm; bar_manager; promoter | yes (non-operators) | |
| `operator_wtp_usd_month` | integer 0..500 | yes (non-operators) | |
| `operator_wants` | claimed_profile; post_offers; dj_updates; demand_analytics; scout_reports_on_my_venue; competitor_benchmark (pipe-separated) | yes (non-operators) | |
| `venue_mentions` | launch venue `license_id`s from `data/launch_venues.csv` (pipe-separated) | yes | |
| `concept_reaction` | integer 1..5 (1 negative, 5 very positive) | no | |
| `is_synthetic` | 0 | no | 0 |

## Quotes (`research/interviews/quotes.csv`)

Add 2–5 short, verbatim (or close) quotes per interview. One row each.

| `quote_id` | `interview_id` | `hypothesis_id` | `theme` | `sentiment` | `text` | `is_synthetic` |
|---|---|---|---|---|---|---|
| q-r-#### | int-r-### | H1…H12 | pain; tools; trust; scouting; pricing; other | -1; 0; 1 | anonymized quote | 0 |
| | | | | | | 0 |
| | | | | | | 0 |
| | | | | | | 0 |

Field notes
- `hypothesis_id`: one of H1, H2, H3, H4, H5, H6, H7, H8, H9, H10, H11, H12
  (`research/hypotheses.md`). If a quote bears on two, pick the stronger one
  or add a second row with a new `quote_id`.
- `sentiment`: -1 negative, 0 neutral, 1 positive toward the concept or the
  hypothesis.
- `text`: no names, contacts or handles. Do not start real quotes with
  `[SYNTHETIC]`.
- Things with no column (decision minutes, posting frequency, what they'd
  drop first) go into quotes, tagged with the matching hypothesis.

## CSV headers (copy exactly)

interviews.csv:

```
interview_id,segment,date,age_band,nights_out_per_month,typical_group_size,neighborhoods,current_tools,bad_pick_last_month,favorite_genres,top_factor_1,top_factor_2,top_factor_3,freshness_tolerance_min,would_scout,scout_motivator,operator_role,operator_wtp_usd_month,operator_wants,venue_mentions,concept_reaction,is_synthetic
```

quotes.csv:

```
quote_id,interview_id,hypothesis_id,theme,sentiment,text,is_synthetic
```
