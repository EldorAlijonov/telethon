from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import Config
from app.keyboards import admin_panel_keyboard, contact_request_keyboard, telethon_connected_keyboard, user_main_keyboard
from app.services.user_service import UserService
from app.utils import format_user_card, user_status_text


def register_user_handlers(user_service: UserService, config: Config) -> Router:
    router = Router()

    async def notify_admin_new_request(message: Message, phone: str) -> None:
        username = f"@{message.from_user.username}" if message.from_user.username else 'mavjud emas'
        text = (
            "📥 Yangi foydalanuvchi tasdiqlashni so'rayapti:\n\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"👤 Ism: {message.from_user.full_name}\n"
            f"🔗 Username: {username}\n"
            f"📞 Telefon: {phone}"
        )
        await message.bot.send_message(config.admin_id, text)

    @router.message(CommandStart())
    async def start_handler(message: Message, state: FSMContext):
        await state.clear()
        if message.from_user.id == config.admin_id:
            await message.answer("🛠 Admin panel", reply_markup=admin_panel_keyboard())
            return

        user = user_service.get_user_by_tg_id(message.from_user.id)
        if not user or not user.get('phone'):
            await message.answer(
                "Assalomu alaykum.\n\nBotdan foydalanish uchun avval telefon raqamingizni ulashing.\nShundan so'ng so'rovingiz adminga yuboriladi.",
                reply_markup=contact_request_keyboard(),
            )
            return

        if user_service.is_user_allowed(message.from_user.id):
            if user_service.has_telethon_session(message.from_user.id):
                await message.answer(
                    "✅ Siz Telegramga ulandingiz. Kengaytirilgan menyu ochildi.",
                    reply_markup=telethon_connected_keyboard(),
                )
            else:
                await message.answer(
                    "Xush kelibsiz. Hisobingiz tasdiqlangan. Pastdagi menyudan foydalanishingiz mumkin.",
                    reply_markup=user_main_keyboard(),
                )
            return

        await message.answer(
            f"Sizning holatingiz: {user_status_text(user)}\nSavol bo'lsa admin bilan bog'laning.",
            reply_markup=user_main_keyboard(),
        )

    @router.message(F.contact)
    async def contact_handler(message: Message, state: FSMContext):
        if message.from_user.id == config.admin_id:
            await message.answer('🛠 Admin panel', reply_markup=admin_panel_keyboard())
            return
        current_state = await state.get_state()
        if current_state is not None:
            return
        contact = message.contact
        if not contact or contact.user_id != message.from_user.id:
            await message.answer("Iltimos, o'zingizning telefon raqamingizni yuboring.", reply_markup=contact_request_keyboard())
            return

        phone = contact.phone_number if contact.phone_number.startswith('+') else f"+{contact.phone_number}"
        user_service.save_phone(
            tg_id=message.from_user.id,
            phone=phone,
            full_name=message.from_user.full_name,
            username=message.from_user.username,
        )
        await notify_admin_new_request(message, phone)
        await message.answer(
            "Rahmat. So'rovingiz adminga yuborildi.\nIltimos, tasdiqlanishini kuting.",
            reply_markup=user_main_keyboard(),
        )

    @router.message(F.text == '📨 Tasdiqlash holati')
    async def status_handler(message: Message):
        if message.from_user.id == config.admin_id:
            await message.answer('🛠 Admin panel', reply_markup=admin_panel_keyboard())
            return
        user = user_service.get_user_by_tg_id(message.from_user.id)
        if not user:
            await message.answer("Avval /start bosing va telefon raqamingizni yuboring.", reply_markup=contact_request_keyboard())
            return
        kb = telethon_connected_keyboard() if user_service.has_telethon_session(message.from_user.id) and user_service.is_user_allowed(message.from_user.id) else user_main_keyboard()
        await message.answer(format_user_card(user), reply_markup=kb)

    @router.message(F.text == '📱 Raqamni yangilash')
    async def update_phone_handler(message: Message):
        await message.answer("Yangi telefon raqamingizni yuboring.", reply_markup=contact_request_keyboard())

    @router.message(F.text == "🔄 So'rovni qayta yuborish")
    async def resend_request_handler(message: Message):
        user = user_service.get_user_by_tg_id(message.from_user.id)
        if not user or not user.get('phone'):
            await message.answer('Avval telefon raqamingizni yuboring.', reply_markup=contact_request_keyboard())
            return
        await notify_admin_new_request(message, user['phone'])
        await message.answer("So'rovingiz adminga qayta yuborildi.", reply_markup=user_main_keyboard())

    @router.message(F.text == 'ℹ️ Yordam')
    async def help_handler(message: Message):
        text = (
            "Botdan foydalanish tartibi:\n\n"
            "1. Telefon raqamingizni yuborasiz.\n"
            "2. So'rovingiz admin tomonidan ko'rib chiqiladi.\n"
            "3. Tasdiqlangach bot menyularidan foydalanasiz.\n"
            "4. Tasdiqlangan foydalanuvchi Telegram akkauntini ulashi mumkin.\n"
            "5. Telegram ulangan foydalanuvchi chatlarni kuzatishi va signal olishi mumkin."
        )
        kb = telethon_connected_keyboard() if user_service.has_telethon_session(message.from_user.id) and user_service.is_user_allowed(message.from_user.id) else user_main_keyboard()
        await message.answer(text, reply_markup=kb)

    @router.message(Command('status'))
    async def command_status(message: Message):
        await status_handler(message)

    return router
