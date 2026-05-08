from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def contact_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📱 Telefon raqamni ulashish', request_contact=True)],
            [KeyboardButton(text='ℹ️ Yordam')],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder='Telefon raqamingizni yuboring',
    )


def user_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📨 Tasdiqlash holati'), KeyboardButton(text='🤖 Telegram ulash')],
            [KeyboardButton(text='📱 Raqamni yangilash'), KeyboardButton(text="🔄 So'rovni qayta yuborish")],
            [KeyboardButton(text='ℹ️ Yordam')],
        ],
        resize_keyboard=True,
    )


def telethon_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📱 Telegram uchun raqam yuborish', request_contact=True)],
            [KeyboardButton(text='❌ Bekor qilish')],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def telethon_connected_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='📡 Kuzatishni yoqish'), KeyboardButton(text='🛑 Kuzatishni o‘chirish')],
            [KeyboardButton(text='📝 Kalit so‘zlarim'), KeyboardButton(text='➕ Kalit so‘z qo‘shish')],
            [KeyboardButton(text='✏️ Kalit so‘zni tahrirlash'), KeyboardButton(text='🗑 Kalit so‘zni o‘chirish')],
            [KeyboardButton(text='👥 Kuzatilayotgan chatlar'), KeyboardButton(text='🔓 Telegramdan chiqish')],
            [KeyboardButton(text='❔ Funksiyalar yordami')],
        ],
        resize_keyboard=True,
        input_field_placeholder='Telegram funksiyalaridan birini tanlang',
    )


def telethon_state_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='❌ Bekor qilish'), KeyboardButton(text='🔙 Funksiyalar menyusi')],
        ],
        resize_keyboard=True,
        input_field_placeholder='Amalni tugatish yoki bekor qilish mumkin',
    )


def admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='🛠 Admin panel')]],
        resize_keyboard=True,
    )


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='⏳ Tasdiqlash kutilayotganlar'), KeyboardButton(text='✅ Tasdiqlangan foydalanuvchilar')],
            [KeyboardButton(text='👥 Barcha foydalanuvchilar'), KeyboardButton(text='📊 Statistika')],
            [KeyboardButton(text='🗑 ID orqali o‘chirish'), KeyboardButton(text='✅ ID orqali tasdiqlash')],
            [KeyboardButton(text='⬅️ Admin panelga qaytish')],
        ],
        resize_keyboard=True,
    )


def back_to_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text='⬅️ Admin panelga qaytish')]],
        resize_keyboard=True,
    )


def pending_user_action_keyboard(tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='✅ Tasdiqlash', callback_data=f'admin_pending:approve:{tg_id}'),
                InlineKeyboardButton(text='❌ Bekor qilish', callback_data=f'admin_pending:reject:{tg_id}'),
            ],
        ],
    )


def telethon_code_keyboard(digits: list[str]) -> InlineKeyboardMarkup:
    entered = '.'.join(digits) if digits else '_'
    rows = [
        [InlineKeyboardButton(text=f'Kod: {entered}', callback_data='telethon:noop')],
        [
            InlineKeyboardButton(text='1', callback_data='telethon:digit:1'),
            InlineKeyboardButton(text='2', callback_data='telethon:digit:2'),
            InlineKeyboardButton(text='3', callback_data='telethon:digit:3'),
        ],
        [
            InlineKeyboardButton(text='4', callback_data='telethon:digit:4'),
            InlineKeyboardButton(text='5', callback_data='telethon:digit:5'),
            InlineKeyboardButton(text='6', callback_data='telethon:digit:6'),
        ],
        [
            InlineKeyboardButton(text='7', callback_data='telethon:digit:7'),
            InlineKeyboardButton(text='8', callback_data='telethon:digit:8'),
            InlineKeyboardButton(text='9', callback_data='telethon:digit:9'),
        ],
        [
            InlineKeyboardButton(text='⬅️', callback_data='telethon:back'),
            InlineKeyboardButton(text='0', callback_data='telethon:digit:0'),
            InlineKeyboardButton(text='🧹', callback_data='telethon:clear'),
        ],
        [
            InlineKeyboardButton(text='✅ Tasdiqlash', callback_data='telethon:submit'),
            InlineKeyboardButton(text='❌ Bekor qilish', callback_data='telethon:cancel'),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
