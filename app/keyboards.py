from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


BTN_STATUS = "📋 Hisob holati"
BTN_ACCOUNT_MENU = "👤 Hisob"
BTN_CONNECT = "🔐 Telegram ulash"
BTN_UPDATE_PHONE = "📱 Raqamni yangilash"
BTN_RESEND = "🔄 So'rovni qayta yuborish"
BTN_HELP = "❓ Yordam"
BTN_MONITOR_MENU = "📡 Monitoring"
BTN_MONITOR_ON = "🟢 Monitoringni yoqish"
BTN_MONITOR_OFF = "🔴 Monitoringni o'chirish"
BTN_KEYWORD_MENU = "🔑 Kalit so'zlar"
BTN_KEYWORDS = "📝 Kalit so'zlarim"
BTN_ADD_KEYWORD = "➕ Kalit so'z qo'shish"
BTN_EDIT_KEYWORD = "✏️ Kalit so'zni tahrirlash"
BTN_DELETE_KEYWORD = "🗑 Kalit so'zni o'chirish"
BTN_CHATS = "👥 Kuzatilayotgan chatlar"
BTN_LOGOUT = "🚪 Telegramdan chiqish"
BTN_CANCEL = "❌ Bekor qilish"
BTN_FEATURES = "🔙 Funksiyalar menyusi"
BTN_MAIN_MENU = "🏠 Asosiy menyu"

BTN_ADMIN = "🛠 Admin panel"
BTN_ADMIN_USERS_MENU = "👥 Foydalanuvchilar"
BTN_ADMIN_CONTROL_MENU = "🧭 Boshqaruv"
BTN_ADMIN_SYSTEM_MENU = "⚙️ Tizim"
BTN_PENDING = "⏳ Kutilayotganlar"
BTN_APPROVED = "✅ Tasdiqlanganlar"
BTN_BLOCKED = "🚫 Bloklanganlar"
BTN_ALL = "👥 Barcha foydalanuvchilar"
BTN_STATS = "📊 Statistika"
BTN_BROADCAST = "📣 Broadcast"
BTN_HEALTH = "🩺 System health"
BTN_MONITORING = "📡 Monitoring nazorati"
BTN_APPROVE_ID = "✅ ID orqali tasdiqlash"
BTN_BLOCK_ID = "🚫 ID orqali bloklash"
BTN_DELETE_ID = "🗑 ID orqali o'chirish"
BTN_BACK_ADMIN = "⬅️ Admin panelga qaytish"


def contact_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni ulashish", request_contact=True)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Telefon raqamingizni yuboring",
    )


def user_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ACCOUNT_MENU), KeyboardButton(text=BTN_CONNECT)],
            [KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Bo'limni tanlang",
    )


def user_account_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATUS)],
            [KeyboardButton(text=BTN_CONNECT)],
            [KeyboardButton(text=BTN_UPDATE_PHONE), KeyboardButton(text=BTN_RESEND)],
            [KeyboardButton(text=BTN_MAIN_MENU), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Hisob bo'limi",
    )


def telethon_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telegram uchun raqam yuborish", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def telethon_connected_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MONITOR_MENU), KeyboardButton(text=BTN_KEYWORD_MENU)],
            [KeyboardButton(text=BTN_ACCOUNT_MENU), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Bo'limni tanlang",
    )


def monitoring_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CHATS)],
            [KeyboardButton(text=BTN_MONITOR_ON), KeyboardButton(text=BTN_MONITOR_OFF)],
            [KeyboardButton(text=BTN_MAIN_MENU), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Monitoring boshqaruvi",
    )


def keyword_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_KEYWORDS), KeyboardButton(text=BTN_ADD_KEYWORD)],
            [KeyboardButton(text=BTN_EDIT_KEYWORD), KeyboardButton(text=BTN_DELETE_KEYWORD)],
            [KeyboardButton(text=BTN_MAIN_MENU), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Kalit so'zlarni boshqarish",
    )


def connected_account_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATUS)],
            [KeyboardButton(text=BTN_LOGOUT)],
            [KeyboardButton(text=BTN_MAIN_MENU), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Hisob sozlamalari",
    )


def telethon_state_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL), KeyboardButton(text=BTN_FEATURES)]], resize_keyboard=True)


def admin_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADMIN_USERS_MENU)],
            [KeyboardButton(text=BTN_ADMIN_CONTROL_MENU), KeyboardButton(text=BTN_ADMIN_SYSTEM_MENU)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin bo'limini tanlang",
    )


def admin_users_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_PENDING), KeyboardButton(text=BTN_APPROVED)],
            [KeyboardButton(text=BTN_BLOCKED), KeyboardButton(text=BTN_ALL)],
            [KeyboardButton(text=BTN_APPROVE_ID), KeyboardButton(text=BTN_BLOCK_ID)],
            [KeyboardButton(text=BTN_DELETE_ID)],
            [KeyboardButton(text=BTN_BACK_ADMIN)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Foydalanuvchilar",
    )


def admin_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CANCEL)],
            [KeyboardButton(text=BTN_BACK_ADMIN)],
        ],
        resize_keyboard=True,
    )


def admin_control_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MONITORING), KeyboardButton(text=BTN_BROADCAST)],
            [KeyboardButton(text=BTN_BACK_ADMIN)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Boshqaruv",
    )


def admin_system_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_HEALTH)],
            [KeyboardButton(text=BTN_BACK_ADMIN)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Tizim va statistika",
    )


def back_to_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_BACK_ADMIN)]], resize_keyboard=True)


def pending_user_action_keyboard(tg_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"admin_user:approve:{tg_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin_user:reject:{tg_id}"),
            ],
            [
                InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"admin_user:block:{tg_id}"),
            ],
        ]
    )


def admin_user_list_pagination_keyboard(
    kind: str,
    page: int,
    total_pages: int,
    pending_user_ids: list[int] | None = None,
) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    for tg_id in pending_user_ids or []:
        rows.append(
            [
                InlineKeyboardButton(text=f"Tasdiqlash {tg_id}", callback_data=f"admin_user:approve:{tg_id}"),
                InlineKeyboardButton(text=f"Bekor {tg_id}", callback_data=f"admin_user:reject:{tg_id}"),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(text=f"Bloklash {tg_id}", callback_data=f"admin_user:block:{tg_id}"),
            ]
        )

    if total_pages <= 1:
        if rows:
            return InlineKeyboardMarkup(inline_keyboard=rows)
        return None

    page = max(1, min(page, total_pages))
    start = max(1, page - 2)
    end = min(total_pages, start + 4)
    start = max(1, end - 4)

    nav_buttons: list[InlineKeyboardButton] = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="Oldingi", callback_data=f"admin_users:list:{kind}:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="Keyingi", callback_data=f"admin_users:list:{kind}:{page + 1}"))

    page_buttons = [
        InlineKeyboardButton(
            text=f"[{number}]" if number == page else str(number),
            callback_data="admin_users:noop" if number == page else f"admin_users:list:{kind}:{number}",
        )
        for number in range(start, end + 1)
    ]

    rows.append(page_buttons)
    if nav_buttons:
        rows.append(nav_buttons)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def telethon_code_keyboard(digits: list[str]) -> InlineKeyboardMarkup:
    entered = ".".join(digits) if digits else "_"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"🔢 Kod: {entered}", callback_data="telethon:noop")],
            [InlineKeyboardButton(text="1", callback_data="telethon:digit:1"), InlineKeyboardButton(text="2", callback_data="telethon:digit:2"), InlineKeyboardButton(text="3", callback_data="telethon:digit:3")],
            [InlineKeyboardButton(text="4", callback_data="telethon:digit:4"), InlineKeyboardButton(text="5", callback_data="telethon:digit:5"), InlineKeyboardButton(text="6", callback_data="telethon:digit:6")],
            [InlineKeyboardButton(text="7", callback_data="telethon:digit:7"), InlineKeyboardButton(text="8", callback_data="telethon:digit:8"), InlineKeyboardButton(text="9", callback_data="telethon:digit:9")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="telethon:back"), InlineKeyboardButton(text="0", callback_data="telethon:digit:0"), InlineKeyboardButton(text="🧹 Tozalash", callback_data="telethon:clear")],
            [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="telethon:submit"), InlineKeyboardButton(text="❌ Bekor qilish", callback_data="telethon:cancel")],
        ]
    )
