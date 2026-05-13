from datetime import UTC, datetime

from app.db.models import User, UserStatus
from app.services.keyword_service import KeywordService
from app.services.subscription_service import SubscriptionGuardService
from app.utils import format_tashkent_time, format_user_card, normalize_phone
import pytest


def test_keyword_normalization():
    assert KeywordService.normalize("  Ish   kerak  ") == "ish kerak"


def test_phone_validation_accepts_e164_like_value():
    assert normalize_phone("+998901234567") == "+998901234567"


def test_tashkent_time_formatter_converts_utc():
    value = datetime(2026, 5, 13, 8, 49, 33, tzinfo=UTC)
    assert format_tashkent_time(value, seconds=True) == "2026-05-13 13:49:33"


def test_user_card_displays_tashkent_time():
    user = User(
        tg_id=1,
        full_name="Test User",
        username="test",
        phone="+998901234567",
        status=UserStatus.approved,
        approved_at=datetime(2026, 5, 13, 8, 0, tzinfo=UTC),
        expires_at=datetime(2026, 5, 14, 8, 0, tzinfo=UTC),
    )

    card = format_user_card(user)

    assert "Tasdiqlangan: 2026-05-13 13:00" in card
    assert "Tugash vaqti: 2026-05-14 13:00 (Toshkent)" in card


@pytest.mark.asyncio
async def test_subscription_guard_allows_admin_without_bot_call():
    guard = SubscriptionGuardService(["@required_channel"], {10})
    ok, text = await guard.ensure_allowed(bot=None, tg_id=10)
    assert ok
    assert text == ""
