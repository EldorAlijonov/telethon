from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import load_config
from app.database import Database
from app.handlers.admin import register_admin_handlers
from app.handlers.telethon import register_telethon_handlers
from app.handlers.telethon_features import register_telethon_feature_handlers
from app.handlers.user import register_user_handlers
from app.logging_config import setup_logging
from app.services.keyword_service import KeywordService
from app.services.live_monitor_service import LiveMonitorService
from app.services.monitor_service import MonitorService
from app.services.telethon_service import TelethonService
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

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

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(register_admin_handlers(user_service, config))
    dp.include_router(register_telethon_handlers(user_service, telethon_service, config))
    dp.include_router(register_telethon_feature_handlers(user_service, keyword_service, monitor_service, live_monitor_service))
    dp.include_router(register_user_handlers(user_service, config))

    logger.info('Bot ishga tushdi')
    try:
        await dp.start_polling(bot)
    finally:
        logger.info("Bot to'xtatilmoqda")
        await live_monitor_service.stop_all()
        await telethon_service.cancel_all()
        await bot.session.close()
