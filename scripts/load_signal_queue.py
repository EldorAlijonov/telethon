from __future__ import annotations

import asyncio
import time

from redis.asyncio import Redis

from app.core.config import get_settings
from app.services.queue_service import SignalQueueService


async def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    queue = SignalQueueService(redis, settings.signal_stream, settings.signal_retry_stream, settings.signal_dlq_stream)
    started = time.perf_counter()
    total = 1000
    for i in range(total):
        await queue.publish_signal({"signal_id": i, "tg_id": 1, "chat_id": -100, "keyword": "load-test"})
    elapsed = time.perf_counter() - started
    print(f"{total} stream event yozildi. elapsed={elapsed:.2f}s rate={total / elapsed:.1f}/s")
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
