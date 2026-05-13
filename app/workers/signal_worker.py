from __future__ import annotations

import asyncio

import structlog
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.observability import setup_sentry, start_metrics_server

logger = structlog.get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    setup_sentry(settings.sentry_dsn, settings.app_env)
    start_metrics_server(settings.metrics_port + 1)
    redis = Redis.from_url(settings.redis_url, decode_responses=True)

    group = "signal-workers"
    consumer = "worker-1"
    try:
        await redis.xgroup_create(settings.signal_stream, group, id="0", mkstream=True)
    except Exception:
        pass

    logger.info("signal_worker_started", stream=settings.signal_stream, group=group)
    try:
        while True:
            messages = await redis.xreadgroup(group, consumer, {settings.signal_stream: ">"}, count=20, block=5000)
            if not messages:
                continue
            for stream, items in messages:
                for message_id, payload in items:
                    # Hozir bot asosiy jarayonda signalni yuboradi; worker kelajakdagi fan-out,
                    # retry va AI enrichment pipeline uchun stream ack qiladi.
                    logger.info("signal_event_consumed", stream=stream, message_id=message_id, signal_id=payload.get("signal_id"))
                    await redis.xack(settings.signal_stream, group, message_id)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
