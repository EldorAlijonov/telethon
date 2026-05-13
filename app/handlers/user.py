from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.core.config import Settings
from app.keyboards import (
    BTN_ACCOUNT_MENU,
    BTN_HELP,
    BTN_MAIN_MENU,
    BTN_RESEND,
    BTN_STATUS,
    BTN_UPDATE_PHONE,
    admin_panel_keyboard,
    connected_account_keyboard,
    contact_request_keyboard,
    pending_user_action_keyboard,
    telethon_connected_keyboard,
    user_account_keyboard,
    user_main_keyboard,
)
from app.services.telethon_service import TelethonAuthService
from app.services.subscription_service import SubscriptionGuardService
from app.services.user_service import UserService
from app.utils import format_user_card, user_status_text


def register_user_handlers(
    user_service: UserService,
    telethon_auth: TelethonAuthService,
    subscription_guard: SubscriptionGuardService,
    settings: Settings,
) -> Router:
    router = Router()

    async def notify_admin(message: Message, phone: str) -> None:
        username = f"@{message.from_user.username}" if message.from_user.username else "mavjud emas"
        text = (
            "Yangi foydalanuvchi tasdiqlash so'rayapti:\n\n"
            f"ID: <code>{message.from_user.id}</code>\n"
            f"Ism: {message.from_user.full_name}\n"
            f"Username: {username}"
        )
        text += f"\nTelefon: {phone}"
        for admin_id in settings.effective_admin_ids:
            await message.bot.send_message(
                admin_id,
                text,
                reply_markup=pending_user_action_keyboard(message.from_user.id),
            )

    @router.message(CommandStart())
    async def start_handler(message: Message, state: FSMContext):
        await state.clear()
        if message.from_user.id in settings.effective_admin_ids:
            await message.answer("Admin panel", reply_markup=admin_panel_keyboard())
            return
        ok, subscription_text = await subscription_guard.ensure_allowed(message.bot, message.from_user.id)
        if not ok:
            await message.answer(subscription_text)
            return

        user = await user_service.get(message.from_user.id)
        if not user or not user.phone:
            await message.answer(
                "Assalomu alaykum.\n\nBotdan foydalanish uchun telefon raqamingizni yuboring. So'rovingiz admin tomonidan ko'rib chiqiladi.",
                reply_markup=contact_request_keyboard(),
            )
            return

        if await user_service.is_allowed(message.from_user.id):
            session = await telethon_auth.get_plain_session(message.from_user.id)
            keyboard = telethon_connected_keyboard() if session else user_main_keyboard()
            await message.answer("Xush kelibsiz. Hisobingiz faol.", reply_markup=keyboard)
            return

        await message.answer(f"Sizning holatingiz: {user_status_text(user)}", reply_markup=user_main_keyboard())

    @router.message(F.contact)
    async def contact_handler(message: Message, state: FSMContext):
        if await state.get_state():
            return
        ok, subscription_text = await subscription_guard.ensure_allowed(message.bot, message.from_user.id)
        if not ok:
            await message.answer(subscription_text)
            return
        contact = message.contact
        if not contact or contact.user_id != message.from_user.id:
            await message.answer("Iltimos, o'zingizning telefon raqamingizni yuboring.", reply_markup=contact_request_keyboard())
            return
        phone = contact.phone_number if contact.phone_number.startswith("+") else f"+{contact.phone_number}"
        await user_service.register_or_update(message.from_user.id, message.from_user.full_name, message.from_user.username, phone)
        await notify_admin(message, phone)
        await message.answer("Rahmat. So'rovingiz adminga yuborildi. Iltimos, tasdiqlanishini kuting.", reply_markup=user_main_keyboard())

    @router.message(F.text == BTN_STATUS)
    @router.message(Command("status"))
    async def status_handler(message: Message):
        user = await user_service.get(message.from_user.id)
        ok, subscription_text = await subscription_guard.ensure_allowed(message.bot, message.from_user.id)
        if not ok:
            await message.answer(subscription_text)
            return
        if not user:
            await message.answer("Avval /start bosing va telefon raqamingizni yuboring.", reply_markup=contact_request_keyboard())
            return
        session = await telethon_auth.get_plain_session(message.from_user.id)
        keyboard = telethon_connected_keyboard() if session and await user_service.is_allowed(message.from_user.id) else user_main_keyboard()
        await message.answer(format_user_card(user), reply_markup=keyboard)

    @router.message(F.text == BTN_ACCOUNT_MENU)
    async def account_menu_handler(message: Message):
        session = await telethon_auth.get_plain_session(message.from_user.id)
        if session and await user_service.is_allowed(message.from_user.id):
            await message.answer("👤 Hisob bo'limi", reply_markup=connected_account_keyboard())
            return
        await message.answer("👤 Hisob bo'limi", reply_markup=user_account_keyboard())

    @router.message(F.text == BTN_MAIN_MENU)
    async def main_menu_handler(message: Message):
        session = await telethon_auth.get_plain_session(message.from_user.id)
        if session and await user_service.is_allowed(message.from_user.id):
            await message.answer("🏠 Asosiy menyu", reply_markup=telethon_connected_keyboard())
            return
        await message.answer("🏠 Asosiy menyu", reply_markup=user_main_keyboard())

    @router.message(F.text == BTN_UPDATE_PHONE)
    async def update_phone_handler(message: Message):
        await message.answer("Yangi telefon raqamingizni yuboring.", reply_markup=contact_request_keyboard())

    @router.message(F.text == BTN_RESEND)
    async def resend_request_handler(message: Message):
        user = await user_service.get(message.from_user.id)
        if not user or not user.phone:
            await message.answer("Avval telefon raqamingizni yuboring.", reply_markup=contact_request_keyboard())
            return
        await notify_admin(message, user.phone)
        await message.answer("So'rovingiz adminga qayta yuborildi.", reply_markup=user_main_keyboard())

    @router.message(F.text == BTN_HELP)
    async def help_handler(message: Message):
        await message.answer(
            "Botdan foydalanish tartibi:\n\n"
            "1. Telefon raqamingizni yuborasiz.\n"
            "2. Admin tasdiqlaydi.\n"
            "3. Telegram akkauntingizni xavfsiz OTP orqali ulaysiz.\n"
            "4. Kalit so'zlar bo'yicha chatlardan realtime signal olasiz.",
            reply_markup=user_main_keyboard(),
        )

    return router
