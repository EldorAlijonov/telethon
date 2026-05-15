from __future__ import annotations

import asyncio
import html
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Any

import structlog
from aiogram import Bot
from redis.asyncio import Redis
from telethon import TelegramClient, events
from telethon.errors import AuthKeyUnregisteredError, FloodWaitError
from telethon.sessions import StringSession

from app.db.models import AuditAction
from app.db.session import Database
from app.core.observability import ACTIVE_MONITORS, SIGNAL_LATENCY, SIGNALS_DELIVERED, SIGNALS_FAILED, SIGNALS_DETECTED, TELETHON_EVENTS
from app.repositories.audit_repository import AuditRepository
from app.repositories.delivery_repository import SignalDeliveryRepository
from app.repositories.monitor_repository import MonitorRepository
from app.repositories.user_repository import UserRepository
from app.services.keyword_service import KeywordService
from app.services.monitor_service import MonitorStateService
from app.services.queue_service import SignalQueueService
from app.services.telethon_service import TelethonAuthService
from app.services.user_service import UserService
from app.utils import to_tashkent_time

logger = structlog.get_logger(__name__)


class TelethonSessionInvalidError(Exception):
    pass


@dataclass
class MonitorRuntime:
    client: TelegramClient
    task: asyncio.Task
    handler: Any
    event_tasks: set[asyncio.Task] = field(default_factory=set)


class LiveMonitorService:
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        db: Database,
        redis: Redis,
        auth_service: TelethonAuthService,
        user_service: UserService,
        keyword_service: KeywordService,
        monitor_state: MonitorStateService,
        signal_queue: SignalQueueService,
        blacklist_ids: set[int],
        dedupe_ttl: int,
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.db = db
        self.redis = redis
        self.auth_service = auth_service
        self.user_service = user_service
        self.keyword_service = keyword_service
        self.monitor_state = monitor_state
        self.signal_queue = signal_queue
        self.blacklist_ids = blacklist_ids
        self.dedupe_ttl = dedupe_ttl
        self.runtimes: dict[int, MonitorRuntime] = {}

    def stats(self) -> dict[str, object]:
        return {
            "active_count": len(self.runtimes),
            "active_user_ids": sorted(self.runtimes.keys()),
        }

    async def start_monitoring(self, tg_id: int, bot: Bot) -> tuple[bool, str]:
        if tg_id in self.runtimes:
            await self.monitor_state.set_enabled(tg_id, True)
            return True, "Kuzatish allaqachon yoqilgan."
        if not await self.user_service.is_allowed(tg_id):
            return False, "Foydalanish muddati tugagan yoki hisob tasdiqlanmagan."
        session_data = await self.auth_service.get_plain_session(tg_id)
        if not session_data:
            return False, "Avval Telegram akkauntingizni ulang."

        _, plain_session = session_data
        await self.keyword_service.ensure_defaults(tg_id)
        client = TelegramClient(StringSession(plain_session), self.api_id, self.api_hash)
        try:
            await client.connect()
            me = await client.get_me()
        except AuthKeyUnregisteredError:
            await client.disconnect()
            await self.auth_service.revoke_session(tg_id)
            return False, "Telegram sessiya eskirgan. Qayta ulaning."

        own_id = int(me.id) if me else None
        if own_id:
            self.blacklist_ids.add(own_id)

        async def handler(event):
            runtime = self.runtimes.get(tg_id)
            task = asyncio.create_task(
                self._handle_event_safe(tg_id=tg_id, bot=bot, event=event, own_id=own_id),
                name=f"signal:{tg_id}:{getattr(getattr(event, 'message', None), 'id', 0) or 0}",
            )
            if runtime:
                runtime.event_tasks.add(task)
                task.add_done_callback(runtime.event_tasks.discard)

        client.add_event_handler(handler, events.NewMessage())
        await self.monitor_state.set_enabled(tg_id, True)

        async def runner():
            try:
                await client.run_until_disconnected()
            except FloodWaitError as exc:
                await asyncio.sleep(getattr(exc, "seconds", 5))
            except Exception as exc:
                logger.warning("monitor_runtime_stopped", tg_id=tg_id, error=type(exc).__name__)
            finally:
                await self.monitor_state.set_enabled(tg_id, False)
                self.runtimes.pop(tg_id, None)

        task = asyncio.create_task(runner(), name=f"monitor:{tg_id}")
        self.runtimes[tg_id] = MonitorRuntime(client=client, task=task, handler=handler)
        ACTIVE_MONITORS.set(len(self.runtimes))
        async with self.db.session() as session:
            await AuditRepository(session).write(AuditAction.monitoring_started, target_tg_id=tg_id)
        return True, "Kuzatish yoqildi."

    async def _handle_event_safe(self, tg_id: int, bot: Bot, event, own_id: int | None) -> None:
        started = monotonic()
        try:
            await self._handle_event(tg_id=tg_id, bot=bot, event=event, own_id=own_id)
        except Exception as exc:
            logger.exception("signal_event_processing_failed", tg_id=tg_id, error=type(exc).__name__)
        finally:
            elapsed = monotonic() - started
            if elapsed >= 2:
                logger.warning("slow_signal_processing", tg_id=tg_id, elapsed_seconds=round(elapsed, 3))

    async def _handle_event(self, tg_id: int, bot: Bot, event, own_id: int | None) -> None:
        if getattr(event, "out", False):
            return
        TELETHON_EVENTS.inc()
        processing_started = monotonic()
        chat_id = int(getattr(event, "chat_id", 0) or 0)
        sender_id = getattr(event, "sender_id", None)
        if not chat_id or chat_id in self.blacklist_ids or (sender_id and int(sender_id) in self.blacklist_ids) or sender_id == own_id:
            return
        if not await self.monitor_state.is_enabled(tg_id):
            return
        if await self._is_chat_blocked(tg_id, chat_id):
            return
        text = (event.raw_text or "").strip()
        if not text:
            return
        keywords = await self.keyword_service.list_keywords(tg_id)
        lowered = text.lower()
        keyword = next((item for item in keywords if item in lowered), None)
        if not keyword:
            return

        message_id = int(getattr(event.message, "id", 0) or 0)
        dedupe_key = f"signal:dedupe:{tg_id}:{chat_id}:{message_id}:{keyword}"
        if not await self.redis.set(dedupe_key, "1", ex=self.dedupe_ttl, nx=True):
            return

        sender, chat = await asyncio.gather(event.get_sender(), event.get_chat())
        if getattr(sender, "bot", False) or self._inactive_chat(chat):
            return

        chat_title = getattr(chat, "title", None) or "Noma'lum chat"
        sender_profile = self._sender_profile(sender)
        sender_name = sender_profile["name"]
        link = self._message_link(chat, chat_id, message_id)
        message_at = getattr(event.message, "date", None) or datetime.now(UTC)
        delivered = False
        delivery_error: str | None = None

        try:
            await bot.send_message(
                tg_id,
                self._signal_text(0, keyword, text, chat_title, sender_profile, message_at, link),
                disable_web_page_preview=True,
            )
            delivered = True
            SIGNALS_DELIVERED.inc()
        except Exception as exc:
            delivery_error = type(exc).__name__
            SIGNALS_FAILED.inc()

        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return
            signal = await MonitorRepository(session).save_signal(
                user_id=user.id,
                chat_id=chat_id,
                message_id=message_id,
                keyword=keyword,
                matched_text=text[:4000],
                source_chat=chat_title,
                sender_info=sender_name,
                message_link=link,
                message_at=message_at,
            )
            if not signal:
                return
            await SignalDeliveryRepository(session).create_pending(signal.id, tg_id)
            await AuditRepository(session).write(AuditAction.signal_sent, target_tg_id=tg_id, details={"keyword": keyword, "chat_id": chat_id})
            signal_id = signal.id

        SIGNALS_DETECTED.inc()
        await self.signal_queue.publish_signal(
            {
                "signal_id": signal_id,
                "tg_id": tg_id,
                "chat_id": chat_id,
                "message_id": message_id,
                "keyword": keyword,
                "message_link": link,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        if delivered:
            async with self.db.session() as session:
                delivery_repo = SignalDeliveryRepository(session)
                delivery = await delivery_repo.get_by_signal_recipient(signal_id, tg_id)
                if delivery:
                    await delivery_repo.mark_delivered(delivery)
        else:
            await self.signal_queue.publish_retry(
                {
                    "signal_id": signal_id,
                    "tg_id": tg_id,
                    "error": delivery_error,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
            async with self.db.session() as session:
                delivery_repo = SignalDeliveryRepository(session)
                delivery = await delivery_repo.get_by_signal_recipient(signal_id, tg_id)
                if delivery:
                    await delivery_repo.mark_failed(delivery, delivery_error or "UnknownError")
        SIGNAL_LATENCY.observe(monotonic() - processing_started)

    async def stop_monitoring(self, tg_id: int) -> None:
        await self.monitor_state.set_enabled(tg_id, False)
        runtime = self.runtimes.pop(tg_id, None)
        if runtime:
            try:
                runtime.client.remove_event_handler(runtime.handler)
                for task in list(runtime.event_tasks):
                    task.cancel()
                if runtime.event_tasks:
                    await asyncio.gather(*runtime.event_tasks, return_exceptions=True)
                await runtime.client.disconnect()
            finally:
                runtime.task.cancel()
        ACTIVE_MONITORS.set(len(self.runtimes))
        async with self.db.session() as session:
            await AuditRepository(session).write(AuditAction.monitoring_stopped, target_tg_id=tg_id)

    async def stop_all(self) -> None:
        await asyncio.gather(*(self.stop_monitoring(tg_id) for tg_id in list(self.runtimes)), return_exceptions=True)

    async def list_dialog_titles(self, tg_id: int) -> list[str]:
        session_data = await self.auth_service.get_plain_session(tg_id)
        if not session_data:
            return []
        _, plain_session = session_data
        client = self.runtimes.get(tg_id).client if tg_id in self.runtimes else TelegramClient(StringSession(plain_session), self.api_id, self.api_hash)
        temporary = tg_id not in self.runtimes
        if temporary:
            await client.connect()
        titles: list[str] = []
        try:
            async for dialog in client.iter_dialogs(limit=100):
                entity = getattr(dialog, "entity", None)
                if getattr(dialog, "is_user", False) or self._inactive_chat(entity) or int(dialog.id) in self.blacklist_ids:
                    continue
                titles.append(dialog.name or "Noma'lum chat")
        except AuthKeyUnregisteredError as exc:
            await self.auth_service.revoke_session(tg_id)
            raise TelethonSessionInvalidError("Session invalid") from exc
        finally:
            if temporary:
                await client.disconnect()
        return titles

    async def block_chat(self, tg_id: int, chat_id: int, title: str | None = None, username: str | None = None) -> str:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return "Hisob topilmadi."
            await MonitorRepository(session).upsert_chat(user.id, chat_id, title or "Noma'lum chat", username, active=False)
        safe_title = html.escape(title or username or str(chat_id))
        return f"Chat bloklandi. Endi bu chatdan signal kelmaydi.\nChat: {safe_title}\nID: <code>{chat_id}</code>"

    async def block_chat_by_username(self, tg_id: int, username: str) -> str:
        session_data = await self.auth_service.get_plain_session(tg_id)
        if not session_data:
            return "Avval Telegram akkauntingizni ulang."
        _, plain_session = session_data
        client = self.runtimes.get(tg_id).client if tg_id in self.runtimes else TelegramClient(StringSession(plain_session), self.api_id, self.api_hash)
        temporary = tg_id not in self.runtimes
        if temporary:
            await client.connect()
        try:
            entity = await client.get_entity(username)
        except AuthKeyUnregisteredError as exc:
            await self.auth_service.revoke_session(tg_id)
            raise TelethonSessionInvalidError("Session invalid") from exc
        except Exception:
            return "Chat topilmadi. @username yoki guruhdan forward qilingan xabar yuboring."
        finally:
            if temporary:
                await client.disconnect()
        chat_id = int(getattr(entity, "id", 0) or 0)
        if getattr(entity, "broadcast", False) or getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False):
            chat_id = int(f"-100{chat_id}")
        title = getattr(entity, "title", None) or getattr(entity, "username", None) or username
        entity_username = getattr(entity, "username", None)
        return await self.block_chat(tg_id, chat_id, title, entity_username)

    async def list_blocked_chats(self, tg_id: int) -> list[tuple[int, str]]:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return []
            chats = await MonitorRepository(session).list_blocked_chats(user.id)
        return [(chat.chat_id, chat.title or (f"@{chat.username}" if chat.username else str(chat.chat_id))) for chat in chats]

    async def unblock_chat(self, tg_id: int, chat_id: int) -> str:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return "Hisob topilmadi."
            chat = await MonitorRepository(session).unblock_chat(user.id, chat_id)
            if not chat:
                return "Chat bloklangan ro'yxatdan topilmadi."
            title = chat.title or (f"@{chat.username}" if chat.username else str(chat.chat_id))
        safe_title = html.escape(title)
        return f"Chat blokdan chiqarildi.\nChat: {safe_title}\nID: <code>{chat_id}</code>"

    async def _is_chat_blocked(self, tg_id: int, chat_id: int) -> bool:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return False
            return await MonitorRepository(session).is_chat_blocked(user.id, chat_id)

    @staticmethod
    def _inactive_chat(chat: Any) -> bool:
        return bool(getattr(chat, "left", False) or getattr(chat, "deactivated", False) or getattr(chat, "kicked", False))

    @staticmethod
    def _sender_name(sender: Any) -> str:
        if not sender:
            return "Noma'lum"
        full = f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
        username = getattr(sender, "username", None)
        return full or (f"@{username}" if username else "Noma'lum")

    @classmethod
    def _sender_profile(cls, sender: Any) -> dict[str, str | None]:
        if not sender:
            return {"name": "Noma'lum", "username": None, "phone": None, "profile_link": None}
        username = getattr(sender, "username", None)
        sender_id = getattr(sender, "id", None)
        profile_link = f"https://t.me/{username}" if username else (f"tg://user?id={sender_id}" if sender_id else None)
        return {
            "name": cls._sender_name(sender),
            "username": f"@{username}" if username else None,
            "phone": getattr(sender, "phone", None),
            "profile_link": profile_link,
        }

    @staticmethod
    def _message_link(chat: Any, chat_id: int, message_id: int) -> str | None:
        username = getattr(chat, "username", None)
        if username:
            return f"https://t.me/{username}/{message_id}"
        raw = str(chat_id)
        if raw.startswith("-100"):
            return f"https://t.me/c/{raw[4:]}/{message_id}"
        return None

    @staticmethod
    def _signal_text(signal_id: int, keyword: str, text: str, chat_title: str, sender_profile: dict[str, str | None], message_at: datetime, link: str | None) -> str:
        safe_text = html.escape(text[:3500])
        safe_keyword = html.escape(keyword)
        safe_chat = html.escape(chat_title)
        safe_sender = html.escape(sender_profile.get("name") or "Noma'lum")
        safe_username = html.escape(sender_profile.get("username") or "Mavjud emas")
        phone = sender_profile.get("phone")
        phone_value = f"+{phone.lstrip('+')}" if phone else None
        safe_phone = html.escape(phone_value) if phone_value else None
        phone_text = f'<a href="tel:{safe_phone}">+{safe_phone}</a>' if safe_phone else "Mavjud emas"
        profile_link = sender_profile.get("profile_link")
        profile_text = f'<a href="{html.escape(profile_link)}">Ochish</a>' if profile_link else "Mavjud emas"
        message_link_text = f'<a href="{html.escape(link)}">Ochish</a>' if link else "Mavjud emas"
        message_at = to_tashkent_time(message_at)
        return (
            "<b>💬 Yangi signal topildi</b>\n\n"
            f"<blockquote>❝ {safe_text} ❞</blockquote>\n\n"
            f"<b>👤 Yozgan:</b> {safe_sender}\n"
            f"<b>🔗 Profil:</b> {profile_text}\n"
            f"<b>📞 Telefon:</b> {phone_text}\n"
            f"<b>🔗 Username:</b> {safe_username}\n\n"
            f"<b>👥 Guruh:</b> {safe_chat}\n\n"
            f"<b>🔗 Xabar havolasi:</b> {message_link_text}\n"
            f"<b>🔑 Topilgan kalit so'z:</b> {safe_keyword}\n"
            f"<b>🕒 Vaqt:</b> {message_at:%Y-%m-%d %H:%M:%S}"
        )
