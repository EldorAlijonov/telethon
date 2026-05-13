# Massive-Scale Architecture

## Maqsad

Tizim Telegram monitoringni 10,000+ user, 100,000+ monitored chat va millionlab xabar/kun masshtabiga tayyorlash uchun qatlamlarga ajratildi.

## Runtime komponentlar

- `bot`: aiogram polling, user/admin UX, Telethon login, monitoring runtime.
- `signal-worker`: Redis Streams consumer. Hozir eventlarni ack qiladi, keyingi bosqichda retry/fan-out/AI enrichment shu yerga ko'chadi.
- `health-api`: `/health` endpoint.
- `postgres`: persistent relational data.
- `redis`: FSM, dedupe, monitoring state, streams.
- `nginx`: health/API reverse proxy.
- `prometheus`: metrics scrape.
- `grafana`: dashboard.

## Event-driven signal pipeline

1. Telethon `NewMessage` event oladi.
2. Blacklist, left chat, bot sender va duplicate filter ishlaydi.
3. Keyword match topiladi.
4. Signal PostgreSQLga yoziladi.
5. `signal_deliveries` pending yoziladi.
6. Event Redis Streams `signals:v1` ga publish qilinadi.
7. Bot signalni userga yuboradi.
8. Delivery status `delivered` yoki `failed` bo'ladi.
9. Xato bo'lsa `signals:retry:v1` ga publish qilinadi.

## Nega Redis Streams

- At-least-once delivery modeli.
- Consumer group orqali parallel workerlar.
- Retry/DLQ pattern.
- Redis allaqachon FSM/dedupe uchun ishlatilgani sabab operatsion soddalik yuqori.

## Scaling strategiya

- Bot UX va monitoring workerlarni alohida deploymentlarga ajratish.
- Telethon monitoringni user ID hash bo'yicha shardlash.
- Redis Streams consumer group sonini oshirish.
- PostgreSQL read-heavy querylar uchun index va keyset pagination.
- Broadcast va signal deliveryni alohida worker poolga chiqarish.

## AI-ready pipeline

Signal event payloadi Redis Stream orqali o'tgani uchun kelajakda quyidagi bosqichlar qo'shiladi:

- NLP classification
- Spam/moderation scoring
- Fuzzy matching
- Intent extraction
- Lead quality scoring

Bu modullar signal detectionni buzmasdan stream consumer sifatida ulanadi.
