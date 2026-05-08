from __future__ import annotations

import asyncio
import html
from typing import Any

from telethon import TelegramClient, events
from telethon.errors import AuthKeyUnregisteredError
from telethon.sessions import StringSession


class TelethonSessionInvalidError(Exception):
    pass


class LiveMonitorService:
    def __init__(
        self,
        api_id: int,
        api_hash: str,
        user_service,
        keyword_service,
        monitor_service,
        blacklist_ids: set[int] | None = None,
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.user_service = user_service
        self.keyword_service = keyword_service
        self.monitor_service = monitor_service
        self.blacklist_ids = blacklist_ids or set()
        self.clients: dict[int, TelegramClient] = {}
        self.handlers: dict[int, Any] = {}
        self.tasks: dict[int, asyncio.Task] = {}
        self.last_signals: dict[int, dict[tuple[int, int, str], float]] = {}
        self.keyword_cache: dict[int, tuple[float, list[str]]] = {}
        self.monitor_enabled_cache: dict[int, tuple[float, bool]] = {}
        self.access_cache: dict[int, tuple[float, bool]] = {}

    def _is_chat_blocked(self, chat_id: int) -> bool:
        return chat_id in self.blacklist_ids

    @staticmethod
    def _is_chat_inactive(chat: Any) -> bool:
        return bool(
            getattr(chat, 'left', False)
            or getattr(chat, 'deactivated', False)
            or getattr(chat, 'kicked', False)
        )

    @staticmethod
    def _looks_like_our_signal(text: str) -> bool:
        lowered = text.lower()
        return 'yangi signal topildi' in lowered and 'topilgan kalit so' in lowered

    def invalidate_keywords(self, tg_id: int) -> None:
        self.keyword_cache.pop(tg_id, None)

    def _set_monitor_enabled_cache(self, tg_id: int, enabled: bool) -> None:
        self.monitor_enabled_cache[tg_id] = (asyncio.get_running_loop().time() + 2, enabled)

    def _is_monitor_enabled(self, tg_id: int) -> bool:
        now = asyncio.get_running_loop().time()
        cached = self.monitor_enabled_cache.get(tg_id)
        if cached and cached[0] > now:
            return cached[1]
        enabled = self.monitor_service.is_enabled(tg_id)
        self.monitor_enabled_cache[tg_id] = (now + 2, enabled)
        return enabled

    def _set_access_cache(self, tg_id: int, allowed: bool) -> None:
        self.access_cache[tg_id] = (asyncio.get_running_loop().time() + 60, allowed)

    def _is_user_allowed_cached(self, tg_id: int) -> bool:
        now = asyncio.get_running_loop().time()
        cached = self.access_cache.get(tg_id)
        if cached and cached[0] > now:
            return cached[1]
        allowed = self.user_service.is_user_allowed(tg_id)
        self.access_cache[tg_id] = (now + 60, allowed)
        return allowed

    def _get_keywords(self, tg_id: int) -> list[str]:
        now = asyncio.get_running_loop().time()
        cached = self.keyword_cache.get(tg_id)
        if cached and cached[0] > now:
            return cached[1]
        keywords = self.keyword_service.get_keywords(tg_id)
        self.keyword_cache[tg_id] = (now + 15, keywords)
        return keywords

    async def start_monitoring(self, tg_id: int, bot) -> tuple[bool, str]:
        user = self.user_service.get_user_by_tg_id(tg_id)
        if not user or not user.get('telethon_session'):
            return False, 'Telegram ulanishi topilmadi.'

        if not self.user_service.is_user_allowed(tg_id):
            self.user_service.clear_telethon_session(tg_id)
            return False, 'Foydalanish muddati tugagan. Qayta tasdiqlanish kerak.'

        self.keyword_service.ensure_default_keywords(tg_id)

        if self.clients.get(tg_id):
            self.monitor_service.set_enabled(tg_id, True)
            self._set_monitor_enabled_cache(tg_id, True)
            return True, 'Kuzatish allaqachon yoqilgan.'

        client = TelegramClient(StringSession(user['telethon_session']), self.api_id, self.api_hash)
        try:
            await client.connect()
            me = await client.get_me()
        except AuthKeyUnregisteredError:
            await client.disconnect()
            self.monitor_service.set_enabled(tg_id, False)
            self.user_service.clear_telethon_session(tg_id)
            return False, "Telegram ulanishingiz eskirgan. Iltimos, Telegramni qayta ulang."

        my_user_id = me.id if me else None
        if my_user_id:
            self.blacklist_ids.add(int(my_user_id))
        self.last_signals[tg_id] = {}

        async def handler(event):
            if getattr(event, 'out', False):
                return

            sender_id = getattr(event, 'sender_id', None)
            if sender_id and int(sender_id) in self.blacklist_ids:
                return

            if my_user_id and sender_id == my_user_id:
                return

            chat_id = getattr(event, 'chat_id', None) or 0
            if not chat_id or self._is_chat_blocked(int(chat_id)):
                return

            text = (event.raw_text or '').strip()
            if not text or self._looks_like_our_signal(text):
                return

            if not self._is_monitor_enabled(tg_id):
                return

            keywords = self._get_keywords(tg_id)
            if not keywords:
                return

            lowered = text.lower()
            found = next((kw for kw in keywords if kw and kw in lowered), None)
            if not found:
                return

            if not self._is_user_allowed_cached(tg_id):
                self.monitor_service.set_enabled(tg_id, False)
                self._set_monitor_enabled_cache(tg_id, False)
                self.user_service.clear_telethon_session(tg_id)
                self._set_access_cache(tg_id, False)
                await self.stop_monitoring(tg_id)
                try:
                    await bot.send_message(tg_id, '⛔ Foydalanish muddati tugadi. Kuzatish o‘chirildi.')
                except Exception:
                    pass
                return

            sender, chat = await asyncio.gather(event.get_sender(), event.get_chat())
            if sender is not None and getattr(sender, 'bot', False):
                return
            if not chat or self._is_chat_inactive(chat):
                return

            msg_id = getattr(event.message, 'id', None) or 0
            dedupe_key = (int(chat_id), int(msg_id), found.lower())
            if dedupe_key in self.last_signals[tg_id]:
                return

            now = asyncio.get_running_loop().time()
            self.last_signals[tg_id][dedupe_key] = now
            stale = [k for k, ts in self.last_signals[tg_id].items() if now - ts > 1800]
            for k in stale:
                self.last_signals[tg_id].pop(k, None)

            sender_name = (((getattr(sender, 'first_name', None) or '') + ' ' + (getattr(sender, 'last_name', None) or '')).strip() or getattr(sender, 'title', None) or "Noma'lum")
            username = getattr(sender, 'username', None)
            phone = getattr(sender, 'phone', None) or 'mavjud emas'

            safe_sender_name = html.escape(sender_name)
            safe_phone = html.escape(str(phone))
            safe_text = html.escape(text)
            safe_found = html.escape(found)

            if username:
                sender_url = f'https://t.me/{username}'
                sender_text = f'<a href="{sender_url}">{safe_sender_name}</a>'
                profile_text = f'<a href="{sender_url}">Ochish</a>'
                username_text = f'@{html.escape(username)}'
            else:
                sender_text = safe_sender_name
                profile_text = 'mavjud emas'
                username_text = 'mavjud emas'

            chat_title = getattr(chat, 'title', None) or "Noma'lum guruh"
            chat_username = getattr(chat, 'username', None)
            safe_chat_title = html.escape(chat_title)

            if chat_username:
                chat_link = f'https://t.me/{chat_username}'
                chat_text = f'<a href="{chat_link}">{safe_chat_title}</a>'
                msg_link = f'https://t.me/{chat_username}/{msg_id}'
                msg_link_text = f'<a href="{msg_link}">Ochish</a>'
            else:
                chat_text = safe_chat_title
                if str(chat_id).startswith('-100'):
                    internal_id = str(chat_id)[4:]
                    msg_link_text = f'<a href="https://t.me/c/{internal_id}/{msg_id}">Ochish</a>'
                else:
                    msg_link_text = 'mavjud emas'

            signal_text = (
                '💬 Yangi signal topildi\n\n'
                f'<blockquote>{safe_text}</blockquote>\n\n'
                f'👤 Yozgan: {sender_text}\n'
                f'🔗 Profil: {profile_text}\n'
                f'📞 Telefon: {safe_phone}\n'
                f'🔗 Username: {username_text}\n\n'
                f'👥 Guruh: {chat_text}\n\n'
                f'🔗 Xabar havolasi: {msg_link_text}\n'
                f'🔑 Topilgan kalit so\'z: {safe_found}'
            )

            try:
                await bot.send_message(tg_id, signal_text, parse_mode='HTML', disable_web_page_preview=True)
            except Exception:
                pass

        client.add_event_handler(handler, events.NewMessage())
        self.clients[tg_id] = client
        self.handlers[tg_id] = handler
        self.monitor_service.set_enabled(tg_id, True)
        self._set_monitor_enabled_cache(tg_id, True)
        self._set_access_cache(tg_id, True)

        async def runner():
            try:
                await client.run_until_disconnected()
            except Exception:
                pass
            finally:
                self.monitor_service.set_enabled(tg_id, False)
                self._set_monitor_enabled_cache(tg_id, False)
                self.clients.pop(tg_id, None)
                self.handlers.pop(tg_id, None)
                self.tasks.pop(tg_id, None)
                self.last_signals.pop(tg_id, None)
                self.keyword_cache.pop(tg_id, None)
                self.access_cache.pop(tg_id, None)

        self.tasks[tg_id] = asyncio.create_task(runner())
        return True, 'Kuzatish yoqildi.'

    async def stop_monitoring(self, tg_id: int) -> None:
        self.monitor_service.set_enabled(tg_id, False)
        self._set_monitor_enabled_cache(tg_id, False)
        client = self.clients.pop(tg_id, None)
        handler = self.handlers.pop(tg_id, None)
        task = self.tasks.pop(tg_id, None)
        self.last_signals.pop(tg_id, None)
        self.keyword_cache.pop(tg_id, None)
        self.access_cache.pop(tg_id, None)

        if client and handler:
            try:
                client.remove_event_handler(handler)
            except Exception:
                pass

        if client:
            try:
                await client.disconnect()
            except Exception:
                pass

        if task:
            task.cancel()

    async def stop_all(self) -> None:
        for tg_id in list(self.clients):
            await self.stop_monitoring(tg_id)

    async def list_dialog_titles(self, tg_id: int) -> list[str]:
        client = self.clients.get(tg_id)
        temp = False
        if not client:
            user = self.user_service.get_user_by_tg_id(tg_id)
            if not user or not user.get('telethon_session'):
                return []
            client = TelegramClient(StringSession(user['telethon_session']), self.api_id, self.api_hash)
            await client.connect()
            temp = True

        titles: list[str] = []
        invalid_session = False
        try:
            async for dialog in client.iter_dialogs(limit=50):
                entity = getattr(dialog, 'entity', None)
                if entity and self._is_chat_inactive(entity):
                    continue
                if getattr(dialog, 'is_user', False):
                    continue
                if int(dialog.id) in self.blacklist_ids:
                    continue
                titles.append(dialog.name or "Noma'lum chat")
        except AuthKeyUnregisteredError:
            invalid_session = True
        finally:
            if temp:
                await client.disconnect()

        if invalid_session:
            if not temp:
                await self.stop_monitoring(tg_id)
            else:
                self.monitor_service.set_enabled(tg_id, False)
            self.user_service.clear_telethon_session(tg_id)
            raise TelethonSessionInvalidError("Telethon session is no longer registered")

        return titles
