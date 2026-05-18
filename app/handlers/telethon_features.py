from __future__ import annotations

import html
import re

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards import (
    BTN_ADD_KEYWORD,
    BTN_BLOCKED_CHATS,
    BTN_BLOCK_CHAT,
    BTN_CANCEL,
    BTN_CHATS,
    BTN_DELETE_KEYWORD,
    BTN_EDIT_KEYWORD,
    BTN_FEATURES,
    BTN_HELP,
    BTN_KEYWORDS,
    BTN_KEYWORD_MENU,
    BTN_LOGOUT,
    BTN_MAIN_MENU,
    BTN_MONITOR_MENU,
    BTN_MONITOR_OFF,
    BTN_MONITOR_ON,
    BTN_SIGNAL_DESTINATION,
    blocked_chats_keyboard,
    keyword_menu_keyboard,
    monitoring_menu_keyboard,
    telethon_connected_keyboard,
    telethon_state_keyboard,
    user_main_keyboard,
)
from app.services.keyword_service import KeywordService
from app.services.live_monitor_service import LiveMonitorService, TelethonSessionInvalidError
from app.services.subscription_service import SubscriptionGuardService
from app.services.telethon_service import TelethonAuthService
from app.services.user_service import UserService
from app.states.telethon_feature_states import TelethonFeatureState


CONTROL_BUTTONS = {
    BTN_MONITOR_ON,
    BTN_MONITOR_OFF,
    BTN_BLOCKED_CHATS,
    BTN_BLOCK_CHAT,
    BTN_KEYWORDS,
    BTN_ADD_KEYWORD,
    BTN_EDIT_KEYWORD,
    BTN_DELETE_KEYWORD,
    BTN_CHATS,
    BTN_SIGNAL_DESTINATION,
    BTN_LOGOUT,
    BTN_HELP,
    BTN_CANCEL,
    BTN_FEATURES,
    BTN_MAIN_MENU,
    BTN_MONITOR_MENU,
    BTN_KEYWORD_MENU,
}


def _extract_forwarded_chat(message: Message) -> tuple[int, str | None, str | None] | None:
    chat = getattr(message, "forward_from_chat", None)
    origin = getattr(message, "forward_origin", None)
    if not chat and origin:
        chat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
    if not chat:
        return None
    chat_id = getattr(chat, "id", None)
    if not chat_id:
        return None
    title = getattr(chat, "title", None) or getattr(chat, "full_name", None)
    username = getattr(chat, "username", None)
    return int(chat_id), title, username


def _extract_chat_username(text: str | None) -> str | None:
    value = (text or "").strip()
    if not value:
        return None
    match = re.search(r"(?:https?://)?t\.me/(?:s/)?([A-Za-z0-9_]{5,32})(?:/|\?|$)", value)
    if match:
        return match.group(1)
    if value.startswith("@") and re.fullmatch(r"@[A-Za-z0-9_]{5,32}", value):
        return value[1:]
    if re.fullmatch(r"[A-Za-z0-9_]{5,32}", value):
        return value
    return None


def _extract_invite_hash(text: str | None) -> str | None:
    value = (text or "").strip()
    if not value:
        return None
    match = re.search(r"(?:https?://)?t\.me/(?:joinchat/|\+)([A-Za-z0-9_-]{8,})", value)
    if match:
        return match.group(1)
    return None


def _extract_chat_id(text: str | None) -> int | None:
    value = (text or "").strip()
    if re.fullmatch(r"-?\d{5,20}", value):
        return int(value)
    return None


def register_telethon_feature_handlers(
    user_service: UserService,
    keyword_service: KeywordService,
    telethon_auth: TelethonAuthService,
    subscription_guard: SubscriptionGuardService,
    live_monitor_service: LiveMonitorService,
) -> Router:
    router = Router()

    async def allowed_connected(tg_id: int) -> tuple[bool, str]:
        if not await user_service.is_allowed(tg_id):
            return False, "Hisobingiz tasdiqlanmagan yoki muddati tugagan."
        if not await telethon_auth.get_plain_session(tg_id):
            return False, "Avval Telegram akkauntingizni ulang."
        return True, ""

    async def allowed_for_message(message: Message) -> tuple[bool, str]:
        ok, text = await subscription_guard.ensure_allowed(message.bot, message.from_user.id)
        if not ok:
            return False, text
        return await allowed_connected(message.from_user.id)

    async def keywords_text(tg_id: int) -> str:
        keywords = await keyword_service.list_keywords(tg_id)
        if not keywords:
            return "Hozircha kalit so'zlar yo'q."
        return "Sizning kalit so'zlaringiz:\n\n" + "\n".join(f"{i}. {item}" for i, item in enumerate(keywords, 1))

    @router.message(StateFilter(TelethonFeatureState), F.text.in_({BTN_CANCEL, BTN_FEATURES}))
    async def cancel_state(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("Amal bekor qilindi.", reply_markup=telethon_connected_keyboard())

    @router.message(F.text == BTN_MAIN_MENU)
    async def main_menu(message: Message):
        ok, _ = await allowed_connected(message.from_user.id)
        await message.answer("🏠 Asosiy menyu", reply_markup=telethon_connected_keyboard() if ok else user_main_keyboard())

    @router.message(F.text == BTN_MONITOR_MENU)
    async def monitor_menu(message: Message):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        await message.answer("📡 Kuzatish bo'limi", reply_markup=monitoring_menu_keyboard())

    @router.message(F.text == BTN_KEYWORD_MENU)
    async def keyword_menu(message: Message):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        await message.answer("🔑 Kalit so'zlar bo'limi", reply_markup=keyword_menu_keyboard())

    @router.message(F.text == BTN_KEYWORDS)
    async def my_keywords(message: Message):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        await message.answer(await keywords_text(message.from_user.id), reply_markup=keyword_menu_keyboard())

    @router.message(F.text == BTN_ADD_KEYWORD)
    async def add_start(message: Message, state: FSMContext):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        await state.set_state(TelethonFeatureState.waiting_keyword_add)
        await message.answer("Qo'shmoqchi bo'lgan kalit so'zni yuboring.", reply_markup=telethon_state_keyboard())

    @router.message(TelethonFeatureState.waiting_keyword_add)
    async def add_finish(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        if text in CONTROL_BUTTONS:
            await message.answer("Oddiy matn ko'rinishida kalit so'z yuboring.")
            return
        ok, msg = await keyword_service.add_keyword(message.from_user.id, text)
        await state.clear()
        await message.answer(msg, reply_markup=keyword_menu_keyboard())

    @router.message(F.text == BTN_DELETE_KEYWORD)
    async def delete_start(message: Message, state: FSMContext):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        await state.set_state(TelethonFeatureState.waiting_keyword_delete)
        await message.answer((await keywords_text(message.from_user.id)) + "\n\nO'chirmoqchi bo'lgan kalit so'zni yuboring.", reply_markup=telethon_state_keyboard())

    @router.message(TelethonFeatureState.waiting_keyword_delete)
    async def delete_finish(message: Message, state: FSMContext):
        deleted = await keyword_service.delete_keyword(message.from_user.id, message.text or "")
        await state.clear()
        await message.answer("Kalit so'z o'chirildi." if deleted else "Kalit so'z topilmadi.", reply_markup=keyword_menu_keyboard())

    @router.message(F.text == BTN_EDIT_KEYWORD)
    async def edit_start(message: Message, state: FSMContext):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        await state.set_state(TelethonFeatureState.waiting_keyword_edit_old)
        await message.answer((await keywords_text(message.from_user.id)) + "\n\nEski kalit so'zni yuboring.", reply_markup=telethon_state_keyboard())

    @router.message(TelethonFeatureState.waiting_keyword_edit_old)
    async def edit_old(message: Message, state: FSMContext):
        await state.update_data(old_keyword=message.text or "")
        await state.set_state(TelethonFeatureState.waiting_keyword_edit_new)
        await message.answer("Yangi kalit so'zni yuboring.", reply_markup=telethon_state_keyboard())

    @router.message(TelethonFeatureState.waiting_keyword_edit_new)
    async def edit_new(message: Message, state: FSMContext):
        data = await state.get_data()
        ok, msg = await keyword_service.rename_keyword(message.from_user.id, data.get("old_keyword", ""), message.text or "")
        await state.clear()
        await message.answer(msg, reply_markup=keyword_menu_keyboard())

    @router.message(F.text == BTN_MONITOR_ON)
    async def monitor_on(message: Message):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        success, msg = await live_monitor_service.start_monitoring(message.from_user.id, message.bot)
        await message.answer(msg, reply_markup=monitoring_menu_keyboard() if success else user_main_keyboard())

    @router.message(F.text == BTN_MONITOR_OFF)
    async def monitor_off(message: Message):
        await live_monitor_service.stop_monitoring(message.from_user.id)
        await message.answer("Kuzatish o'chirildi.", reply_markup=monitoring_menu_keyboard())

    @router.message(F.text == BTN_CHATS)
    async def chats(message: Message):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        try:
            titles = await live_monitor_service.list_dialog_titles(message.from_user.id)
        except TelethonSessionInvalidError:
            await message.answer("Telegram sessiya eskirgan. Qayta ulaning.", reply_markup=user_main_keyboard())
            return
        body = "\n".join(f"- {title}" for title in titles[:30]) if titles else "Chatlar topilmadi."
        await message.answer("Ko'rinib turgan chatlar:\n\n" + body, reply_markup=monitoring_menu_keyboard())

    @router.message(F.text == BTN_BLOCK_CHAT)
    async def block_chat_start(message: Message, state: FSMContext):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        await state.set_state(TelethonFeatureState.waiting_chat_block)
        await message.answer(
            "Bloklamoqchi bo'lgan chat @username'ini yuboring yoki o'sha guruhdan bitta xabarni forward qiling.",
            reply_markup=telethon_state_keyboard(),
        )

    @router.message(TelethonFeatureState.waiting_chat_block)
    async def block_chat_finish(message: Message, state: FSMContext):
        forwarded_chat = _extract_forwarded_chat(message)
        try:
            if forwarded_chat:
                chat_id, title, username = forwarded_chat
                msg = await live_monitor_service.block_chat(message.from_user.id, chat_id, title, username)
            else:
                username = _extract_chat_username(message.text)
                if not username:
                    await message.answer("@username yoki guruhdan forward qilingan xabar yuboring.")
                    return
                msg = await live_monitor_service.block_chat_by_username(message.from_user.id, username)
        except TelethonSessionInvalidError:
            await state.clear()
            await message.answer("Telegram sessiya eskirgan. Qayta ulaning.", reply_markup=user_main_keyboard())
            return
        await state.clear()
        await message.answer(msg, reply_markup=monitoring_menu_keyboard())

    @router.message(F.text == BTN_BLOCKED_CHATS)
    async def blocked_chats(message: Message):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        chats = await live_monitor_service.list_blocked_chats(message.from_user.id)
        if not chats:
            await message.answer("Bloklangan chatlar yo'q.", reply_markup=monitoring_menu_keyboard())
            return
        body = "\n".join(f"{i}. {html.escape(title)} - <code>{chat_id}</code>" for i, (chat_id, title) in enumerate(chats[:50], 1))
        await message.answer(
            "Bloklangan chatlar:\n\n" + body,
            reply_markup=blocked_chats_keyboard(chats[:50]),
        )

    @router.message(F.text == BTN_SIGNAL_DESTINATION)
    async def signal_destination_start(message: Message, state: FSMContext):
        ok, error = await allowed_for_message(message)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        current = await user_service.get(message.from_user.id)
        current_text = ""
        if current and current.signal_destination_chat_id:
            title = html.escape(current.signal_destination_title or str(current.signal_destination_chat_id))
            current_text = f"\n\nHozirgi manzil: {title} - <code>{current.signal_destination_chat_id}</code>"
        await state.set_state(TelethonFeatureState.waiting_signal_destination)
        await message.answer(
            "Signallar yuboriladigan guruh yoki kanalni yuboring.\n"
            "@username, t.me havola, maxfiy invite link, chat ID yoki o'sha guruh/kanaldan forward qilingan xabar qabul qilinadi.\n\n"
            "Bot o'sha guruh/kanalga qo'shilgan va xabar yubora oladigan bo'lishi kerak."
            f"{current_text}",
            reply_markup=telethon_state_keyboard(),
        )

    @router.message(TelethonFeatureState.waiting_signal_destination)
    async def signal_destination_finish(message: Message, state: FSMContext):
        forwarded_chat = _extract_forwarded_chat(message)
        title: str | None = None
        try:
            if forwarded_chat:
                chat_id, title, _ = forwarded_chat
            else:
                chat_id = _extract_chat_id(message.text)
                invite_hash = _extract_invite_hash(message.text)
                username = _extract_chat_username(message.text)
                if invite_hash:
                    chat_id, title = await live_monitor_service.resolve_invite_destination(message.from_user.id, invite_hash)
                elif username:
                    chat = await message.bot.get_chat(f"@{username}")
                    chat_id = int(chat.id)
                    title = getattr(chat, "title", None) or getattr(chat, "username", None)
                elif chat_id is not None:
                    chat = await message.bot.get_chat(chat_id)
                    title = getattr(chat, "title", None) or getattr(chat, "username", None)
                else:
                    await message.answer("@username, t.me havola, maxfiy invite link, chat ID yoki forward qilingan xabar yuboring.")
                    return
        except TelethonSessionInvalidError:
            await state.clear()
            await message.answer("Telegram sessiya eskirgan. Qayta ulaning.", reply_markup=user_main_keyboard())
            return
        except ValueError as exc:
            await message.answer(str(exc))
            return
        except Exception:
            await message.answer("Manzil topilmadi yoki bot u yerga kira olmayapti. Botni guruh/kanalga qo'shib qayta urinib ko'ring.")
            return

        try:
            bot_chat = await message.bot.get_chat(chat_id)
            title = title or getattr(bot_chat, "title", None) or getattr(bot_chat, "username", None)
        except Exception:
            await message.answer(
                "Chat topildi, lekin bot u yerga kira olmayapti. Botni maxfiy guruhga qo'shing yoki kanalga admin qiling, keyin qayta urinib ko'ring."
            )
            return

        saved = await user_service.set_signal_destination(message.from_user.id, chat_id, title)
        await state.clear()
        if not saved:
            await message.answer("Hisob topilmadi.", reply_markup=monitoring_menu_keyboard())
            return
        safe_title = html.escape(title or str(chat_id))
        await message.answer(
            f"Signal manzili saqlandi:\n{safe_title}\nID: <code>{chat_id}</code>",
            reply_markup=monitoring_menu_keyboard(),
        )

    @router.callback_query(F.data.startswith("chat_unblock:"))
    async def unblock_chat(callback: CallbackQuery):
        try:
            chat_id = int((callback.data or "").split(":", 1)[1])
        except (IndexError, ValueError):
            await callback.answer("Chat ID noto'g'ri.", show_alert=True)
            return
        ok, error = await allowed_connected(callback.from_user.id)
        if not ok:
            await callback.answer(error, show_alert=True)
            return
        msg = await live_monitor_service.unblock_chat(callback.from_user.id, chat_id)
        await callback.message.answer(msg, reply_markup=monitoring_menu_keyboard())
        await callback.answer("Blokdan chiqarildi")

    @router.message(F.text == BTN_LOGOUT)
    async def logout(message: Message, state: FSMContext):
        await state.clear()
        await live_monitor_service.stop_monitoring(message.from_user.id)
        await telethon_auth.revoke_session(message.from_user.id)
        await message.answer("Telegram ulanishi uzildi.", reply_markup=user_main_keyboard())

    return router
