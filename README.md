# Salary Insights

Salary management for ACME's HR team: 10,000 employees across several countries, moved off spreadsheets into a web app where the HR Manager keeps salary history correct and answers pay questions in seconds, from the dashboard or the explorer. Sheets come in and go out as CSV.

Django 5.2 + DRF · React + TypeScript + Ant Design · PostgreSQL.

**Live demo: https://jeremy-moscow-minus-desert.trycloudflare.com**. No sign-in is needed: the brief asks for one HR Manager persona without authentication. The data is generated, and anyone may change it, so it is reset every night at 03:00 UTC.

## Run it locally

You need Docker (for PostgreSQL), [uv](https://docs.astral.sh/uv/) and Node 22.

```bash
make install   # backend, frontend and browser-test dependencies
make seed      # 10,000 demo employees with salary history
make dev       # database, API and UI together
```

Open **http://localhost:5180**. Ctrl+C stops the servers.

| Command | What it does |
|---|---|
| `make dev` | Starts PostgreSQL in Docker, applies migrations, runs the API (port 8100) and the UI (port 5180) |
| `make seed` | Loads 10,000 deterministic demo employees with salary history, replacing earlier demo data |
| `make test` | Backend tests (pytest, with a coverage gate) and frontend tests (Vitest) |
| `make lint` | ruff, strict mypy, import boundaries, ESLint and TypeScript |
| `make browser-tests` | Browser tests (Playwright, Chromium) against the built app, on a database of their own: the main flows and an accessibility check of every page |
| `make deploy` | Deploys this checkout to the demo VM by hand (`DEPLOY_HOST=deploy@<vm>`); CD needs no command |
| `make stop` | Stops the database |
| `make help` | Lists every command |

The ports are project-specific, so this runs alongside other local apps on 5173 or 8000.

## Deployment

One Ubuntu VM, set up once with [`deploy/setup-vm.sh`](deploy/setup-vm.sh): PostgreSQL, gunicorn under systemd, a nightly reset timer, and a Cloudflare tunnel for the public HTTPS address. CD is pulled by the VM: every two minutes [`deploy/pull.sh`](deploy/pull.sh) checks the head of `main`, and once its CI run has passed, downloads it, builds the frontend, migrates, switches over and restarts. GitHub needs no secrets or access to the VM. Design §10 has the details.

## How it was designed

Read in this order:

1. [Clarifying questions](docs/00-clarifying-questions.md), sent before any code, with the interviewer's answers
2. [Requirements](docs/01-requirements.md): one page covering goal, scope and what is deliberately left out, with reasons
3. [Design](docs/02-design.md): architecture, decisions, configuration, data model, API, deployment, testing
4. [Edge cases](docs/03-edge-cases.md): each case and where it is tested
5. [Build plan](docs/04-build-plan.md): milestones and the cut line
6. [AI usage](docs/ai-usage.md) and [`CLAUDE.md`](CLAUDE.md): how AI was used, and the rules it follows

## Layout

```
backend/    Django project: config/ (settings), apps/ (features), domain/ (pure Python), tests/
frontend/   React app: src/features/, src/components/, src/api/
browser-tests/  Playwright tests of the whole app in a real browser
deploy/     VM setup and deploy scripts
docs/       questions, requirements, design, edge cases, plan
```
