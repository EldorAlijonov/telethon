#!/usr/bin/env sh
set -eu

echo "Migratsiyalar bajarilmoqda..."
alembic upgrade head

echo "Bot ishga tushmoqda..."
exec python main.py
