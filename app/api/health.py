from __future__ import annotations

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import Database, create_session_factory

app = FastAPI(title="Telegram Monitor Health API")


@app.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    engine, session_factory = create_session_factory(settings.database_url)
    redis = Redis.from_url(settings.redis_url)
    result = {"status": "ok", "database": "ok", "redis": "ok"}
    try:
        async with Database(session_factory).session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        result["status"] = "degraded"
        result["database"] = type(exc).__name__
    try:
        await redis.ping()
    except Exception as exc:
        result["status"] = "degraded"
        result["redis"] = type(exc).__name__
    finally:
        await redis.aclose()
        await engine.dispose()
    return result
