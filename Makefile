# Common tasks. `make dev` runs the database, the API and the UI with one command.
.DEFAULT_GOAL := help
.PHONY: help install db dev seed test lint fmt browser-tests deploy stop

help:  ## List the commands
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

install:  ## Install backend, frontend and browser-test dependencies (and the test browser)
	cd backend && uv sync
	cd frontend && npm install
	cd browser-tests && npm install && npx playwright install chromium

db:  ## Start PostgreSQL in Docker and wait until it is ready
	docker compose up -d --wait db

dev: db  ## Run the API and the UI together; Ctrl+C stops both
	cd backend && uv run python manage.py migrate
	@echo "UI: http://localhost:5180   API: http://localhost:8100"
	@trap 'trap - INT TERM EXIT; kill 0' INT TERM EXIT; \
	(cd backend && uv run python manage.py runserver 8100) & \
	(cd frontend && npm run dev) & \
	wait

seed: db  ## Load 10,000 demo employees with salary history (replaces demo data)
	cd backend && uv run python manage.py migrate -v 0 && uv run python manage.py seed --reset

test: db  ## Run the backend and frontend tests
	cd backend && uv run pytest --cov
	cd frontend && npm test

lint:  ## Lint, check formatting, types and import boundaries
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run lint-imports
	cd frontend && npm run lint && npm run typecheck

fmt:  ## Format the backend code
	cd backend && uv run ruff format . && uv run ruff check --fix .

browser-tests: db  ## Run the browser tests (Playwright) against the built app, on a database of its own
	./browser-tests/run.sh

deploy:  ## Deploy this checkout to the demo VM by hand (DEPLOY_HOST=deploy@<vm>); CD is pulled by the VM
	./deploy/deploy.sh

stop:  ## Stop the database
	docker compose down
