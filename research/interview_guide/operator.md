# Operator interview guide (25 min)

Who: owner, GM, bar manager or promoter at a bar in the Lower East Side.
Goal: learn how they tell people about tonight (cover, DJ, offers), how often
they post, and whether they would pay for demand analytics. Past behavior
first; the concept and pricing come last.

Rules for the interviewer
- Walk-ins happen on an early weeknight, 5–7 pm, before service. If they're
  busy, ask for a better time; don't push.
- Ask about what they did last week, not what they would do.
- No names of staff, phone numbers or handles in notes. The venue itself may
  be named, recorded by its `license_id` from `data/launch_venues.csv`.
- Notes stay off-repo; fill `note_template.md` right after.

| Section | Time |
|---|---|
| Screener | 1–2 min (at the door or before scheduling) |
| Consent | 1 min |
| Warm-up | 3 min |
| Core questions | 10 min |
| Concept test | 8 min |
| Wrap-up | 2 min |
| Total | about 25 min |

## Screener (1–2 min)

1. What's your role here? (Qualifies: owner, GM, bar manager, or promoter who
   books nights here.)
2. Is this venue in the Lower East Side? (Check it against
   `data/launch_venues.csv`; note its `license_id`. Non-launch LES bars still
   qualify; leave `venue_mentions` empty for them.)
3. Are you involved in deciding cover, DJ/music, or promotions? (Must be yes.)

Qualifies: owner / GM / bar manager / promoter at an LES bar who has a say in
cover, music or promotions.

## Consent script (1 min, verbal)

> Thanks for the time. I'm an NYU student doing a class project on how people
> pick bars in the Lower East Side and how venues get the word out. It takes
> about 25 minutes. I'll take notes but won't record your name or contact
> details; notes are anonymized with an ID number. I may note the venue name,
> since it's public. You can skip any question or stop at any time. There's no
> payment for this; we don't have a budget, and we're not selling anything. Is
> it OK to go ahead?

Proceed only on a clear yes. Write "consent: verbal yes" in your off-repo notes.

## Warm-up (3 min)

W1. What's your role, and how long have you been here?
W2. In the last 30 days, how many nights did you work the floor?
W3. What kind of night is a good night here? What music do you book?

## Core questions (10 min)

1. Tell me about last Saturday. How busy was it, and when did it pick up?
   `[H1] [H5]`
   - Probe: Was there a line? How long? Did people leave the line?
2. Think of a recent night that was slower than you wanted. What did you do
   about it, during the night? `[H1] [H11]`
   - Probe: Did you post anything, change cover, text a promoter?
3. Where do you tell people about tonight: cover, DJ, specials? Show me the
   last post. `[H3]`
   - Probe: Instagram, Google Maps, Resy, DICE, Partiful, Yelp, TikTok, a
     promoter's group chat?
   - Probe: What can't you say on those that you'd want to?
4. In the last month, how often did you post updates about cover, DJ or
   offers? Who does it, and how long does it take? `[H11]`
   - Probe: Same day, or planned ahead? What stops you from posting more?
5. How do you know what customers say about your bar right now, tonight?
   `[H6] [H10]`
   - Probe: Have you seen wrong info about your bar online? What happened?

## Concept test (8 min)

Default: read the description aloud. If frontend mockup PNGs of the venue
dashboard exist, show them after reading.

> Picture an app that helps groups pick a bar right now. People at bars,
> called Scouts, send a 10-second vibe check: crowd 1 to 5, dancing, line
> length, cover and music. Venues can claim their profile and post official
> updates like cover, DJ and offers. The app shows each bar's vibe score, how
> confident it is and how fresh it is, like "12 min ago", and ranks bars
> against what a group wants. A venue dashboard shows demand: how many groups
> looked at you tonight, what they wanted, and how you compare.

Scenario: "It's Saturday, Nov 14, 11:30 pm. A group of 4 is on Ludlow St
deciding where to go. Your bar shows up second on their list."

1. First reaction: what would you want to change or check? How do you feel
   about it from 1 very negative to 5 very positive? `[H12] [H6]`
   - Probe: How do you feel about Scouts reporting on your bar? What if a
     report is wrong?
2. Thinking about how often you posted last month, how often would you post
   cover/DJ/offer updates here? What would make you skip it? `[H11]`
   - Probe: Weekly or more? Who on staff would do it?
3. Which of these would you actually use: a claimed profile, posting offers,
   DJ updates, demand analytics, Scout reports on your venue, a comparison
   with nearby bars? `[H10]`
   - Probe: Which one would you drop first?
4. What do you pay today for tools like this (POS add-ons, Resy, promoters,
   ads)? For the tools you picked, what's the most per month you'd pay before
   it's not worth it? `[H10]`
   - Probe: Would $49 a month be cheap, fair, or too much? Why?
   - Probe: Would you rather pay per redeemed offer?

## Wrap-up (2 min)

- "Anything I should have asked?"
- "Is there another manager or promoter nearby who might talk to us? Please
  pass on our message."
- Thank them. Remind them notes are anonymized.

## Which note-template field each section fills

| Section | Note-template fields |
|---|---|
| Screener | `segment` (= operator), `operator_role`, `venue_mentions` (their venue's `license_id`), `age_band` (= na if not asked or declined) |
| Warm-up W2–W3 | `nights_out_per_month` (nights on the floor), `favorite_genres` (genres they book), `neighborhoods` (= les) |
| Core 1–2 | quotes tagged H1/H5/H11 |
| Core 3 | `current_tools` (where they post) |
| Core 4 | quotes tagged H11 (posting frequency) |
| Core 5 | quotes tagged H6/H10 |
| Concept 1 | `concept_reaction` |
| Concept 2 | quotes tagged H11 ("weekly or more" or not) |
| Concept 3 | `operator_wants` |
| Concept 4 | `operator_wtp_usd_month` |
| Consumer-only fields | leave empty: `typical_group_size`, `bad_pick_last_month`, `top_factor_1..3`, `freshness_tolerance_min`, `would_scout`, `scout_motivator` |
| System | `interview_id`, `date`, `is_synthetic` (= 0) |
