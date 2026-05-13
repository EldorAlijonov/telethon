from __future__ import annotations

from redis.asyncio import Redis


class SignalQueueService:
    def __init__(self, redis: Redis, stream_name: str, retry_stream: str, dlq_stream: str):
        self.redis = redis
        self.stream_name = stream_name
        self.retry_stream = retry_stream
        self.dlq_stream = dlq_stream

    async def publish_signal(self, payload: dict[str, str | int | float | None]) -> str:
        normalized = {key: "" if value is None else str(value) for key, value in payload.items()}
        return await self.redis.xadd(self.stream_name, normalized, maxlen=100_000, approximate=True)

    async def publish_retry(self, payload: dict[str, str | int | float | None]) -> str:
        normalized = {key: "" if value is None else str(value) for key, value in payload.items()}
        return await self.redis.xadd(self.retry_stream, normalized, maxlen=50_000, approximate=True)

    async def publish_dead_letter(self, payload: dict[str, str | int | float | None]) -> str:
        normalized = {key: "" if value is None else str(value) for key, value in payload.items()}
        return await self.redis.xadd(self.dlq_stream, normalized, maxlen=50_000, approximate=True)
