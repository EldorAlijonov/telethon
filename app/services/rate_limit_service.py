from __future__ import annotations

from redis.asyncio import Redis


class RateLimitService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, window_seconds)
        return count <= limit
