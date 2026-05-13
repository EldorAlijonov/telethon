# Telegram Monitor SaaS Bot

Bu loyiha Telegram chatlarida kalit so'zlarni realtime kuzatish, foydalanuvchilarni admin tasdig'i bilan boshqarish va Telethon session orqali signal yuborish uchun production-ready arxitekturaga qayta qurildi.

## Asosiy imkoniyatlar

- aiogram v3 asosidagi bot flow
- Telethon OTP va 2FA login
- PostgreSQL + SQLAlchemy 2.x async
- Alembic migratsiyalar
- Redis FSM storage, rate-limit va dedupe cache
- Shifrlangan Telethon session storage
- Admin panel: pending/approved/blocked users, statistika, broadcast, health
- Admin monitoring control: faol monitoringlar va majburiy stop
- Mandatory channel subscription check
- User panel: ro'yxatdan o'tish, status, keyword CRUD, monitoring on/off
- Docker Compose: bot, PostgreSQL, Redis
- Structured JSON logging
- CI workflow va startup/migration scriptlar
- Redis Streams signal queue
- Prometheus, Grafana, Sentry, Nginx va health API

## Ishga tushirish

1. `.env.example` asosida `.env` ni tayyorlang.
2. `SECRET_KEY` ni kuchli random qiymatga almashtiring.
3. Docker orqali ko'taring:

```bash
docker compose up -d --build
```

Bot konteyneri start paytida:

```bash
sh scripts/start.sh
```

Script ichida:

```bash
alembic upgrade head
python main.py
```

komandalarini bajaradi.

## Lokal development

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
docker compose up -d postgres redis
alembic upgrade head
python main.py
```

## Test

```bash
python -m pytest -q
python -m compileall app
```

## Mandatory subscription

Majburiy kanal obunalarini `.env` ichida vergul bilan yozing:

```env
MANDATORY_CHANNELS=@kanal1,@kanal2
```

Bot ushbu kanallarda `getChatMember` ishlata olishi kerak. Private kanal bo'lsa, botni kanalga admin qilib qo'ying.

## Ubuntu production deployment

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin git
sudo mkdir -p /opt/telegram-monitor
sudo cp -r . /opt/telegram-monitor
cd /opt/telegram-monitor
sudo cp .env.example .env
sudo nano .env
sudo docker compose up -d --build
```

Systemd orqali boshqarish:

```bash
sudo cp deploy/telegram-monitor.service /etc/systemd/system/telegram-monitor.service
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-monitor
sudo journalctl -u telegram-monitor -f
```

## Backup

```bash
sh scripts/backup_postgres.sh
```

Backup fayllari `./backups` papkasiga yoziladi.

## Observability

- Bot metrics: `http://localhost:9108`
- Worker metrics: `http://localhost:9109`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`
- Health API: `http://localhost:8080/health`

Sentry uchun `.env`:

```env
SENTRY_DSN=https://...
```

## Queue

Signal eventlar Redis Streams orqali publish qilinadi:

- `signals:v1`
- `signals:retry:v1`
- `signals:dlq:v1`

Load smoke:

```bash
python scripts/load_signal_queue.py
```

## Xavfsizlik eslatmalari

- `.env` Gitga qo'shilmasin.
- `BOT_TOKEN`, `API_HASH`, `SECRET_KEY` va sessionlar logga chiqarilmasin.
- Production uchun `SECRET_KEY` ni almashtiring va sirlarni server secret managerda saqlang.
- Redis va PostgreSQL tashqi internetga ochilmasin.
- Admin ID ro'yxatini `ADMIN_IDS` orqali boshqaring.

## Muhim audit natijalari

Oldingi loyiha SQLite va sinxron DB calllardan foydalangan, Telethon sessionni plaintext saqlagan, Docker/Alembic/Redis yo'q edi va ko'p Uzbek UI matnlari kodirovka buzilishi sabab noto'g'ri ko'rinardi. Yangi arxitektura bu risklarni production talablariga yaqinlashtirdi.
