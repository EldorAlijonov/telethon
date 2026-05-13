from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

from app.db.models import User, UserStatus

TASHKENT_TZ = timezone(timedelta(hours=5), "Asia/Tashkent")
DISPLAY_DATETIME_FORMAT = "%Y-%m-%d %H:%M"
DISPLAY_DATETIME_SECONDS_FORMAT = "%Y-%m-%d %H:%M:%S"


def normalize_phone(phone: str) -> str:
    value = (phone or "").strip().replace(" ", "")
    if not value.startswith("+"):
        raise ValueError("Telefon raqami + bilan boshlanishi kerak.")
    if not value[1:].isdigit() or len(value) < 9 or len(value) > 16:
        raise ValueError("Telefon raqami noto'g'ri formatda.")
    return value


def dotted_code(digits: list[str]) -> str:
    return ".".join(digits) if digits else "_"


def user_status_text(user: User | None) -> str:
    if not user:
        return "Ro'yxatdan o'tmagan"
    if user.status == UserStatus.pending:
        return "Tasdiqlash kutilmoqda"
    if user.status == UserStatus.approved:
        if user.expires_at and user.expires_at > datetime.now(UTC):
            return "Faol"
        return "Muddati tugagan"
    if user.status == UserStatus.blocked:
        return "Bloklangan"
    if user.status == UserStatus.rejected:
        return "Rad etilgan"
    return "Muddati tugagan"


def format_username(username: str | None) -> str:
    return f"@{username}" if username else "mavjud emas"


def to_tashkent_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(TASHKENT_TZ)


def format_tashkent_time(value: datetime | None, *, seconds: bool = False) -> str:
    if value is None:
        return "-"
    fmt = DISPLAY_DATETIME_SECONDS_FORMAT if seconds else DISPLAY_DATETIME_FORMAT
    return to_tashkent_time(value).strftime(fmt)


def format_user_card(user: User) -> str:
    expires = format_tashkent_time(user.expires_at)
    approved = format_tashkent_time(user.approved_at)
    return (
        f"ID: <code>{user.tg_id}</code>\n"
        f"Ism: {user.full_name or '-'}\n"
        f"Username: {format_username(user.username)}\n"
        f"Telefon: {user.phone or 'mavjud emas'}\n"
        f"Holat: {user_status_text(user)}\n"
        f"Tasdiqlangan: {approved}\n"
        f"Tugash vaqti: {expires} (Toshkent)"
    )
