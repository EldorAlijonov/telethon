from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import (
    BTN_ADD_KEYWORD,
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
    BTN_KEYWORDS,
    BTN_ADD_KEYWORD,
    BTN_EDIT_KEYWORD,
    BTN_DELETE_KEYWORD,
    BTN_CHATS,
    BTN_LOGOUT,
    BTN_HELP,
    BTN_CANCEL,
    BTN_FEATURES,
    BTN_MAIN_MENU,
    BTN_MONITOR_MENU,
    BTN_KEYWORD_MENU,
}


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
        await message.answer("📡 Monitoring bo'limi", reply_markup=monitoring_menu_keyboard())

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

    @router.message(F.text == BTN_LOGOUT)
    async def logout(message: Message, state: FSMContext):
        await state.clear()
        await live_monitor_service.stop_monitoring(message.from_user.id)
        await telethon_auth.revoke_session(message.from_user.id)
        await message.answer("Telegram ulanishi uzildi.", reply_markup=user_main_keyboard())

    return router
