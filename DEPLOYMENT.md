# Deployment Guide

## Ubuntu server

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo mkdir -p /opt/telegram-monitor
sudo chown "$USER":"$USER" /opt/telegram-monitor
cd /opt/telegram-monitor
git clone <repo-url> .
cp .env.example .env
nano .env
docker compose up -d --build
```

`.env` ichida production uchun kamida quyilarni to'g'ri kiriting:

- `BOT_TOKEN`
- `ADMIN_IDS`
- `API_ID`
- `API_HASH`
- `SECRET_KEY`
- `APP_ENV=production`

Docker Compose ichida bot PostgreSQL va Redisga container nomlari orqali ulanadi:

```env
DATABASE_URL=postgresql+asyncpg://bot:bot_password@postgres:5432/telegram_monitor
REDIS_URL=redis://redis:6379/0
```

## Systemd

```bash
sudo sh scripts/install_systemd.sh
sudo journalctl -u telegram-monitor -f
```

Service `docker compose up --remove-orphans` ni foreground rejimida yuritadi. Bot containeri start paytida `scripts/start.sh` orqali migrationni bajaradi va keyin `python main.py` ni ishga tushiradi.

Qayta build qilib restart qilish:

```bash
cd /opt/telegram-monitor
sudo docker compose build
sudo systemctl restart telegram-monitor
```

## Migration

```bash
docker compose run --rm bot alembic upgrade head
```

## Loglar

```bash
docker compose logs -f bot
docker compose logs -f postgres
docker compose logs -f redis
sudo journalctl -u telegram-monitor -f
```

Health tekshirish:

```bash
curl -fsS http://localhost:8080/health
```

## Backup

```bash
BACKUP_DIR=/opt/backups sh scripts/backup_postgres.sh
```

## Restore

```bash
gunzip -c backups/telegram_monitor_YYYYmmdd_HHMMSS.sql.gz | docker compose exec -T postgres psql -U bot telegram_monitor
```

## Monitoring

Admin `System health` tugmasi PostgreSQL va Redis holatini tekshiradi. Docker Compose Prometheus va Grafana servislarini ham ko'taradi:

```bash
docker compose up -d prometheus grafana
```

Endpointlar:

- Bot metrics: `:9108`
- Worker metrics: `:9109`
- Prometheus: `:9090`
- Grafana: `:3000`
- Health API: `/health`

Grafana uchun boshlang'ich dashboard: `deploy/grafana-dashboard.json`.

## Worker scaling

Signal stream consumerlar sonini oshirish:

```bash
docker compose up -d --scale signal-worker=3
```

Katta productionda bot UX, monitoring runtime va delivery worker alohida node poollarda yurishi kerak.
