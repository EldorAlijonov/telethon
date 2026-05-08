from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import Config
from app.filters import AdminFilter
from app.keyboards import admin_panel_keyboard, back_to_admin_panel_keyboard, pending_user_action_keyboard
from app.services.user_service import UserService
from app.states.admin_states import AdminActionState
from app.utils import format_user_card


def register_admin_handlers(user_service: UserService, config: Config) -> Router:
    router = Router()
    admin_filter = AdminFilter(config.admin_id)

    async def send_admin_panel(message: Message):
        await message.answer('🛠 Admin panel', reply_markup=admin_panel_keyboard())

    @router.message(Command('start'), admin_filter)
    async def admin_start(message: Message, state: FSMContext):
        await state.clear()
        await send_admin_panel(message)

    @router.message(Command('admin'), admin_filter)
    async def admin_panel_cmd(message: Message):
        await send_admin_panel(message)

    @router.message(F.text == '🛠 Admin panel', admin_filter)
    async def admin_panel_btn(message: Message):
        await send_admin_panel(message)

    @router.message(F.text == '⬅️ Admin panelga qaytish', admin_filter)
    async def back_to_panel(message: Message, state: FSMContext):
        await state.clear()
        await send_admin_panel(message)

    @router.message(F.text == '⏳ Tasdiqlash kutilayotganlar', admin_filter)
    async def pending_users(message: Message):
        users = [user for user in user_service.get_pending_users() if user['tg_id'] != config.admin_id]
        if not users:
            await message.answer('⏳ Tasdiqlash kutilayotgan foydalanuvchilar mavjud emas.', reply_markup=back_to_admin_panel_keyboard())
            return
        await message.answer('⏳ Tasdiqlash kutilayotgan foydalanuvchilar:', reply_markup=back_to_admin_panel_keyboard())
        for user in users:
            await message.answer(format_user_card(user), reply_markup=pending_user_action_keyboard(user['tg_id']))
        await message.answer('Tasdiqlash uchun “✅ ID orqali tasdiqlash” tugmasini bosing.', reply_markup=admin_panel_keyboard())

    @router.callback_query(F.data.startswith('admin_pending:'))
    async def pending_user_action(callback: CallbackQuery):
        if callback.from_user.id != config.admin_id:
            await callback.answer('Siz admin emassiz.', show_alert=True)
            return

        parts = (callback.data or '').split(':')
        if len(parts) != 3 or not parts[2].isdigit():
            await callback.answer("Noto'g'ri amal.", show_alert=True)
            return

        action = parts[1]
        tg_id = int(parts[2])
        if tg_id == config.admin_id:
            await callback.answer('Adminni bu yerdan boshqarib bo‘lmaydi.', show_alert=True)
            return

        user = user_service.get_user_by_tg_id(tg_id)
        if not user or user.get('status') != 'pending':
            if callback.message:
                await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer('Bu so‘rov allaqachon ko‘rib chiqilgan.', show_alert=True)
            return

        if action == 'approve':
            ok = user_service.approve_user(tg_id)
            if not ok:
                await callback.answer('Foydalanuvchi topilmadi.', show_alert=True)
                return
            if callback.message:
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer(f'✅ Foydalanuvchi tasdiqlandi.\nID: {tg_id}', reply_markup=admin_panel_keyboard())
            try:
                await callback.bot.send_message(tg_id, '🎉 Siz tasdiqlandingiz. Botdan 1 oy davomida foydalanishingiz mumkin.')
            except Exception:
                pass
            await callback.answer('Tasdiqlandi')
            return

        if action == 'reject':
            ok = user_service.delete_user(tg_id)
            if not ok:
                await callback.answer('Foydalanuvchi topilmadi.', show_alert=True)
                return
            if callback.message:
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer(f'❌ So‘rov bekor qilindi.\nID: {tg_id}', reply_markup=admin_panel_keyboard())
            try:
                await callback.bot.send_message(tg_id, '❌ Tasdiqlash so‘rovingiz bekor qilindi.')
            except Exception:
                pass
            await callback.answer('Bekor qilindi')
            return

        await callback.answer("Noto'g'ri amal.", show_alert=True)

    @router.message(F.text == '✅ Tasdiqlangan foydalanuvchilar', admin_filter)
    async def approved_users(message: Message):
        users = user_service.get_approved_users()
        if not users:
            await message.answer('✅ Tasdiqlangan foydalanuvchilar mavjud emas.', reply_markup=back_to_admin_panel_keyboard())
            return
        await message.answer('✅ Tasdiqlangan foydalanuvchilar:', reply_markup=back_to_admin_panel_keyboard())
        for user in users:
            await message.answer(format_user_card(user))
        await message.answer('O‘chirish uchun “🗑 ID orqali o‘chirish” tugmasini bosing.', reply_markup=admin_panel_keyboard())

    @router.message(F.text == '👥 Barcha foydalanuvchilar', admin_filter)
    async def all_users(message: Message):
        users = user_service.get_all_users()
        if not users:
            await message.answer('👥 Foydalanuvchilar mavjud emas.', reply_markup=back_to_admin_panel_keyboard())
            return
        await message.answer('👥 Barcha foydalanuvchilar:', reply_markup=back_to_admin_panel_keyboard())
        for user in users:
            await message.answer(format_user_card(user))

    @router.message(F.text == '📊 Statistika', admin_filter)
    async def stats(message: Message):
        s = user_service.get_user_stats()
        text = (
            '📊 Statistika\n\n'
            f"👥 Jami foydalanuvchilar: {s['total']}\n"
            f"⏳ Tasdiqlash kutilayotganlar: {s['pending']}\n"
            f"✅ Faol foydalanuvchilar: {s['active']}\n"
            f"⌛ Muddati tugaganlar: {s['expired']}\n"
            f"🤖 Telegram ulanganlar: {s['telethon_connected']}\n"
            f"📡 Kuzatish yoqilganlar: {s['monitoring_enabled']}"
        )
        await message.answer(text, reply_markup=back_to_admin_panel_keyboard())

    @router.message(F.text == '🗑 ID orqali o‘chirish', admin_filter)
    async def ask_delete_id(message: Message, state: FSMContext):
        await state.set_state(AdminActionState.waiting_for_delete_user_id)
        await message.answer('O‘chirish uchun foydalanuvchi ID sini yuboring.', reply_markup=back_to_admin_panel_keyboard())

    @router.message(F.text == '✅ ID orqali tasdiqlash', admin_filter)
    async def ask_approve_id(message: Message, state: FSMContext):
        await state.set_state(AdminActionState.waiting_for_approve_user_id)
        await message.answer('Tasdiqlash uchun foydalanuvchi ID sini yuboring.', reply_markup=back_to_admin_panel_keyboard())

    @router.message(AdminActionState.waiting_for_delete_user_id, admin_filter)
    async def delete_user_by_id(message: Message, state: FSMContext):
        raw = (message.text or '').strip()
        if not raw.isdigit():
            await message.answer('Iltimos, faqat raqamdan iborat foydalanuvchi ID yuboring.')
            return
        tg_id = int(raw)
        ok = user_service.delete_user(tg_id)
        if not ok:
            await message.answer('Bunday ID ga ega foydalanuvchi topilmadi.', reply_markup=back_to_admin_panel_keyboard())
            return
        await state.clear()
        await message.answer(f'🗑 Foydalanuvchi o‘chirildi.\nID: {tg_id}', reply_markup=admin_panel_keyboard())
        try:
            await message.bot.send_message(tg_id, '⛔ Sizning akkauntingiz admin tomonidan o‘chirildi.')
        except Exception:
            pass

    @router.message(AdminActionState.waiting_for_approve_user_id, admin_filter)
    async def approve_user_by_id(message: Message, state: FSMContext):
        raw = (message.text or '').strip()
        if not raw.isdigit():
            await message.answer('Iltimos, faqat raqamdan iborat foydalanuvchi ID yuboring.')
            return
        tg_id = int(raw)
        ok = user_service.approve_user(tg_id)
        if not ok:
            await message.answer('Bunday ID ga ega foydalanuvchi topilmadi.', reply_markup=back_to_admin_panel_keyboard())
            return
        await state.clear()
        await message.answer(f'✅ Foydalanuvchi tasdiqlandi.\nID: {tg_id}', reply_markup=admin_panel_keyboard())
        try:
            await message.bot.send_message(tg_id, '🎉 Siz tasdiqlandingiz. Botdan 1 oy davomida foydalanishingiz mumkin.')
        except Exception:
            pass

    @router.message(Command('admin'))
    async def deny_non_admin(message: Message):
        await message.answer('Siz admin emassiz.')

    return router
