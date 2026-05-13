from __future__ import annotations

from sqlalchemy import text
from redis.asyncio import Redis

from app.db.session import Database


class HealthService:
    def __init__(self, db: Database, redis: Redis):
        self.db = db
        self.redis = redis

    async def check(self) -> dict[str, str]:
        result = {"database": "ok", "redis": "ok"}
        try:
            async with self.db.session() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            result["database"] = f"error: {type(exc).__name__}"
        try:
            await self.redis.ping()
        except Exception as exc:
            result["redis"] = f"error: {type(exc).__name__}"
        return result
