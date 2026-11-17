# AI-use disclosure

The code, notebooks and explanation notes in `coursework/` (the tiny transformer and the Scout churn
model) were **drafted with Claude (Anthropic's AI assistant, via Claude Code)** on Nov 17, 2026, from
a plan Ryan Mehta wrote and approved (`docs/prd/coursework/`).

**Before submitting either exercise, Ryan must check his course's AI-use policy.** The assignment
sheets and the policy were not available when this was written. Depending on the policy, Ryan may
need to:

- cite this disclosure (or a shortened version) in the submission,
- retype or rewrite parts of the code himself,
- answer the self-check questions in each `NOTES.md` without notes, to show he understands every step.

What the AI did: wrote the `.py` scripts, tests, notebooks, the stand-in synthetic Scout data
generator, and both `NOTES.md` files, then ran everything and recorded the results.
What it did not do: no pretrained models or outside text were used. The transformer is trained from
scratch on public NY State Liquor Authority licence names, and all Scout data is synthetic.

Suggested disclosure line (edit to match the policy):

> I used Claude (Anthropic) to help draft the code and explanation notes for this assignment. I
> reviewed, ran and tested all of it, and I can explain every step.
