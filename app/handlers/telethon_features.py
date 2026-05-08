from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import telethon_connected_keyboard, telethon_state_keyboard, user_main_keyboard
from app.services.live_monitor_service import TelethonSessionInvalidError
from app.states.telethon_feature_states import TelethonFeatureState


CONTROL_BUTTONS = {
    '📡 Kuzatishni yoqish',
    '🛑 Kuzatishni o‘chirish',
    '📝 Kalit so‘zlarim',
    '➕ Kalit so‘z qo‘shish',
    '✏️ Kalit so‘zni tahrirlash',
    '🗑 Kalit so‘zni o‘chirish',
    '👥 Kuzatilayotgan chatlar',
    '🔓 Telegramdan chiqish',
    '❔ Funksiyalar yordami',
    '❌ Bekor qilish',
    '🔙 Funksiyalar menyusi',
}

STATEFUL_MENU_BUTTONS = {
    '📝 Kalit so‘zlarim',
    '➕ Kalit so‘z qo‘shish',
    '✏️ Kalit so‘zni tahrirlash',
    '🗑 Kalit so‘zni o‘chirish',
    '📡 Kuzatishni yoqish',
    '🛑 Kuzatishni o‘chirish',
    '👥 Kuzatilayotgan chatlar',
    '🔓 Telegramdan chiqish',
    '❔ Funksiyalar yordami',
}


def register_telethon_feature_handlers(user_service, keyword_service, monitor_service, live_monitor_service):
    router = Router()

    def allowed_and_connected(tg_id: int) -> tuple[bool, str]:
        if not user_service.is_user_allowed(tg_id):
            return False, '⛔ Foydalanish muddati tugagan yoki tasdiqlanmagansiz.'
        user = user_service.get_user_by_tg_id(tg_id)
        if not user or not user.get('telethon_session'):
            return False, 'Avval Telegram ulang.'
        return True, ''

    async def _cancel_state(message: Message, state: FSMContext, text: str = 'Amal bekor qilindi.') -> None:
        await state.clear()
        await message.answer(text, reply_markup=telethon_connected_keyboard())

    def _keywords_text(keywords: list[str]) -> str:
        if not keywords:
            return "📝 Sizning kalit so‘zlaringiz:\n\nHozircha kalit so‘zlar yo‘q."
        rows = '\n'.join(f'{i+1}. {k}' for i, k in enumerate(keywords))
        return (
            "📝 Sizning kalit so‘zlaringiz:\n\n"
            f"{rows}\n\n"
            "Kerak bo‘lsa, qo‘shish, tahrirlash yoki o‘chirish tugmalaridan foydalaning."
        )

    @router.message(StateFilter(TelethonFeatureState), F.text == '❌ Bekor qilish')
    async def cancel_any_state(message: Message, state: FSMContext):
        await _cancel_state(message, state)

    @router.message(StateFilter(TelethonFeatureState), F.text == '🔙 Funksiyalar menyusi')
    async def back_to_features_menu(message: Message, state: FSMContext):
        await _cancel_state(message, state, 'Funksiyalar menyusiga qaytdingiz.')

    @router.message(StateFilter(TelethonFeatureState), F.text.in_(STATEFUL_MENU_BUTTONS))
    async def interrupt_state_with_menu_button(message: Message, state: FSMContext):
        await _cancel_state(
            message,
            state,
            "Oldingi amal bekor qilindi. Tanlangan bo‘limni yana bir marta bosing.",
        )

    @router.message(F.text == '📝 Kalit so‘zlarim')
    async def my_keywords(message: Message):
        ok, error = allowed_and_connected(message.from_user.id)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        keyword_service.ensure_default_keywords(message.from_user.id)
        keywords = keyword_service.get_keywords(message.from_user.id)
        await message.answer(_keywords_text(keywords), reply_markup=telethon_connected_keyboard())

    @router.message(F.text == '➕ Kalit so‘z qo‘shish')
    async def add_keyword_start(message: Message, state: FSMContext):
        ok, error = allowed_and_connected(message.from_user.id)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        keyword_service.ensure_default_keywords(message.from_user.id)
        await state.set_state(TelethonFeatureState.waiting_keyword_add)
        await message.answer(
            "Qo‘shmoqchi bo‘lgan kalit so‘zni yuboring.\n\n"
            "Bekor qilish uchun ❌ Bekor qilish ni bosing.",
            reply_markup=telethon_state_keyboard(),
        )

    @router.message(TelethonFeatureState.waiting_keyword_add)
    async def add_keyword_finish(message: Message, state: FSMContext):
        text = (message.text or '').strip()
        if not text:
            await message.answer('Kalit so‘z bo‘sh bo‘lmasin.', reply_markup=telethon_state_keyboard())
            return
        if text in CONTROL_BUTTONS:
            await message.answer(
                "Iltimos, oddiy matn ko‘rinishida kalit so‘z yuboring yoki ❌ Bekor qilish ni bosing.",
                reply_markup=telethon_state_keyboard(),
            )
            return
        success, msg = keyword_service.add_keyword(message.from_user.id, text)
        if success:
            live_monitor_service.invalidate_keywords(message.from_user.id)
        await state.clear()
        await message.answer(msg, reply_markup=telethon_connected_keyboard())

    @router.message(F.text == '🗑 Kalit so‘zni o‘chirish')
    async def delete_keyword_start(message: Message, state: FSMContext):
        ok, error = allowed_and_connected(message.from_user.id)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        keyword_service.ensure_default_keywords(message.from_user.id)
        keywords = keyword_service.get_keywords(message.from_user.id)
        await state.set_state(TelethonFeatureState.waiting_keyword_delete)
        await message.answer(
            _keywords_text(keywords) + "\n\nO‘chirmoqchi bo‘lgan kalit so‘zni aynan yozib yuboring.",
            reply_markup=telethon_state_keyboard(),
        )

    @router.message(TelethonFeatureState.waiting_keyword_delete)
    async def delete_keyword_finish(message: Message, state: FSMContext):
        text = (message.text or '').strip()
        if not text:
            await message.answer('O‘chirish uchun kalit so‘z yuboring.', reply_markup=telethon_state_keyboard())
            return
        if text in CONTROL_BUTTONS:
            await message.answer(
                "Iltimos, o‘chirmoqchi bo‘lgan kalit so‘zni oddiy matn ko‘rinishida yuboring yoki ❌ Bekor qilish ni bosing.",
                reply_markup=telethon_state_keyboard(),
            )
            return
        deleted = keyword_service.delete_keyword(message.from_user.id, text)
        if deleted:
            live_monitor_service.invalidate_keywords(message.from_user.id)
        await state.clear()
        await message.answer(
            'Kalit so‘z o‘chirildi.' if deleted else 'Kalit so‘z topilmadi.',
            reply_markup=telethon_connected_keyboard(),
        )

    @router.message(F.text == '✏️ Kalit so‘zni tahrirlash')
    async def edit_keyword_start(message: Message, state: FSMContext):
        ok, error = allowed_and_connected(message.from_user.id)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        keyword_service.ensure_default_keywords(message.from_user.id)
        keywords = keyword_service.get_keywords(message.from_user.id)
        await state.set_state(TelethonFeatureState.waiting_keyword_edit_old)
        await message.answer(
            _keywords_text(keywords) + "\n\nEski kalit so‘zni yuboring.",
            reply_markup=telethon_state_keyboard(),
        )

    @router.message(TelethonFeatureState.waiting_keyword_edit_old)
    async def edit_keyword_old(message: Message, state: FSMContext):
        text = (message.text or '').strip()
        if not text:
            await message.answer('Eski kalit so‘zni yuboring.', reply_markup=telethon_state_keyboard())
            return
        if text in CONTROL_BUTTONS:
            await message.answer(
                "Iltimos, eski kalit so‘zni oddiy matn ko‘rinishida yuboring yoki ❌ Bekor qilish ni bosing.",
                reply_markup=telethon_state_keyboard(),
            )
            return
        await state.update_data(old_keyword=text)
        await state.set_state(TelethonFeatureState.waiting_keyword_edit_new)
        await message.answer(
            'Yangi kalit so‘zni yuboring.',
            reply_markup=telethon_state_keyboard(),
        )

    @router.message(TelethonFeatureState.waiting_keyword_edit_new)
    async def edit_keyword_new(message: Message, state: FSMContext):
        text = (message.text or '').strip()
        if not text:
            await message.answer('Yangi kalit so‘zni yuboring.', reply_markup=telethon_state_keyboard())
            return
        if text in CONTROL_BUTTONS:
            await message.answer(
                "Iltimos, yangi kalit so‘zni oddiy matn ko‘rinishida yuboring yoki ❌ Bekor qilish ni bosing.",
                reply_markup=telethon_state_keyboard(),
            )
            return
        data = await state.get_data()
        success, msg = keyword_service.edit_keyword(message.from_user.id, data.get('old_keyword', ''), text)
        if success:
            live_monitor_service.invalidate_keywords(message.from_user.id)
        await state.clear()
        await message.answer(msg, reply_markup=telethon_connected_keyboard())

    @router.message(F.text == '📡 Kuzatishni yoqish')
    async def start_monitor(message: Message):
        ok, error = allowed_and_connected(message.from_user.id)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        keyword_service.ensure_default_keywords(message.from_user.id)
        keywords = keyword_service.get_keywords(message.from_user.id)
        if not keywords:
            await message.answer('Avval kamida bitta kalit so‘z qo‘shing.', reply_markup=telethon_connected_keyboard())
            return
        success, msg = await live_monitor_service.start_monitoring(message.from_user.id, message.bot)
        await message.answer(msg, reply_markup=telethon_connected_keyboard())

    @router.message(F.text == '🛑 Kuzatishni o‘chirish')
    async def stop_monitor(message: Message):
        await live_monitor_service.stop_monitoring(message.from_user.id)
        await message.answer('Kuzatish o‘chirildi.', reply_markup=telethon_connected_keyboard())

    @router.message(F.text == '👥 Kuzatilayotgan chatlar')
    async def monitored_info(message: Message):
        ok, error = allowed_and_connected(message.from_user.id)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        enabled = monitor_service.is_enabled(message.from_user.id)
        try:
            titles = await live_monitor_service.list_dialog_titles(message.from_user.id)
        except TelethonSessionInvalidError:
            await message.answer(
                "Telegram ulanishingiz eskirgan. Iltimos, Telegramni qayta ulang.",
                reply_markup=user_main_keyboard(),
            )
            return
        txt = 'Kuzatish holati: yoqilgan\n\n' if enabled else 'Kuzatish holati: o‘chiq\n\n'
        txt += 'Ko‘rinib turgan chatlar:\n' + ('\n'.join(f'• {t}' for t in titles[:20]) if titles else 'Chatlar topilmadi.')
        await message.answer(txt, reply_markup=telethon_connected_keyboard())

    @router.message(F.text == '❔ Funksiyalar yordami')
    async def help_text(message: Message):
        ok, error = allowed_and_connected(message.from_user.id)
        if not ok:
            await message.answer(error, reply_markup=user_main_keyboard())
            return
        await message.answer(
            'Bu bo‘limda siz kalit so‘zlar qo‘shishingiz, ularni tahrirlashingiz, o‘chirishingiz va kuzatishni yoqib/o‘chirishingiz mumkin.\n\n'
            'Har qanday amal paytida ❌ Bekor qilish bilan chiqishingiz yoki 🔙 Funksiyalar menyusi bilan menyuga qaytishingiz mumkin.',
            reply_markup=telethon_connected_keyboard(),
        )

    @router.message(F.text == '🔓 Telegramdan chiqish')
    async def logout_telethon(message: Message, state: FSMContext):
        await state.clear()
        await live_monitor_service.stop_monitoring(message.from_user.id)
        user_service.clear_telethon_session(message.from_user.id)
        await message.answer('Telegram ulanishi uzildi.', reply_markup=user_main_keyboard())

    return router
