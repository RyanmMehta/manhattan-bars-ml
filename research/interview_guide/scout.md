# Scout interview guide (20 min)

Who: people who already share what a bar is like while they're there (stories,
texts to friends, reviews, posting in group chats), or who say they'd send a
vibe check. Goal: learn whether and how often they'd report, and what reward
makes it worth it. Past behavior first; the concept comes last.

Rules for the interviewer
- Ask about real recent nights ("the last time you posted from a bar…").
- Don't pitch points or perks before the concept section.
- Notes stay off-repo; fill `note_template.md` after the call. No names,
  contacts or handles, including Instagram or TikTok handles they mention.

| Section | Time |
|---|---|
| Screener | 2 min (before scheduling) |
| Consent | 1 min |
| Warm-up | 2 min |
| Core questions | 8–9 min |
| Concept test | 5–6 min |
| Wrap-up | 1–2 min |
| Total | about 20 min |

## Screener (2 min, before scheduling)

1. Are you 21 or older? (Must be yes.)
2. In the last 30 days, how many nights did you go out to a bar or club?
   (Qualifies: 3 or more.)
3. In the last 30 days, did you post a story, send a text, or leave a review
   about what a bar was like while you were there or right after?
   (Qualifies: yes. "Would, but haven't" can fill at most 1 of 3 slots.)
4. Do you work at a bar or for a venue? (If yes, use the operator guide.)

Qualifies: 21+, 3+ nights out in the last 30 days, has shared live bar info at
least once in the last 30 days, not nightlife industry.

## Consent script (1 min, verbal)

> Thanks for doing this. It's for an NYU class project about how people share
> what bars are like on a night out. It takes about 20 minutes. I'll take notes
> but won't record your name, phone number, or social handles; notes are
> anonymized with an ID number. You can skip any question or stop at any time.
> There's no payment or gift for this; we don't have a budget. Is it OK to go
> ahead?

Proceed only on a clear yes. Write "consent: verbal yes" in your off-repo notes.

## Warm-up (2 min)

W1. Roughly how many nights in the last 30 days did you go out?
W2. Where do you usually go out, and with how many people?

## Core questions (8–9 min)

1. Tell me about the last time you shared what a bar was like while you were
   there. What did you post or send, and to whom? `[H7]`
   - Probe: What made you do it at that moment?
   - Probe: How long did it take?
2. On that night, how many times did you post or text about where you were?
   `[H7]`
   - Probe: Was that a typical night? What about the night before that?
3. Think of a night you didn't share anything. What stopped you? `[H7]`
   - Probe: Phone battery, being with people, privacy, no one asked?
4. Has anyone ever asked you "what's it like there?" while you were out? What
   did you tell them, and what happened next? `[H7]`
   - Probe: Did they come? Did it change their plans?
5. When someone else sent you info about a bar, how old could it be before it
   was useless to you? Tell me about a time it was out of date. `[H4]`
   - Probe: 15 min, 30, an hour, two hours?

## Concept test (5–6 min)

Default: read the description aloud. If frontend mockup PNGs exist, show the
vibe-check screen and the points/perks screen after reading.

> Picture an app where people at a bar send a 10-second "vibe check": crowd
> level from 1 to 5, whether people are dancing, the line in minutes, the
> cover, and the music. Other people use those reports to pick a bar, with a
> freshness label like "12 min ago". People who send vibe checks, called
> Scouts, earn points they can trade for things like skipping the line, a free
> drink, or a cover waiver, or they can show a Scout status badge.

Scenario: "It's Saturday, Nov 14, 11:30 pm. You're at a bar on Ludlow St with
3 friends. Your phone buzzes: the app asks for a vibe check."

1. What do you do with that prompt? Which reward, if any, would make you tap
   it: skip the line, a free drink, a cover waiver, or a status badge? `[H8]
   [H7]`
   - Probe: Why that one over the others? Would the badge alone do it?
   - Probe: Would helping friends be enough without any reward?
2. On a typical night out, how many vibe checks do you think you'd actually
   send? Compare with what you did on your last night out. `[H7]`
   - Probe: What would make you stop after a few weeks?
3. Overall, how do you feel about this, from 1 very negative to 5 very
   positive? Would you use it to pick bars too, not just report? `[H12]`

## Wrap-up (1–2 min)

- "Anything I should have asked?"
- "Anyone you know who posts from bars a lot and might talk to us? Pass on our
  message; please don't give me their contact for the notes."
- Thank them. Remind them notes are anonymized.

## Which note-template field each section fills

| Section | Note-template fields |
|---|---|
| Screener | `segment` (= scout), `age_band` |
| Warm-up W1–W2 | `nights_out_per_month`, `typical_group_size`, `neighborhoods` |
| Core 1–4 | quotes tagged H7; `current_tools` (where they post/read); `venue_mentions` |
| Core 5 | `freshness_tolerance_min` |
| Concept 1 | `scout_motivator`, quotes tagged H8 |
| Concept 2 | `would_scout` |
| Concept 3 | `concept_reaction` |
| Not asked directly | `bad_pick_last_month`, `favorite_genres`, `top_factor_1..3`: fill only if they came up, else leave empty |
| Operator-only fields | leave empty: `operator_role`, `operator_wtp_usd_month`, `operator_wants` |
| System | `interview_id`, `date`, `is_synthetic` (= 0) |
