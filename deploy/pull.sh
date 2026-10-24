#!/usr/bin/env bash
# Continuous deployment, pulled by the VM (design §10). A systemd timer runs this every two
# minutes as the deploy user. When the newest push to main has passed CI and isn't deployed
# yet, it downloads that commit, builds the React app and installs it with release.sh.
#
# Pulled, not pushed: the VM's provider drops data from some networks, GitHub's runners among
# them, so a push from CI could stall halfway. Requests the VM makes itself get through.
set -euo pipefail
REPO="Monu5040/salary-insights"
APP=/opt/acme-salary
exec 9>"$APP/pull.lock"
flock -n 9 || exit 0 # a deploy is already running

# Only ever the head of main, never an older green commit, so a deploy can't go backwards.
# ls-remote costs no API quota; the one API call stays well inside GitHub's 60 an hour for
# a public repository without a token.
SHA="$(git ls-remote "https://github.com/$REPO.git" refs/heads/main | cut -f1)"
[ -n "$SHA" ] || exit 0
[ "$SHA" = "$(cat "$APP/deployed-sha" 2>/dev/null || true)" ] && exit 0
PASSED="$(curl -fsS --max-time 20 \
  "https://api.github.com/repos/$REPO/actions/workflows/ci.yml/runs?head_sha=$SHA&status=success&per_page=1" |
  python3 -c 'import json, sys; print(json.load(sys.stdin)["total_count"])')"
[ "$PASSED" -gt 0 ] || exit 0 # CI hasn't passed for it (yet)
# A commit that failed to deploy is tried once, not every two minutes; the next push is tried.
[ "$SHA" = "$(cat "$APP/failed-sha" 2>/dev/null || true)" ] && exit 0

RELEASE="${SHA:0:7}-$(date -u +%Y%m%d%H%M%S)"
DIR="$APP/releases/$RELEASE"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
echo "Deploying $SHA"
if ! (
  curl -fsSL --max-time 120 "https://codeload.github.com/$REPO/tar.gz/$SHA" |
    tar -xz -C "$WORK" --strip-components=1
  cd "$WORK/frontend"
  npm ci --silent --no-audit --no-fund
  npm run build --silent
  mkdir -p "$DIR/frontend"
  cp -R "$WORK/backend" "$WORK/deploy" "$DIR/"
  cp -R "$WORK/frontend/dist" "$DIR/frontend/"
  "$DIR/deploy/release.sh" "$DIR" "$RELEASE"
); then
  echo "$SHA" >"$APP/failed-sha"
  echo "Deploying $SHA failed; the previous release keeps serving" >&2
  exit 1
fi
echo "$SHA" >"$APP/deployed-sha"
