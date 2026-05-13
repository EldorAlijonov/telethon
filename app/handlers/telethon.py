from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
import structlog

from app.keyboards import BTN_CANCEL, BTN_CONNECT, telethon_code_keyboard, telethon_connected_keyboard, telethon_phone_keyboard, user_main_keyboard
from app.services.telethon_service import TelethonAuthService
from app.services.subscription_service import SubscriptionGuardService
from app.services.user_service import UserService
from app.states.telethon_states import TelethonState
from app.utils import dotted_code, normalize_phone

logger = structlog.get_logger(__name__)


def register_telethon_handlers(
    user_service: UserService,
    telethon_auth: TelethonAuthService,
    subscription_guard: SubscriptionGuardService,
    admin_ids: set[int],
) -> Router:
    router = Router()

    @router.message(F.text == BTN_CONNECT)
    async def start_login(message: Message, state: FSMContext):
        if message.from_user.id in admin_ids:
            await message.answer("Admin uchun Telethon login kerak emas.")
            return
        ok, subscription_text = await subscription_guard.ensure_allowed(message.bot, message.from_user.id)
        if not ok:
            await message.answer(subscription_text)
            return
        if not await user_service.is_allowed(message.from_user.id):
            await state.clear()
            await message.answer("Hisobingiz hali tasdiqlanmagan yoki muddati tugagan.", reply_markup=user_main_keyboard())
            return
        await state.set_state(TelethonState.waiting_for_phone)
        await message.answer("Telegram akkauntni ulash uchun telefon raqamingizni yuboring.", reply_markup=telethon_phone_keyboard())

    @router.message(TelethonState.waiting_for_phone, F.text == BTN_CANCEL)
    async def cancel_phone(message: Message, state: FSMContext):
        await state.clear()
        await telethon_auth.cancel(message.from_user.id)
        await message.answer("Telegram ulash bekor qilindi.", reply_markup=user_main_keyboard())

    @router.message(TelethonState.waiting_for_phone, F.contact)
    async def phone_contact(message: Message, state: FSMContext):
        contact = message.contact
        if not contact or contact.user_id != message.from_user.id:
            await message.answer("Iltimos, o'zingizning telefon raqamingizni yuboring.")
            return
        phone = contact.phone_number if contact.phone_number.startswith("+") else f"+{contact.phone_number}"
        await _process_phone(message, state, phone)

    @router.message(TelethonState.waiting_for_phone)
    async def phone_text(message: Message, state: FSMContext):
        try:
            phone = normalize_phone(message.text or "")
        except ValueError as exc:
            await message.answer(str(exc))
            return
        await _process_phone(message, state, phone)

    async def _process_phone(message: Message, state: FSMContext, phone: str):
        try:
            await telethon_auth.send_code(message.from_user.id, phone)
        except ValueError as exc:
            await state.clear()
            await message.answer(f"Xatolik: {exc}", reply_markup=user_main_keyboard())
            return
        await state.set_state(TelethonState.waiting_for_code)
        await state.update_data(phone=phone, digits=[])
        await message.answer("Telegramdan kelgan kodni pastdagi tugmalar orqali kiriting.", reply_markup=user_main_keyboard())
        await message.answer("Kod kiritish paneli:", reply_markup=telethon_code_keyboard([]))

    @router.callback_query(F.data == "telethon:noop")
    async def noop(callback: CallbackQuery):
        await callback.answer()

    @router.callback_query(F.data.startswith("telethon:"))
    async def code_input(callback: CallbackQuery, state: FSMContext):
        if await state.get_state() != TelethonState.waiting_for_code.state:
            await callback.answer("Avval Telegram ulashni boshlang.", show_alert=True)
            return
        data = await state.get_data()
        digits = list(data.get("digits", []))
        parts = (callback.data or "").split(":")
        action = parts[1]

        if action == "cancel":
            await telethon_auth.cancel(callback.from_user.id)
            await state.clear()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Telegram ulash bekor qilindi.", reply_markup=user_main_keyboard())
            await callback.answer()
            return
        if action == "digit":
            if len(digits) < 6:
                digits.append(parts[2])
        elif action == "back":
            if digits:
                digits.pop()
        elif action == "clear":
            digits = []
        elif action == "submit":
            if len(digits) < 5:
                await callback.answer("Kod kamida 5 xonali bo'lishi kerak.", show_alert=True)
                return
            try:
                session = await telethon_auth.sign_in_code(callback.from_user.id, "".join(digits))
            except ValueError as exc:
                if str(exc) == "2FA_PASSWORD_NEEDED":
                    await state.set_state(TelethonState.waiting_for_password)
                    await callback.message.edit_reply_markup(reply_markup=None)
                    await callback.message.answer("Akkauntingizda 2FA yoqilgan. Parolni yuboring. Xabar avtomatik o'chiriladi.", reply_markup=user_main_keyboard())
                    await callback.answer("2FA kerak", show_alert=True)
                    return
                await telethon_auth.cancel(callback.from_user.id)
                await state.clear()
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer(f"Xatolik: {exc}", reply_markup=user_main_keyboard())
                await callback.answer("Xatolik", show_alert=True)
                return
            await telethon_auth.save_session(callback.from_user.id, data["phone"], session)
            await state.clear()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Telegram akkauntingiz muvaffaqiyatli ulandi.", reply_markup=telethon_connected_keyboard())
            await callback.answer("Ulandi")
            return
        await state.update_data(digits=digits)
        await callback.message.edit_reply_markup(reply_markup=telethon_code_keyboard(digits))
        await callback.answer(dotted_code(digits))

    @router.message(TelethonState.waiting_for_password)
    async def password_input(message: Message, state: FSMContext):
        password = (message.text or "").strip()
        try:
            await message.delete()
        except Exception:
            pass
        if not password:
            await message.answer("2FA parol bo'sh bo'lmasligi kerak.")
            return
        data = await state.get_data()
        if not data.get("phone"):
            await state.clear()
            await telethon_auth.cancel(message.from_user.id)
            await message.answer("2FA jarayoni eskirgan. Iltimos, Telegram ulashni qaytadan boshlang.", reply_markup=user_main_keyboard())
            return
        try:
            session = await telethon_auth.sign_in_password(message.from_user.id, password)
        except ValueError as exc:
            logger.warning("telethon_2fa_failed", tg_id=message.from_user.id, error=str(exc))
            await message.answer(f"Xatolik: {exc}", reply_markup=user_main_keyboard())
            return
        except Exception as exc:
            logger.exception("telethon_2fa_unexpected_error", tg_id=message.from_user.id, error=type(exc).__name__)
            await state.clear()
            await telethon_auth.cancel(message.from_user.id)
            await message.answer("2FA tekshiruvda kutilmagan xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.", reply_markup=user_main_keyboard())
            return
        await telethon_auth.save_session(message.from_user.id, data["phone"], session)
        await state.clear()
        await message.answer("Telegram akkauntingiz 2FA orqali muvaffaqiyatli ulandi.", reply_markup=telethon_connected_keyboard())

    return router
