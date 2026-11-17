<!--
Purpose: PR template draft (integration copies it to .github/pull_request_template.md).
Status: agreed.
Last updated: 2026-11-17
-->
## What and why
<!-- One or two sentences. -->

## Workstream / folder
<!-- e.g. backend / `backend/`. A PR touches only folders its workstream owns (docs/CONTRACTS.md). -->

## Linked story or task
<!-- US-… id from docs/specs/requirements.md, or OUTLINE task id, or GOOD_FIRST_PRS number. -->

## How tested
<!-- Commands you ran and their output (paste the last lines). -->
```
```

## Synthetic data touched
- [ ] None
- [ ] Yes: rows have `is_synthetic`, files under a `synthetic` path / `syn_` tables, `# SYNTHETIC:` comments added, registry `docs/synthetic/<workstream>.md` updated, UI shows the "demo data" badge

## Contract impact
- [ ] None
- [ ] Contract change request logged in `docs/workstreams/<workstream>.md` (id: CCR-…)

## Screenshots (UI changes)

## Checklist
- [ ] Only my workstream's folders changed
- [ ] Tests / checks pass locally
- [ ] No secrets, `.env`, or generated `.db` files committed
- [ ] Docs updated (`docs/workstreams/<workstream>.md`)
