#!/usr/bin/env sh
set -eu

APP_DIR="${APP_DIR:-/opt/telegram-monitor}"
SERVICE_NAME="${SERVICE_NAME:-telegram-monitor}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Bu script root huquqi bilan ishlashi kerak: sudo sh scripts/install_systemd.sh"
  exit 1
fi

if [ ! -f "$APP_DIR/docker-compose.yml" ]; then
  echo "$APP_DIR ichida docker-compose.yml topilmadi"
  exit 1
fi

install -m 0644 "$APP_DIR/deploy/telegram-monitor.service" "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
systemctl --no-pager --full status "$SERVICE_NAME"
