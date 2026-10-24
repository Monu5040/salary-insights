#!/usr/bin/env bash
# Deploy this checkout to the demo VM (design §10). CD runs it after the tests pass on main;
# it also works by hand from a laptop:
#   DEPLOY_HOST=deploy@<vm> [DEPLOY_SSH_KEY=~/.ssh/key] deploy/deploy.sh
# Builds the React app here, uploads a new release, installs its locked dependencies,
# migrates, switches to it, restarts, and checks it answers. The last five releases are kept.
set -euo pipefail

HOST="${DEPLOY_HOST:?set DEPLOY_HOST, such as deploy@151.185.44.30}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RELEASE="$(git -C "$ROOT" rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)"
APP=/opt/acme-salary
DIR="$APP/releases/$RELEASE"
# One SSH connection, opened once and shared by every step: the VM's provider sometimes drops
# a new connection, so a deploy that opened five could fail halfway (exit 255).
SOCKET="$(mktemp -d)/ssh"
SSH=(ssh -o BatchMode=yes -o ConnectionAttempts=5 -o ConnectTimeout=20
  -o ServerAliveInterval=15 -o ControlMaster=auto -o "ControlPath=$SOCKET" -o ControlPersist=600)
[ -n "${DEPLOY_SSH_KEY:-}" ] && SSH+=(-i "$DEPLOY_SSH_KEY" -o IdentitiesOnly=yes)
trap '"${SSH[@]}" -O exit "$HOST" 2>/dev/null || true' EXIT

echo "Building the frontend"
(cd "$ROOT/frontend" && npm ci --silent && npm run build --silent)

echo "Uploading release $RELEASE"
"${SSH[@]}" "$HOST" "mkdir -p $DIR"
rsync -az --delete -e "${SSH[*]}" \
  --exclude .venv --exclude __pycache__ --exclude '.*_cache' --exclude staticfiles \
  "$ROOT/backend" "$ROOT/deploy" "$HOST:$DIR/"
"${SSH[@]}" "$HOST" "mkdir -p $DIR/frontend"
rsync -az -e "${SSH[*]}" "$ROOT/frontend/dist" "$HOST:$DIR/frontend/"

"${SSH[@]}" "$HOST" bash -s -- "$DIR" "$RELEASE" <<'REMOTE'
set -euo pipefail
DIR="$1"; RELEASE="$2"; APP=/opt/acme-salary
cd "$DIR/backend"
set -a; . "$APP/.env"; set +a
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
REMOTE

# The tunnel's public address, and a check that the app answers through it.
URL="$("${SSH[@]}" "$HOST" "journalctl -u acme-salary-tunnel --no-pager -o cat | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1")"
curl -fsS --retry 5 --retry-delay 3 --retry-all-errors "$URL/readyz/" >/dev/null
echo "Live at $URL"
