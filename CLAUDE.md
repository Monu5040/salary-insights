# CLAUDE.md

Salary management for ACME's HR team: 10,000 employees, several countries, one HR Manager persona with no sign-in. Django 5.2 + DRF backend, React (Vite, TypeScript, Ant Design, TanStack Query) frontend, PostgreSQL. One gunicorn process serves the API and the built app; `deploy/` holds the VM setup and deploy scripts.

The docs are the spec. Read the relevant one before changing behaviour, and update it in the same commit when behaviour changes:
- `docs/00-clarifying-questions.md`: the questions and the interviewer's answers, which fix the scope
- `docs/01-requirements.md`: scope, and what is deliberately left out
- `docs/02-design.md`: architecture, decisions (D1–D10), configuration, data model, analytics definitions, API, deployment
- `docs/03-edge-cases.md`: every edge case and the test that covers it
- `docs/04-build-plan.md`: milestones; build them in order, one thin slice at a time

## Commands (from M1)
`make dev` · `make test` · `make lint` (ruff, mypy, import-linter, eslint, tsc) · `make seed` · `make browser-tests` · `make deploy`

## Rules
- **Layers.** Views and serializers handle HTTP only. `services` own writes: the transaction, business rules and the version check. `selectors` own reads and analytics. `domain/` is pure Python with no Django imports. import-linter enforces this.
- **Money.** `Decimal` end to end, `NUMERIC(19,4)` plus a currency code, strings in JSON. Never `float`. Round half-up to the currency's minor unit, and only where the design says.
- **Dates.** Never `date.today()` or `timezone.now()` in business logic: use the injected `Clock` and the `ORG_TIME_ZONE` setting.
- **Assumptions are configuration.** Anything listed in design §2 Configuration (reporting currency, fixed rates, group-size threshold, time zone, dashboard questions) is read from settings or reference data, never hard-coded.
- **Scope.** Stay inside `docs/01-requirements.md`. Anything under "Deliberately left out" needs the user's say-so first.
- **One transaction per business operation.** The data and its version bump commit together.
- **Concurrent edits.** Every write to an employee (salary included) locks the employee row first, checks the `If-Match` version and bumps it.
- **SQL.** ORM or parameterized SQL only; sort and filter fields are allow-listed.
- **Privacy.** Never log salaries, names, emails, request bodies or `str(IntegrityError)`.
- **Migrations.** Backward-compatible (expand now, contract in a later release); `makemigrations --check` stays clean.
- **Frontend.** Server state lives in TanStack Query and view state in the URL. Salary writes are never optimistic. No `dangerouslySetInnerHTML`.

## Tests
- Every change ships with tests. Write money, FX, date and statistics code test-first.
- Domain unit tests are fast and use no database. Integration tests use real Postgres and roll back.
- Deterministic: injected `Clock`, fixed random seeds, no network.
- List and detail endpoints assert their query counts.
- Each new edge case gets a row in `docs/03-edge-cases.md`.

## Git
Small commits at every green step, with a message that says why. Never commit secrets or `.env`. Record prompts, and anywhere the AI got something wrong, in `docs/ai-usage.md`.
