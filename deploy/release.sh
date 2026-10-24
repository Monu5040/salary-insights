#!/usr/bin/env bash
# Install a release that is already on the VM, and switch to it (design §10). Run as the deploy
# user by pull.sh (CD) or deploy.sh (by hand):
#   release.sh /opt/acme-salary/releases/<release> <release>
# Installs its locked dependencies, checks the settings, migrates, then points `current` at it,
# restarts and waits until it answers. Anything failing before the switch leaves the previous
# release serving. The last five releases are kept.
set -euo pipefail
DIR="$1"
RELEASE="$2"
APP=/opt/acme-salary

cd "$DIR/backend"
set -a
. "$APP/.env"
set +a
export RELEASE SPA_DIR="$DIR/frontend/dist"

uv sync --locked --no-dev --python 3.12 --quiet
.venv/bin/python manage.py check --deploy --fail-level WARNING
.venv/bin/python manage.py collectstatic --noinput -v 0
.venv/bin/python manage.py migrate --noinput

ln -sfn "$DIR" "$APP/current"
sudo /usr/bin/systemctl restart acme-salary

for _ in $(seq 30); do
  curl -fsS -H "Host: localhost" http://127.0.0.1:8000/readyz/ >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS -H "Host: localhost" http://127.0.0.1:8000/readyz/ >/dev/null

# An empty database gets the demo data once; the nightly timer resets it after that.
if [ "$(.venv/bin/python manage.py shell --no-imports -c 'from apps.employees.models import Employee; print(Employee.objects.exists())')" = "False" ]; then
  .venv/bin/python manage.py seed
fi

ls -1dt "$APP"/releases/* | tail -n +6 | xargs -r rm -rf
echo "Deployed $RELEASE"
