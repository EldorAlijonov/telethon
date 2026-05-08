from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.keyboards import telethon_code_keyboard, telethon_connected_keyboard, telethon_phone_keyboard, user_main_keyboard
from app.services.telethon_service import TelethonService
from app.services.user_service import UserService
from app.states.telethon_states import TelethonState
from app.utils import dotted_code, normalize_phone


def register_telethon_handlers(user_service: UserService, telethon_service: TelethonService, config: Config) -> Router:
    router = Router()

    def user_has_active_access(user_id: int) -> bool:
        return user_service.is_user_allowed(user_id)

    @router.message(F.text == '🤖 Telegram ulash')
    async def telethon_start(message: Message, state: FSMContext):
        if message.from_user.id == config.admin_id:
            await message.answer("Admin uchun bu bo'lim ishlatilmaydi.")
            return
        if not user_has_active_access(message.from_user.id):
            user_service.clear_telethon_session(message.from_user.id)
            await state.clear()
            await message.answer(
                "⛔ Sizning foydalanish muddati tugagan yoki hali tasdiqlanmagansiz.\n\nQayta faollashtirish uchun admin tasdiqlashini kuting.",
                reply_markup=user_main_keyboard(),
            )
            return
        await state.set_state(TelethonState.waiting_for_phone)
        await message.answer('Telegram ulash uchun telefon raqamingizni qayta yuboring.', reply_markup=telethon_phone_keyboard())

    @router.message(TelethonState.waiting_for_phone, F.contact)
    async def telethon_phone_contact(message: Message, state: FSMContext):
        if not user_has_active_access(message.from_user.id):
            user_service.clear_telethon_session(message.from_user.id)
            await state.clear()
            await message.answer("⛔ Foydalanish muddati tugagan. Qayta tasdiqlanish uchun admin bilan bog'laning.", reply_markup=user_main_keyboard())
            return
        contact = message.contact
        if not contact or contact.user_id != message.from_user.id:
            await message.answer("Iltimos, o'zingizning telefon raqamingizni yuboring.")
            return
        phone = contact.phone_number if contact.phone_number.startswith('+') else f'+{contact.phone_number}'
        await _process_phone(message, state, phone)

    @router.message(TelethonState.waiting_for_phone)
    async def telethon_phone_text(message: Message, state: FSMContext):
        if (message.text or '') == '❌ Bekor qilish':
            await state.clear()
            await message.answer('Telegram ulash bekor qilindi.', reply_markup=user_main_keyboard())
            return
        if not user_has_active_access(message.from_user.id):
            user_service.clear_telethon_session(message.from_user.id)
            await state.clear()
            await message.answer("⛔ Foydalanish muddati tugagan. Qayta tasdiqlanish uchun admin bilan bog'laning.", reply_markup=user_main_keyboard())
            return
        try:
            phone = normalize_phone(message.text or '')
        except ValueError as exc:
            await message.answer(str(exc))
            return
        await _process_phone(message, state, phone)

    async def _process_phone(message: Message, state: FSMContext, phone: str):
        try:
            await telethon_service.send_code(message.from_user.id, phone)
        except ValueError as exc:
            await message.answer(f'❌ {exc}', reply_markup=user_main_keyboard())
            await state.clear()
            return
        await state.set_state(TelethonState.waiting_for_code)
        await state.update_data(telethon_phone=phone, telethon_digits=[])
        await message.answer("Telegramdan kelgan kodni inline tugmalar orqali kiriting.\nKo'rinishi: 1.2.3.4.5", reply_markup=user_main_keyboard())
        await message.answer('Kod kiritish paneli:', reply_markup=telethon_code_keyboard([]))

    @router.callback_query(F.data == 'telethon:noop')
    async def telethon_noop(callback: CallbackQuery):
        await callback.answer()

    @router.callback_query(F.data.startswith('telethon:'))
    async def telethon_code_input(callback: CallbackQuery, state: FSMContext):
        current_state = await state.get_state()
        if current_state != TelethonState.waiting_for_code.state:
            await callback.answer('Avval Telegram ulashni boshlang.', show_alert=True)
            return
        if not user_has_active_access(callback.from_user.id):
            user_service.clear_telethon_session(callback.from_user.id)
            await telethon_service.cancel(callback.from_user.id)
            await state.clear()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer('⛔ Foydalanish muddati tugagan. Qayta faollashtirish uchun admin tasdiqlashi kerak.', reply_markup=user_main_keyboard())
            await callback.answer('Muddati tugagan', show_alert=True)
            return

        parts = callback.data.split(':')
        action = parts[1]
        data = await state.get_data()
        digits = list(data.get('telethon_digits', []))

        if action == 'cancel':
            await telethon_service.cancel(callback.from_user.id)
            await state.clear()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer('Telegram ulash bekor qilindi.', reply_markup=user_main_keyboard())
            await callback.answer()
            return
        if action == 'digit':
            if len(digits) < 6:
                digits.append(parts[2])
            await state.update_data(telethon_digits=digits)
            await callback.message.edit_reply_markup(reply_markup=telethon_code_keyboard(digits))
            await callback.answer(dotted_code(digits))
            return
        if action == 'back':
            if digits:
                digits.pop()
            await state.update_data(telethon_digits=digits)
            await callback.message.edit_reply_markup(reply_markup=telethon_code_keyboard(digits))
            await callback.answer(dotted_code(digits))
            return
        if action == 'clear':
            await state.update_data(telethon_digits=[])
            await callback.message.edit_reply_markup(reply_markup=telethon_code_keyboard([]))
            await callback.answer('Tozalandi')
            return
        if action == 'submit':
            if len(digits) < 5:
                await callback.answer("Kod kamida 5 xonali bo'lishi kerak", show_alert=True)
                return
            code = ''.join(digits)
            phone = data.get('telethon_phone', '')
            try:
                session = await telethon_service.sign_in(callback.from_user.id, code)
            except ValueError as exc:
                if str(exc) == '2FA_PASSWORD_NEEDED':
                    await state.set_state(TelethonState.waiting_for_password)
                    await callback.message.edit_reply_markup(reply_markup=None)
                    await callback.message.answer("🔐 Akkountda ikki bosqichli parol yoqilgan.\nIltimos, 2FA parolingizni yuboring.", reply_markup=user_main_keyboard())
                    await callback.answer('Parol kerak', show_alert=True)
                    return
                await callback.answer('Kirishda xatolik', show_alert=True)
                await callback.message.answer(f'❌ {exc}\nQaytadan urinib ko\'ring.', reply_markup=user_main_keyboard())
                await callback.message.edit_reply_markup(reply_markup=None)
                await state.clear()
                await telethon_service.cancel(callback.from_user.id)
                return
            user_service.save_telethon_session(callback.from_user.id, phone, session)
            await state.clear()
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                "✅ Telegram muvaffaqiyatli ulandi.\n\nEndi siz botning keyingi imkoniyatlaridan foydalanishingiz mumkin.",
                reply_markup=telethon_connected_keyboard(),
            )
            await callback.answer('Muvaffaqiyatli')

    @router.message(TelethonState.waiting_for_password)
    async def telethon_password_input(message: Message, state: FSMContext):
        if not user_has_active_access(message.from_user.id):
            user_service.clear_telethon_session(message.from_user.id)
            await telethon_service.cancel(message.from_user.id)
            await state.clear()
            await message.answer('⛔ Foydalanish muddati tugagan. Qayta faollashtirish uchun admin tasdiqlashi kerak.', reply_markup=user_main_keyboard())
            return
        password = (message.text or '').strip()
        if not password:
            await message.answer('Iltimos, 2FA parolni yuboring.')
            return
        data = await state.get_data()
        phone = data.get('telethon_phone', '')
        try:
            session = await telethon_service.sign_in_with_password(message.from_user.id, password)
        except ValueError as exc:
            await message.answer(f'❌ {exc}\nQaytadan urinib ko\'ring.', reply_markup=user_main_keyboard())
            return
        user_service.save_telethon_session(message.from_user.id, phone, session)
        await state.clear()
        await message.answer('✅ Telegram muvaffaqiyatli ulandi.\n\nIkki bosqichli parol orqali kirish yakunlandi.', reply_markup=telethon_connected_keyboard())

    return router
