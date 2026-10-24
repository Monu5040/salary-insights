# 04 · Build plan

Thin vertical slices, each demoable and tested. Docs before code. A commit at every green step, so the history reads as the solution evolving.

## Milestones

| # | Milestone | Commits | Done when |
|---|---|---|---|
| M0 | Thinking | clarifying questions · the interviewer's answers · one-page requirements · design, edge cases and this plan · `CLAUDE.md` | Scope agreed; what's left out is written down with the reason |
| M1 | Skeleton | Django project (split settings, DRF, drf-spectacular) with health checks and the working assumptions as settings · frontend scaffold (Vite, TypeScript, Ant Design, Router, TanStack Query) · `make` commands with Postgres in Compose · CI with ruff, mypy, import-linter, `makemigrations --check` and `check --deploy` | `make dev` serves the app; CI green |
| M2 | Domain core | money and rounding · conversion at fixed rates · statistics · text rules for names, codes and search — test-first, no Django | Rounding, precision and conversion covered by unit tests, shared with the frontend |
| M3 | Data and seed | reference data with fixed rates · the employee with their current salary and database rules · `manage.py seed` | 10,000 employees seeded in about a second; invariants tested |
| M4 | Employees API | problem+json errors with request ids · reference lists and settings for the screens · the directory (search, filter, sort, page) · add, edit and delete with `If-Match` versions | API tests including 409/412/428 and query counts |
| M5 | Insights API | summary · explorer · dashboard presets · peers | Tests on a small hand-computed company |
| M6 | Screens | directory · record · add and edit forms · Change salary with an exact preview · insights dashboard and explorer · peers card | Frontend tests for each flow |
| M7 | Hardening | security headers and CSP · Django serves the built app · error and empty states · accessibility · Playwright | Browser tests and axe green in CI |
| M8 | Ship | VM setup and deploy scripts · CD: the VM pulls every green push to `main` · README | The live URL works from a clean browser |
| M9 | Optional extras | effective-dated salary history, back- and future-dated · insights on any date · pay equity by role · CSV import (preview, then whole file or nothing) and export | Each covered by API, frontend and browser tests; deployed |
| — | Next, if wanted | sign-in and roles before real data · audit log | — |

**Cut line.** M0–M6 plus M8 is the demo. M7's security headers stay in even when time is short; the rest of M7 goes before any core feature does.

## How AI is used

- Claude Code is the pair programmer. I review the design before any code is generated.
- `CLAUDE.md` fixes the conventions (thin views, services for writes and selectors for reads, money rules, no `date.today()` in logic, tests with every change), so generated code stays consistent.
- Money, conversion and statistics are written test-first; generated code has to pass tests I wrote or reviewed.
- Every commit passes lint, type checks and tests. Nothing lands on "looks right".
- `docs/ai-usage.md` keeps the key prompts and where the AI got something wrong.

## Demo video (~5 minutes)

The problem → find an employee → record a +7% raise with its preview → insights update → answer five pay questions (payroll by country, ranges by department, salary by job title, an explorer question, an employee against peers) → two people editing at once → architecture and trade-offs → tests, CI and the deploy.

## Risks

| Risk | Mitigation |
|---|---|
| Scope creep | The interviewer's answers fix scope; optional extras (M9) only after M8 ships, minimal versions, and nothing the brief calls not required |
| Subtle money bugs in generated code | Domain tests first; property-based tests for rounding and conversion |
| An open demo gets vandalized | Generated data only, reseeded nightly |
| The live URL is down when the reviewer opens it | systemd restarts the app; the deploy checks the public address answers |
