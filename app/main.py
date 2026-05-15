from __future__ import annotations

import asyncio

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.core.local_redis import LocalRedis
from app.core.logging import setup_logging
from app.core.observability import setup_sentry, start_metrics_server
from app.core.security import SessionCipher
from app.core.single_instance import SingleInstanceLock
from app.db.session import Database, create_session_factory
from app.handlers.admin import register_admin_handlers
from app.handlers.telethon import register_telethon_handlers
from app.handlers.telethon_features import register_telethon_feature_handlers
from app.handlers.user import register_user_handlers
from app.services.broadcast_service import BroadcastService
from app.services.health_service import HealthService
from app.services.keyword_service import KeywordService
from app.services.live_monitor_service import LiveMonitorService
from app.services.monitor_service import MonitorStateService
from app.services.queue_service import SignalQueueService
from app.services.subscription_service import SubscriptionGuardService
from app.services.telethon_service import TelethonAuthService
from app.services.user_service import UserService

logger = structlog.get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    instance_lock = SingleInstanceLock(settings.app_lock_port)
    instance_lock.acquire()
    setup_sentry(settings.sentry_dsn, settings.app_env)
    start_metrics_server(settings.metrics_port)

    engine, session_factory = create_session_factory(settings.database_url)
    db = Database(session_factory)
    redis = Redis.from_url(settings.redis_url, decode_responses=False)
    try:
        await redis.ping()
    except RedisError:
        if settings.is_production:
            raise
        logger.warning("redis_unavailable_using_local_memory_fallback")
        await redis.aclose()
        redis = LocalRedis()
    storage = RedisStorage(redis)

    cipher = SessionCipher(settings.secret_key, settings.session_encryption_key)
    user_service = UserService(db, settings.default_access_days)
    keyword_service = KeywordService(db, settings.default_keywords)
    monitor_state = MonitorStateService(redis)
    signal_queue = SignalQueueService(redis, settings.signal_stream, settings.signal_retry_stream, settings.signal_dlq_stream)
    telethon_auth = TelethonAuthService(
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        db=db,
        cipher=cipher,
        redis=redis,
        otp_ttl=settings.otp_ttl_seconds,
        max_attempts=settings.otp_max_attempts,
    )
    live_monitor_service = LiveMonitorService(
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        db=db,
        redis=redis,
        auth_service=telethon_auth,
        user_service=user_service,
        keyword_service=keyword_service,
        monitor_state=monitor_state,
        signal_queue=signal_queue,
        blacklist_ids=set(settings.blacklist_ids),
        dedupe_ttl=settings.signal_dedupe_ttl_seconds,
    )
    health_service = HealthService(db, redis)
    broadcast_service = BroadcastService(db, user_service)
    subscription_guard = SubscriptionGuardService(settings.mandatory_channels, settings.effective_admin_ids)

    health = await health_service.check()
    if health["database"] != "ok" or health["redis"] != "ok":
        raise RuntimeError(
            "Bot start bo'lishi uchun PostgreSQL va Redis ishlashi kerak. "
            f"Database={health['database']}; Redis={health['redis']}. "
            "Lokal ishga tushirish: docker compose up -d postgres redis && alembic upgrade head"
        )

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp.include_router(register_admin_handlers(user_service, health_service, broadcast_service, live_monitor_service, settings))
    dp.include_router(register_telethon_handlers(user_service, telethon_auth, subscription_guard, settings.effective_admin_ids))
    dp.include_router(register_telethon_feature_handlers(user_service, keyword_service, telethon_auth, subscription_guard, live_monitor_service))
    dp.include_router(register_user_handlers(user_service, telethon_auth, subscription_guard, settings))

    logger.info("bot_started")
    monitor_restore_task = asyncio.create_task(live_monitor_service.restore_default_monitoring(bot), name="monitor:restore")
    try:
        while True:
            try:
                await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
                break
            except TelegramNetworkError as exc:
                logger.warning("telegram_network_error_retrying", error=str(exc))
                await asyncio.sleep(10)
    finally:
        logger.info("bot_stopping")
        monitor_restore_task.cancel()
        await asyncio.gather(monitor_restore_task, return_exceptions=True)
        await live_monitor_service.stop_all()
        await telethon_auth.cancel_all()
        await bot.session.close()
        await redis.aclose()
        await engine.dispose()
        instance_lock.release()


if __name__ == "__main__":
    asyncio.run(main())
