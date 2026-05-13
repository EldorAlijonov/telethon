from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from telethon import TelegramClient
from telethon.sessions import StringSession

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings
from app.core.security import SessionCipher
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


async def _check_bot_token(bot: Bot) -> None:
    me = await asyncio.wait_for(bot.get_me(), timeout=20)
    print(f"OK bot token: @{me.username or me.id}")


async def _check_telethon_connection(api_id: int, api_hash: str) -> None:
    client = TelegramClient(StringSession(), api_id, api_hash)
    try:
        await asyncio.wait_for(client.connect(), timeout=20)
        if not client.is_connected():
            raise RuntimeError("Telethon client did not connect")
        print("OK telethon connection")
    finally:
        await client.disconnect()


async def _build_dispatcher() -> None:
    settings = get_settings()
    engine, session_factory = create_session_factory(settings.database_url)
    db = Database(session_factory)
    redis = Redis.from_url(settings.redis_url)
    storage = RedisStorage(redis)

    user_service = UserService(db, settings.default_access_days)
    keyword_service = KeywordService(db, settings.default_keywords)
    monitor_state = MonitorStateService(redis)
    cipher = SessionCipher(settings.secret_key, settings.session_encryption_key)
    telethon_auth = TelethonAuthService(settings.api_id, settings.api_hash, db, cipher, redis, settings.otp_ttl_seconds, settings.otp_max_attempts)
    signal_queue = SignalQueueService(redis, settings.signal_stream, settings.signal_retry_stream, settings.signal_dlq_stream)
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
        blacklist_ids=settings.blacklist_ids,
        dedupe_ttl=settings.signal_dedupe_ttl_seconds,
    )
    health_service = HealthService(db, redis)
    broadcast_service = BroadcastService(db, user_service)
    subscription_guard = SubscriptionGuardService(settings.mandatory_channels, settings.effective_admin_ids)

    dp = Dispatcher(storage=storage)
    dp.include_router(register_admin_handlers(user_service, health_service, broadcast_service, live_monitor_service, settings))
    dp.include_router(register_telethon_handlers(user_service, telethon_auth, subscription_guard, settings.effective_admin_ids))
    dp.include_router(register_telethon_feature_handlers(user_service, keyword_service, telethon_auth, subscription_guard, live_monitor_service))
    dp.include_router(register_user_handlers(user_service, telethon_auth, subscription_guard, settings))
    await redis.aclose()
    await engine.dispose()
    print("OK dispatcher registration")


async def main() -> None:
    settings = get_settings()
    print("OK config loaded")

    await _build_dispatcher()

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await _check_bot_token(bot)
    finally:
        await bot.session.close()

    await _check_telethon_connection(settings.api_id, settings.api_hash)
    print("Integration smoke passed")


if __name__ == "__main__":
    asyncio.run(main())
