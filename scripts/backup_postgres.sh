#!/usr/bin/env sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/telegram_monitor_$(date +%Y%m%d_%H%M%S).sql.gz"

docker compose exec -T postgres pg_dump -U bot telegram_monitor | gzip > "$FILE"
echo "Backup yaratildi: $FILE"
