#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-telegram-monitor}"
APP_USER="${APP_USER:-telegram-monitor}"
APP_DIR="${APP_DIR:-/opt/telegram-monitor}"
CONFIG_DIR="${CONFIG_DIR:-/etc/telegram-monitor}"
SERVICE_NAME="${SERVICE_NAME:-telegram-monitor}"
SOURCE_DIR="${SOURCE_DIR:-$(pwd)}"
DB_NAME="${DB_NAME:-telegram_monitor}"
DB_USER="${DB_USER:-telegram_monitor}"
DB_PASSWORD="${DB_PASSWORD:-$(openssl rand -hex 24)}"
SECRET_KEY_VALUE="${SECRET_KEY_VALUE:-$(openssl rand -hex 32)}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo bash scripts/deploy_ubuntu_venv.sh"
  exit 1
fi

if [ ! -f "$SOURCE_DIR/requirements.txt" ] || [ ! -f "$SOURCE_DIR/main.py" ]; then
  echo "SOURCE_DIR must point to the project root. Current: $SOURCE_DIR"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  build-essential \
  libpq-dev \
  openssl \
  postgresql \
  postgresql-client \
  python3 \
  python3-dev \
  python3-pip \
  python3-venv \
  redis-server \
  rsync

systemctl enable --now postgresql
systemctl enable --now redis-server

if ! id "$APP_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
fi

mkdir -p "$APP_DIR/current" "$APP_DIR/logs" "$APP_DIR/backups" "$CONFIG_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 750 "$APP_DIR" "$APP_DIR/current" "$APP_DIR/logs" "$APP_DIR/backups"
chmod 750 "$CONFIG_DIR"

rsync -a --delete \
  --exclude '.git' \
  --exclude '.env' \
  --exclude '.venv' \
  --exclude 'venv' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.pgdata' \
  --exclude '.pgdata*' \
  --exclude '*.log' \
  --exclude '*.pid' \
  "$SOURCE_DIR/" "$APP_DIR/current/"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/current"

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD';
  ELSE
    ALTER ROLE $DB_USER WITH PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '$DB_NAME')\\gexec
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
SQL

ENV_FILE="$CONFIG_DIR/telegram-monitor.env"
if [ ! -f "$ENV_FILE" ]; then
  if [ -f "$SOURCE_DIR/.env" ]; then
    install -m 600 -o root -g "$APP_USER" "$SOURCE_DIR/.env" "$ENV_FILE"
  else
    install -m 600 -o root -g "$APP_USER" "$SOURCE_DIR/.env.example" "$ENV_FILE"
  fi
fi

sed -i "s#^DATABASE_URL=.*#DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME#" "$ENV_FILE"
sed -i "s#^REDIS_URL=.*#REDIS_URL=redis://127.0.0.1:6379/0#" "$ENV_FILE"
sed -i "s#^APP_ENV=.*#APP_ENV=production#" "$ENV_FILE"
if grep -q '^SECRET_KEY=change-this-32-byte-minimum-secret-key$' "$ENV_FILE"; then
  sed -i "s#^SECRET_KEY=.*#SECRET_KEY=$SECRET_KEY_VALUE#" "$ENV_FILE"
fi
chown root:"$APP_USER" "$ENV_FILE"
chmod 640 "$ENV_FILE"

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/python" -m pip install --upgrade pip setuptools wheel
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/current/requirements.txt"
chown -R "$APP_USER:$APP_USER" "$APP_DIR/venv"

install -m 0644 "$APP_DIR/current/deploy/telegram-monitor-venv.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload

sudo -u "$APP_USER" bash -c "cd '$APP_DIR/current' && set -a && . '$ENV_FILE' && set +a && '$APP_DIR/venv/bin/alembic' upgrade head"

systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
systemctl --no-pager --full status "$SERVICE_NAME"

echo
echo "Deployed $APP_NAME"
echo "App dir: $APP_DIR/current"
echo "Env file: $ENV_FILE"
echo "Logs: $APP_DIR/logs"
echo "Backups: $APP_DIR/backups"
