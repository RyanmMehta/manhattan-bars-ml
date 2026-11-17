# Survey: picking a bar tonight (≤ 5 minutes)

17 questions (Q9 is one grid with 8 rows, a–h). Schema: `codebook.csv`
(`syn_survey_responses`). Each option below shows the label people see and
the stored value in `code`.

Distribution: NYU classmates and friends, via class and group chats
(convenience sample). Results are directional only, not representative of
Manhattan bar-goers. No incentive (no budget). Target n ≥ 100 `[PLACEHOLDER]`.

## Intro and consent (shown first)

> This is a 5-minute survey for an NYU class project about how people pick a
> bar on a night out. It's anonymous: we don't ask for your name, email or
> phone, and we can't identify you. You can skip out at any time by closing
> the form. There's no payment or prize. Please only take it if you're 18 or
> older. By continuing, you agree that your anonymous answers can be used for
> the class project.

Form setting: do not collect email addresses; do not limit to one response
(that requires sign-in).

## About you and your nights out

**Q1. How old are you?** (single choice) → `age_band`

| Label | Stored |
|---|---|
| 18–20 | `18-20` |
| 21–24 | `21-24` |
| 25–29 | `25-29` |
| 30–34 | `30-34` |
| 35 or older | `35+` |

**Q2. Are you currently a student?** (single choice) → `student`

| Label | Stored |
|---|---|
| Yes | `1` |
| No | `0` |

**Q3. In the last 30 days, how many nights did you go out to a bar or club?**
(number, 0–30) → `nights_out_per_month`

**Q4. How many people (including you) are usually in your group?** (number,
1–12; "12 or more" = 12) → `typical_group_size`

**Q5. Who usually picks where the group goes?** (single choice) → `who_picks`

| Label | Stored |
|---|---|
| Me | `me` |
| A friend (usually the same person) | `friend` |
| It rotates | `rotates` |
| We vote / decide together | `group_vote` |

**Q6. Last time you went out, about how many minutes did the group spend
deciding where to go?** (number, 0–120; "over 2 hours" = 120) →
`decision_minutes`

**Q7. What did you use to decide last time? Check all that apply.**
(checkboxes) → `current_tools` (pipe-separated)

| Label | Stored |
|---|---|
| Google Maps | `google_maps` |
| Instagram | `instagram` |
| Group chat | `group_chat` |
| Partiful | `partiful` |
| Resy | `resy` |
| DICE | `dice` |
| Yelp | `yelp` |
| TikTok | `tiktok` |
| Nothing, we just went | `none` (only on its own) |

**Q8. In the last month, did your group go somewhere that turned out wrong
(too empty, too packed, long line, wrong music, surprise cover)?** (single
choice) → `bad_pick_last_month`

| Label | Stored |
|---|---|
| Yes | `1` |
| No | `0` |

## What matters when you pick

**Q9. How much does each of these matter when choosing a bar?** (grid, one
answer per row; required) → `importance_*`

Scale for every row:

| Label | Stored |
|---|---|
| 1 – Not at all | `1` |
| 2 | `2` |
| 3 | `3` |
| 4 | `4` |
| 5 – Deal-breaker | `5` |

| Row | Label | Column |
|---|---|---|
| Q9a | Music genre | `importance_genres` |
| Q9b | Whether people are dancing | `importance_want_dancing` |
| Q9c | How crowded it is | `importance_crowd_pref` |
| Q9d | Cover charge | `importance_max_cover_usd` |
| Q9e | Line / wait | `importance_max_line_minutes` |
| Q9f | Walking distance | `importance_max_distance_km` |
| Q9g | Drink prices | `importance_price` |
| Q9h | Knowing friends are there | `importance_friends_there` |

**Q10. Pick up to 3 genres you most want to hear.** (checkboxes, max 3) →
`favorite_genres` (pipe-separated)

| Label | Stored |
|---|---|
| Hip-hop | `hip-hop` |
| R&B | `r&b` |
| Afrobeats | `afrobeats` |
| Latin | `latin` |
| Reggaeton | `reggaeton` |
| House | `house` |
| Techno | `techno` |
| EDM | `edm` |
| Disco | `disco` |
| Pop | `pop` |
| Top 40 | `top-40` |
| Throwbacks | `throwbacks` |
| Indie | `indie` |
| Rock | `rock` |
| Punk | `punk` |
| Jazz | `jazz` |
| Soul / funk | `soul-funk` |

**Q10 (separate checkbox): ☐ No preference for music** → `genre_no_pref`
(`1` if ticked, else `0`). If ticked, `favorite_genres` must be empty.

**Q11. If an app told you how busy a bar is, how old could that info be
before you'd stop trusting it?** (single choice) → `freshness_tolerance_min`

| Label | Stored |
|---|---|
| 15 minutes | `15` |
| 30 minutes | `30` |
| 45 minutes | `45` |
| 1 hour | `60` |
| 1.5 hours | `90` |
| 2 hours | `120` |

**Q12. Which would make you trust a live report about a bar most?** (single
choice) → `trust_cue_pref`

| Label | Stored |
|---|---|
| Many people reported the same thing | `n_reports` |
| It was reported in the last few minutes | `recency` |
| It came from a verified reporter | `verified_scout` |
| It came from the venue itself | `venue_official` |

## The idea (concept shown before Q13)

Show this text on its own page/section, above Q13:

> **Imagine an app for picking a bar right now.** People already at bars,
> called Scouts, send a 10-second "vibe check": how crowded it is (1–5),
> whether people are dancing, the line in minutes, the cover, and the music.
> Bars can post official updates like cover, DJ or drink offers. For each bar
> the app shows a vibe score, how confident it is, and how fresh it is (like
> "12 min ago"). Your group sets what you want and it ranks nearby bars.
> Scouts earn points they can trade for perks.

**Q13. Would you use this on most weeks you go out?** (single choice) →
`would_use_weekly`

| Label | Stored |
|---|---|
| Yes | `1` |
| No | `0` |

**Q14. How likely are you to recommend this app to a friend?** (linear
scale 0–10; 0 = not at all likely, 10 = extremely likely) → `nps_concept`
(stored `0`…`10`)

**Q15. Would you send a 10-second vibe check from a bar you're at in exchange
for perks?** (single choice) → `would_scout`

| Label | Stored |
|---|---|
| No | `0` |
| Maybe | `1` |
| Yes | `2` |
| I already do something like this (stories, texting friends) | `3` |

**Q16. If yes or maybe: how many vibe checks would you send on a typical
night out?** (number, 0–10; enter 0 if no) → `reports_per_night_if_scout`

**Q17. Which reward would make sending vibe checks worth it?** (single
choice) → `points_value_pref`

| Label | Stored |
|---|---|
| A free drink | `free_drink` |
| Skip the line | `skip_line` |
| Cover waived | `cover_waiver` |
| Status / badge (top Scout) | `status` |

End page: "Thanks! That's it. Your answers are anonymous."

## Column mapping

| Q | Column | Type |
|---|---|---|
| — | `response_id` | id, `srv-r-####` (added at export) |
| — | `submitted_at` | datetime, ISO 8601 with New York offset (from form timestamp) |
| Q1 | `age_band` | enum |
| Q2 | `student` | int 0..1 |
| Q3 | `nights_out_per_month` | int 0..30 |
| Q4 | `typical_group_size` | int 1..12 |
| Q5 | `who_picks` | enum |
| Q6 | `decision_minutes` | int 0..120 |
| Q7 | `current_tools` | multi_enum |
| Q8 | `bad_pick_last_month` | int 0..1 |
| Q9a | `importance_genres` | int 1..5 |
| Q9b | `importance_want_dancing` | int 1..5 |
| Q9c | `importance_crowd_pref` | int 1..5 |
| Q9d | `importance_max_cover_usd` | int 1..5 |
| Q9e | `importance_max_line_minutes` | int 1..5 |
| Q9f | `importance_max_distance_km` | int 1..5 |
| Q9g | `importance_price` | int 1..5 |
| Q9h | `importance_friends_there` | int 1..5 |
| Q10 | `favorite_genres` | multi_enum (may be empty) |
| Q10 | `genre_no_pref` | int 0..1 |
| Q11 | `freshness_tolerance_min` | int 15/30/45/60/90/120 |
| Q12 | `trust_cue_pref` | enum |
| Q13 | `would_use_weekly` | int 0..1 |
| Q14 | `nps_concept` | int 0..10 |
| Q15 | `would_scout` | int 0..3 |
| Q16 | `reports_per_night_if_scout` | int 0..10 |
| Q17 | `points_value_pref` | enum |
| — | `is_synthetic` | always `0` for real rows |

## Building it in Google Forms

1. New form, title "Picking a bar tonight". Settings → Responses: turn off
   "Collect email addresses" and "Limit to 1 response".
2. Put the intro/consent text in the form description.
3. Section 1 (Q1–Q8), Section 2 (Q9–Q12), Section 3 (concept text as the
   section description, then Q13–Q17).
4. Question types: Q1, Q2, Q5, Q8, Q11, Q12, Q13, Q15, Q17 = Multiple choice;
   Q3, Q4, Q6, Q16 = Short answer with response validation "Number, between"
   (0–30, 1–12, 0–120, 0–10); Q7 = Checkboxes; Q9 = Multiple choice grid
   (rows a–h, columns 1–5, "Require a response in each row"); Q10 =
   Checkboxes with validation "Select at most 3", plus a separate Checkboxes
   question with one option "No preference for music"; Q14 = Linear scale
   0–10.
5. Use the labels above exactly, so recoding is a simple lookup.
6. Make every question required except Q10 genres, the Q10 no-preference
   box and Q16 (blank Q16 is recoded to 0).
7. Preview, time yourself (target under 5 minutes), then share the link only
   in class and friend chats.

## Export → codebook mapping

1. Responses → Download (.csv). Keep the raw export off-repo.
2. Rename columns to the codebook names (table above). The Q9 grid exports as
   8 columns ("… [Music genre]" etc.); map each to its `importance_*`
   column. Timestamp → `submitted_at`, converted to ISO 8601 with the New York
   offset (e.g. `2026-11-20T21:14:00-05:00`).
3. Recode labels to stored values using the tables above (e.g. "It rotates" →
   `rotates`, "1 hour" → `60`, "Yes" → `1`).
4. Checkbox answers: Forms joins options with ", ". Recode each option and
   join with `|` (e.g. `google_maps|group_chat`). If "Nothing, we just went"
   is ticked with anything else, keep only the other tools.
5. Q10: if "No preference" is ticked, set `genre_no_pref=1` and clear
   `favorite_genres`; else `genre_no_pref=0`. If more than 3 genres appear,
   keep the first 3.
6. Q16 blank → `0`; Q4 "12 or more" → `12`.
7. Add `response_id` = `srv-r-0001`, `srv-r-0002`, … in submission order, and
   `is_synthetic` = `0` on every row. Drop any column not in the codebook.
8. Order columns as in `codebook.csv` and save as
   `research/survey/responses.csv`.
9. Run `python -I research/validate.py --real` and fix any errors it lists.
