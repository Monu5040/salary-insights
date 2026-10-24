#!/usr/bin/env bash
# Deploy this checkout to the demo VM by hand, from a laptop (design §10). CD doesn't use it:
# the VM pulls each green push to main itself (pull.sh).
#   DEPLOY_HOST=deploy@<vm> [DEPLOY_SSH_KEY=~/.ssh/key] deploy/deploy.sh
# Builds the React app here, uploads a new release, installs it with release.sh, and checks it
# answers at the public address.
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

"${SSH[@]}" "$HOST" "$DIR/deploy/release.sh" "$DIR" "$RELEASE"
# So the VM's own CD (pull.sh) doesn't deploy this commit again.
"${SSH[@]}" "$HOST" "echo $(git -C "$ROOT" rev-parse HEAD) > $APP/deployed-sha"

# The tunnel's public address, and a check that the app answers through it.
URL="$("${SSH[@]}" "$HOST" "journalctl -u acme-salary-tunnel --no-pager -o cat | grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' | tail -1")"
curl -fsS --retry 5 --retry-delay 3 --retry-all-errors "$URL/readyz/" >/dev/null
echo "Live at $URL"
