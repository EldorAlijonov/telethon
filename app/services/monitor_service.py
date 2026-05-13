from __future__ import annotations

from redis.asyncio import Redis


class MonitorStateService:
    def __init__(self, redis: Redis):
        self.redis = redis

    def _key(self, tg_id: int) -> str:
        return f"monitor:enabled:{tg_id}"

    async def is_enabled(self, tg_id: int) -> bool:
        return await self.redis.get(self._key(tg_id)) == b"1"

    async def set_enabled(self, tg_id: int, enabled: bool) -> None:
        if enabled:
            await self.redis.set(self._key(tg_id), "1")
        else:
            await self.redis.delete(self._key(tg_id))


MonitorService = MonitorStateService
