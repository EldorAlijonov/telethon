from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from telethon import TelegramClient
from telethon.sessions import StringSession

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.config import load_config
from app.database import Database
from app.handlers.admin import register_admin_handlers
from app.handlers.telethon import register_telethon_handlers
from app.handlers.telethon_features import register_telethon_feature_handlers
from app.handlers.user import register_user_handlers
from app.services.keyword_service import KeywordService
from app.services.live_monitor_service import LiveMonitorService
from app.services.monitor_service import MonitorService
from app.services.telethon_service import TelethonService
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


def _build_dispatcher() -> None:
    config = load_config()
    db = Database(config.db_path)
    user_service = UserService(db)
    telethon_service = TelethonService(api_id=config.api_id, api_hash=config.api_hash)
    keyword_service = KeywordService(db, default_keywords=config.default_keywords)
    monitor_service = MonitorService(db)
    live_monitor_service = LiveMonitorService(
        api_id=config.api_id,
        api_hash=config.api_hash,
        user_service=user_service,
        keyword_service=keyword_service,
        monitor_service=monitor_service,
        blacklist_ids=config.blacklist_ids,
    )

    dp = Dispatcher()
    dp.include_router(register_admin_handlers(user_service, config))
    dp.include_router(register_telethon_handlers(user_service, telethon_service, config))
    dp.include_router(register_telethon_feature_handlers(user_service, keyword_service, monitor_service, live_monitor_service))
    dp.include_router(register_user_handlers(user_service, config))
    print("OK dispatcher registration")


async def main() -> None:
    config = load_config()
    print("OK config loaded")

    Database(config.db_path)
    print("OK database initialized")

    _build_dispatcher()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await _check_bot_token(bot)
    finally:
        await bot.session.close()

    await _check_telethon_connection(config.api_id, config.api_hash)
    print("Integration smoke passed")


if __name__ == "__main__":
    asyncio.run(main())
