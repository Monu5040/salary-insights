#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 VM for the demo (design §10). Run as root:
#   ssh root@<vm> "bash -s -- '<deploy public key>'" < deploy/setup-vm.sh
# Installs PostgreSQL, uv, Node.js and a Cloudflare tunnel, creates the `deploy` user, and
# starts the timer that pulls each green push to main (pull.sh). Safe to run again: it never
# replaces the database or the secrets.
#
# The tunnel gives the demo a public HTTPS address without opening any port: this VM's provider
# drops some inbound traffic, so no certificate authority could validate it (design §10).
set -euo pipefail

DEPLOY_KEY="$1"
APP=/opt/acme-salary

apt-get update -q
apt-get install -y -q postgresql rsync curl
systemctl enable --now postgresql
# Node.js, so the VM can build the React app of each release it pulls. The official build,
# checked against the checksum published beside it.
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 22 ]; then
  NODE_DIST=https://nodejs.org/dist/latest-v22.x
  NODE_TAR="$(curl -fsSL "$NODE_DIST/SHASUMS256.txt" | grep -o 'node-v[0-9.]*-linux-x64.tar.xz' | head -1)"
  curl -fsSL -o "/tmp/$NODE_TAR" "$NODE_DIST/$NODE_TAR"
  (cd /tmp && curl -fsSL "$NODE_DIST/SHASUMS256.txt" | grep " $NODE_TAR\$" | sha256sum -c -)
  tar -xJf "/tmp/$NODE_TAR" -C /usr/local --strip-components=1
  rm "/tmp/$NODE_TAR"
fi

if ! command -v cloudflared >/dev/null; then
  curl -fsSL -o /tmp/cloudflared.deb \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  dpkg -i /tmp/cloudflared.deb
fi

# The deploy user owns the app, signs in with the CD key only, may restart the app, and may
# read the tunnel's log for its address.
id deploy >/dev/null 2>&1 || useradd --create-home --shell /bin/bash deploy
usermod -aG systemd-journal deploy
install -d -m 0700 -o deploy -g deploy /home/deploy/.ssh
echo "$DEPLOY_KEY" > /home/deploy/.ssh/authorized_keys
chown deploy:deploy /home/deploy/.ssh/authorized_keys
chmod 0600 /home/deploy/.ssh/authorized_keys
cat > /etc/sudoers.d/acme-salary <<'SUDO'
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart acme-salary
SUDO
chmod 0440 /etc/sudoers.d/acme-salary

# uv, which installs Python 3.12 and the locked dependencies for each release.
if [ ! -x /usr/local/bin/uv ]; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh
fi

install -d -o deploy -g deploy "$APP" "$APP/releases"

# The database and the secrets, made once; they live only on this VM.
if [ ! -f "$APP/.env" ]; then
  DB_PASSWORD="$(openssl rand -hex 24)"
  sudo -u postgres psql -v ON_ERROR_STOP=1 -q <<SQL
CREATE ROLE acme LOGIN PASSWORD '${DB_PASSWORD}';
CREATE DATABASE acme OWNER acme;
SQL
  umask 077
  cat > "$APP/.env" <<ENV
ENV=demo
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_ALLOWED_HOSTS=.trycloudflare.com,localhost
DJANGO_SECRET_KEY=$(openssl rand -base64 48 | tr -d '\n')
DATABASE_URL=postgres://acme:${DB_PASSWORD}@localhost:5432/acme
SPA_DIR=${APP}/current/frontend/dist
ENV
  chown deploy:deploy "$APP/.env"
fi

# The app under systemd: gunicorn on localhost, behind the tunnel.
cat > /etc/systemd/system/acme-salary.service <<UNIT
[Unit]
Description=ACME Salary (gunicorn)
After=network.target postgresql.service
Requires=postgresql.service

[Service]
User=deploy
Group=deploy
WorkingDirectory=${APP}/current/backend
EnvironmentFile=${APP}/.env
ExecStart=${APP}/current/backend/.venv/bin/gunicorn config.wsgi --bind 127.0.0.1:8000 \\
  --workers 3 --threads 4 --worker-class gthread --timeout 30 --access-logfile -
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

# The demo is open to anyone, so its data goes back to the seed every night at 03:00 UTC.
cat > /etc/systemd/system/acme-salary-reset.service <<UNIT
[Unit]
Description=Reset the ACME Salary demo data

[Service]
Type=oneshot
User=deploy
WorkingDirectory=${APP}/current/backend
EnvironmentFile=${APP}/.env
ExecStart=${APP}/current/backend/.venv/bin/python manage.py seed --reset
UNIT
cat > /etc/systemd/system/acme-salary-reset.timer <<UNIT
[Unit]
Description=Reset the ACME Salary demo data every night

[Timer]
OnCalendar=*-*-* 03:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
UNIT
# Continuous deployment: every two minutes, deploy the newest push to main that passed CI.
cat > /etc/systemd/system/acme-salary-pull.service <<UNIT
[Unit]
Description=Deploy the newest green push to main
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=deploy
Environment=PATH=/usr/local/bin:/usr/bin:/bin
ExecStart=/bin/bash -c 'exec "\$(readlink -f ${APP}/current)/deploy/pull.sh"'
UNIT
cat > /etc/systemd/system/acme-salary-pull.timer <<UNIT
[Unit]
Description=Check for a new green push to main every two minutes

[Timer]
OnBootSec=1min
OnUnitInactiveSec=2min

[Install]
WantedBy=timers.target
UNIT

systemctl daemon-reload
systemctl enable acme-salary.service acme-salary-reset.timer acme-salary-pull.timer
systemctl start acme-salary-reset.timer acme-salary-pull.timer

# The public address: a Cloudflare quick tunnel to gunicorn. Cloudflare serves HTTPS and passes
# X-Forwarded-Proto on; the address (https://<words>.trycloudflare.com) is in the unit's log.
cat > /etc/systemd/system/acme-salary-tunnel.service <<UNIT
[Unit]
Description=Public HTTPS address for ACME Salary (Cloudflare quick tunnel)
After=network-online.target acme-salary.service
Wants=network-online.target

[Service]
ExecStart=/usr/bin/cloudflared tunnel --no-autoupdate --url http://127.0.0.1:8000
Restart=always
RestartSec=5
DynamicUser=yes

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now acme-salary-tunnel.service
echo "VM ready"
