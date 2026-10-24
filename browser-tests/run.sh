#!/usr/bin/env bash
# Browser tests (`make browser-tests`): Playwright in Chromium against the built app, served by
# Django as in production. The tests write, so they run on a
# database of their own (acme_browser_tests), seeded afresh each time: your development data is never
# touched. Arguments go to Playwright, such as a test file or --headed.
set -euo pipefail
cd "$(dirname "$0")/.."
export DJANGO_SETTINGS_MODULE=config.settings.browser_tests
PORT=8300
mkdir -p browser-tests/results

(cd frontend && npm run build > /dev/null)

cd backend
# The database named in config/settings/browser_tests.py, created through the server DATABASE_URL names.
uv run python - <<'PY'
import os

import psycopg

url = os.environ.get("DATABASE_URL", "postgres://acme:acme@localhost:5432/acme")
with psycopg.connect(url, autocommit=True) as connection:
    if not connection.execute("SELECT 1 FROM pg_database WHERE datname = 'acme_browser_tests'").fetchone():
        connection.execute("CREATE DATABASE acme_browser_tests")
PY
uv run python manage.py migrate -v 0
uv run python manage.py seed --reset > /dev/null

# exec, so each pid is the process itself and stopping it stops its children too.
(exec .venv/bin/gunicorn config.wsgi --workers 1 --threads 8 --bind "127.0.0.1:$PORT" \
  --access-logfile -) > ../browser-tests/results/server.log 2>&1 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null || true' EXIT
for _ in $(seq 1 50); do
  curl -sf --max-time 2 -o /dev/null "http://127.0.0.1:$PORT/healthz/" && break
  sleep 0.2
done

cd ../browser-tests
npx playwright test "$@"
