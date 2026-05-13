#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/telegram-monitor/telegram-monitor.env}"
BACKUP_DIR="${BACKUP_DIR:-/opt/telegram-monitor/backups}"

if [ ! -f "$ENV_FILE" ]; then
  echo "Env file not found: $ENV_FILE"
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

mkdir -p "$BACKUP_DIR"
chmod 750 "$BACKUP_DIR"

read -r DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD <<EOF
$(python3 - <<'PY'
import os
from urllib.parse import urlparse

url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
parsed = urlparse(url)
print(parsed.hostname or "127.0.0.1", parsed.port or 5432, parsed.path.lstrip("/"), parsed.username or "", parsed.password or "")
PY
)
EOF

FILE="$BACKUP_DIR/telegram_monitor_$(date +%Y%m%d_%H%M%S).sql.gz"
PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$FILE"
chmod 640 "$FILE"
echo "$FILE"
