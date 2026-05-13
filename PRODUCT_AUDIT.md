# Product Audit

## A. Loyiha haqida tushuncha

Mavjud loyiha Telegram bot bo'lib, foydalanuvchi telefon raqamini yuboradi, admin tasdiqlaydi, foydalanuvchi Telethon orqali Telegram akkauntini ulaydi va chatlardagi kalit so'zlar bo'yicha signal oladi.

## B. Mavjud loyiha auditi

- `main.py`: faqat `app.main` ni ishga tushiradi. Muammo yo'q, lekin deployment entrypoint minimal.
- `app/config.py`: `.env` ni dataclass bilan o'qiydi. `ADMIN_ID` bitta admin bilan cheklangan, secret validation yo'q.
- `app/database.py`: SQLite bilan sinxron connection ochadi. Async bot ichida blocking I/O, migration yo'q.
- `app/services/user_service.py`: user approval, expiry, Telethon sessionni bitta `users` jadvalida saqlaydi. Session plaintext, transaction va domain ajratish yo'q.
- `app/services/keyword_service.py`: keyword CRUD bor, lekin kodirovka buzilgan matnlar va umumiy `except Exception` ishlatilgan.
- `app/services/live_monitor_service.py`: realtime monitoring bor, lekin har user uchun alohida Telethon client va memory cache ishlaydi. Restartdan keyin state yo'qoladi, dedupe DB/Redis bilan mustahkamlanmagan.
- `app/services/subscription_service.py`: mandatory channel guard qo'shildi. Bot API `getChatMember` ishlashi uchun bot kanalga kira olishi kerak.
- `app/services/broadcast_service.py`: broadcast job DBga yoziladi va natijasi hisoblanadi. Katta masshtabda alohida queue workerga chiqarish tavsiya etiladi.
- `app/services/queue_service.py`: Redis Streams orqali signal event publish qiladi. Bu retry/DLQ va parallel consumerlarga yo'l ochadi.
- `app/core/observability.py`: Prometheus metriclar va Sentry init markazlashtirildi.
- `app/handlers/*`: biznes logika handler ichiga aralashgan, admin/user UX ishlaydi, lekin matnlar mojibake bo'lgan.
- `tests/*`: asosiy service lifecycle tekshirilgan, lekin production DB, Redis, migration, security flow qamrovi yo'q.
- Docker/Alembic/CI/systemd/backup fayllari mavjud emas edi.

## C. Topilgan kritik muammolar

| Muammo | Joylashuv | Daraja | Ta'sir | To'g'ri yechim |
|---|---|---:|---|---|
| Telethon session plaintext | `users.telethon_session` | Critical | Session o'g'irlansa akkaunt egallanadi | `telegram_sessions.encrypted_session` + Fernet encryption |
| SQLite blocking I/O | `app/database.py`, service qatlamlari | High | Bot event loop sekinlashadi, scale ko'tarmaydi | PostgreSQL async SQLAlchemy |
| Migration yo'q | repo bo'ylab | High | Schema drift va deploy xatolari | Alembic |
| Redis/FSM storage yo'q | `app/main.py` | High | Restartda FSM va dedupe yo'qoladi | RedisStorage + Redis dedupe |
| Kodirovka buzilgan UI | handlers/keyboards/utils | Medium | Uzbek UX yomon, tugmalar mos kelmasligi mumkin | UTF-8 matnlarni qayta yozish |
| Admin faqat bitta ID | `app/config.py` | Medium | Operatsion boshqaruv cheklangan | `ADMIN_IDS` ro'yxati |
| Generic exception swallow | monitoring va admin notify | Medium | Xatolar ko'rinmaydi | Structured logging va audit log |
| Dedupe faqat memory | `LiveMonitorService.last_signals` | High | Restartda duplicate signal | Redis NX TTL + DB unique constraint |
| Deployment yo'q | repo | High | Productionda qo'lda va xatoga moyil ishga tushirish | Docker Compose + systemd |
| Mandatory subscription yo'q | user/telethon flow | Medium | Kanalga bog'langan access enforce qilinmaydi | `SubscriptionGuardService` |
| Broadcast audit trail yo'q | admin handler | Medium | Admin broadcastlari kuzatilmaydi | `broadcast_jobs` + audit log |
| Admin monitoring control yo'q | admin panel | Medium | Muammoli monitoringni tez to'xtatish qiyin | active runtime stats + force stop |
| Signal delivery audit yo'q | signal flow | High | Yuborilgan/yuborilmagan signalni tiklash qiyin | `signal_deliveries` jadvali |
| Observability yo'q | runtime/deploy | High | Incident root-cause topish qiyin | Prometheus, Grafana, Sentry, health API |

## D. Yangi professional arxitektura

Qatlamlar:

- `core`: config, logging, security
- `db`: SQLAlchemy engine, session, models
- `repositories`: DB CRUD va query boundary
- `services`: biznes qoidalar, Telethon auth, monitoring state, health
- `services`: broadcast, mandatory subscription guard va monitoring runtime control
- `handlers`: aiogram user/admin/Telethon flows
- `alembic`: migration lifecycle
- `deploy`: systemd va production yordamchi fayllar
- `workers`: Redis Streams consumerlar
- `api`: health endpoint

## E. Yangi folder structure

```text
app/
  core/
  db/
  repositories/
  services/
  handlers/
  states/
  keyboards.py
alembic/
deploy/
scripts/
tests/
Dockerfile
docker-compose.yml
```

## F. Qayta yozilgan codebase haqida

Yangi kod PostgreSQL, Redis, encrypted session, async repository/service pattern va Alembic migration bilan ishlaydi. Eski biznes logika saqlandi: ro'yxatdan o'tish, admin approval, Telethon login, keyword CRUD, realtime signal.
Qo'shimcha ravishda broadcast job persistence, mandatory subscription enforcement va admin monitoring control qo'shildi.

## G. Database schema

Jadvallar: `users`, `approvals`, `subscriptions`, `keywords`, `monitored_chats`, `telegram_sessions`, `signals`, `signal_deliveries`, `broadcast_jobs`, `audit_logs`, `settings`, `rate_limits`, `suspicious_activities`.

Muhim constraintlar:

- `users.tg_id` unique
- `keywords(user_id, keyword)` unique
- `signals(user_id, chat_id, message_id, keyword)` unique
- `signal_deliveries(signal_id, recipient_tg_id)` unique
- session `user_id` unique

## H. Security improvements

- Session encryption
- Admin ID whitelist
- OTP attempt limit Redis orqali
- Mandatory subscription guard
- Broadcast audit trail
- Delivery audit trail
- Sentry error tracking
- Sensitive log masking
- Safe transactions
- User isolation repository querylarda `user_id` orqali

## I. Performance improvements

- Async DB
- Redis FSM va dedupe
- DB indexes
- Event handlerda tez keyword match
- Signal duplicate oldini olish uchun Redis `SET NX EX`
- Broadcast yuborishda kichik delay Bot API flood riskini kamaytiradi
- Redis Streams signal pipeline parallel workerlarga tayyor

## J. Deployment guide

Docker Compose bilan `docker compose up -d --build`. Ubuntu uchun `deploy/telegram-monitor.service` systemd unit ishlatiladi. Migratsiya startda `scripts/start.sh` orqali `alembic upgrade head` bilan bajariladi. Batafsil: `DEPLOYMENT.md`.

## K. Testing guide

```bash
python -m compileall app
python -m pytest -q
```

## L. O'zgartirilgan qismlar

SQLite olib tashlandi, SQLAlchemy/Alembic qo'shildi, handlerlar async service qatlamiga o'tkazildi, UI matnlari tozalandi, Docker va systemd qo'shildi, session encryption qo'shildi. Mandatory subscription, broadcast persistence, CI workflow va monitoring control qo'shildi.

## M. Qo'shimcha tavsiyalar

- Monitoringni 1000+ user uchun alohida worker shardlarga ajrating.
- Broadcastni keyingi bosqichda Celery/RQ worker orqali yuboring.
- Prometheus metrics endpoint va Grafana dashboard qo'shing.
- Mandatory channel subscription uchun private kanallarda botni admin qiling.
