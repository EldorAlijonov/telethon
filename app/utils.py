from __future__ import annotations

from datetime import UTC, datetime, timedelta

DT_FORMAT = '%Y-%m-%d %H:%M:%S'


def now_dt() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def now_str() -> str:
    return now_dt().strftime(DT_FORMAT)


def add_30_days_str() -> str:
    return (now_dt() + timedelta(days=30)).strftime(DT_FORMAT)


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, DT_FORMAT)
    except ValueError:
        return None


def is_subscription_active(expires_at: str | None) -> bool:
    dt = parse_dt(expires_at)
    return bool(dt and dt >= now_dt())


def user_status_text(user: dict) -> str:
    status = user.get('status')
    if status == 'pending':
        return 'Tasdiqlash kutilmoqda'
    if status == 'approved':
        return 'Tasdiqlandi' if is_subscription_active(user.get('expires_at')) else 'Muddati tugagan'
    if status == 'expired':
        return 'Muddati tugagan'
    return 'Noma\'lum'


def format_username(username: str | None) -> str:
    if not username:
        return 'mavjud emas'
    return username if username.startswith('@') else f'@{username}'


def format_user_card(user: dict) -> str:
    return (
        f"🆔 ID: <code>{user['tg_id']}</code>\n"
        f"👤 Ism: {user.get('full_name') or '-'}\n"
        f"🔗 Username: {format_username(user.get('username'))}\n"
        f"📞 Telefon: {user.get('phone') or 'mavjud emas'}\n"
        f"📌 Holati: {user_status_text(user)}\n"
        f"🕒 Tasdiqlangan vaqt: {user.get('approved_at') or '-'}\n"
        f"⌛ Tugash vaqti: {user.get('expires_at') or '-'}\n"
        f"🤖 Telegram: {'Ulangan' if user.get('telethon_session') else 'Ulanmagan'}"
    )


def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(' ', '')
    if not phone.startswith('+'):
        raise ValueError('Telefon raqami + bilan boshlanishi kerak')
    digits = phone[1:]
    if not digits.isdigit() or len(digits) < 8:
        raise ValueError('Telefon raqami noto\'g\'ri')
    return phone


def dotted_code(digits: list[str]) -> str:
    return '.'.join(digits) if digits else '_'
