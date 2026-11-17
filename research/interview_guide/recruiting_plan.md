# Recruiting plan (real interviews)

Status as of 2026-11-17: zero real interviews have been run. Everything in
`research/synthetic/` is placeholder data. Real interviews start after the
Nov 17 demo.

## Target

| Segment | Target | Guide |
|---|---|---|
| Consumers | 7 | `consumer.md` (25–30 min) |
| Scouts | 3 | `scout.md` (20 min) |
| Operators (owner / GM / bar manager / promoter at an LES bar) | 3–5 | `operator.md` (25 min) |
| Total | 13–15 (minimum 10) | |

No incentive is offered: there is no budget. Say so up front in every message.

## Channels

- Consumers and Scouts
  - NYU classmates and friends (in person, class group chats, club chats).
  - Group chats: ask each person to forward the message to one or two friends
    who go out in the LES (snowball). Cap at 2 people per referrer to avoid
    one friend group dominating.
  - Scouts: ask in the same chats for "people who post stories or text
    friends from bars"; consumers who screen as heavy sharers can be moved to
    the Scout guide.
- Operators
  - Walk-ins at LES venues on an early weeknight (Tue–Thu), 5–7 pm, before
    service. Use `data/launch_venues.csv` to pick 8–10 venues on a walkable
    route (e.g. Ludlow, Orchard, Rivington, Stanton). Go in pairs: one asks,
    one takes notes.
  - If the right person isn't in, leave the short pitch with staff and ask
    when they're usually around. Don't leave or collect personal contacts in
    the repo; any follow-up goes through the venue's public channel.
  - Ask each operator for one referral (another manager or promoter nearby).

## Outreach messages (no incentive)

Group chat / friends (consumers):

> Hey! For an NYU class project we're learning how people pick bars on a
> night out (especially LES). Would you do a 25-minute chat this week or
> next? Over coffee or video, your pick. No names recorded, notes are
> anonymized, and you can stop anytime. We can't pay anything (no budget),
> but it'd help a lot. Reply here and I'll DM you times.

Scouts:

> Do you post stories or text friends about what a bar is like while you're
> out? For an NYU class project we'd love 20 minutes to hear how you do it.
> Anonymous notes, no payment (no budget), stop anytime. Interested?

Forward request:

> If you know someone who goes out in the LES a lot, could you forward this
> to them? Please don't send me their contact; they can reply to you or the
> chat.

Operator walk-in (spoken, at the door):

> Hi, I'm an NYU student doing a class project on how groups pick bars in the
> LES and how venues get the word out about cover, DJs and specials. Could I
> ask the manager or owner about 25 minutes of questions, now or another
> early evening this week? I'm not selling anything, there's no payment, and
> I don't record names.

## Schedule (starting the week of Nov 17, 2026)

| Week | Dates | Plan |
|---|---|---|
| 1 | Mon Nov 16 – Sun Nov 22 | Nov 17 demo. After the demo: send consumer and Scout messages; book 3–4 consumer interviews; 1 pilot interview to time the consumer guide (target ≤ 30 min); fix the guide. |
| 2 | Mon Nov 23 – Sun Nov 29 | Thanksgiving week: expect fewer people. Remote consumer and Scout interviews (3–4). Operator walk-ins Tue Nov 24, 5–7 pm. |
| 3 | Mon Nov 30 – Sun Dec 6 | Operator walk-ins Tue Dec 1 and Wed Dec 2, 5–7 pm. Finish consumers (to 7) and Scouts (to 3). |
| 4 | Mon Dec 7 – Sun Dec 13 | Fill gaps (operators to 3–5). Enter all rows, run `python -I research/validate.py --real`, re-run analysis. |

## Tracking (by ID only)

Keep a tracker with these columns only; no names, contacts or handles. Store
the contact itself in the recruiter's own phone or chat, never in the repo.

| Column | Example values |
|---|---|
| `slot_id` | rec-01, rec-02, … |
| `segment` | consumer; scout; operator |
| `channel` | class; group_chat; referral; walk_in |
| `status` | contacted; screened_out; scheduled; done; no_show; declined |
| `interview_id` | int-r-001 (once done) |
| `venue_license_id` | operators only, from `data/launch_venues.csv` |
| `interviewer` | team role (e.g. research-1), not a name |

When an interview is done: fill `note_template.md`, add rows to
`research/interviews/interviews.csv` and `research/interviews/quotes.csv` with
`is_synthetic=0`, and run the validator.
