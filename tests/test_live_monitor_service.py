from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.live_monitor_service import LiveMonitorService


@pytest.mark.asyncio
async def test_expired_user_receives_subscription_notice_instead_of_signal():
    user_service = SimpleNamespace(is_allowed=AsyncMock(return_value=False))
    keyword_service = SimpleNamespace(list_keywords=AsyncMock(return_value=["signal"]))
    monitor_state = SimpleNamespace(is_enabled=AsyncMock(return_value=True))
    redis = SimpleNamespace(set=AsyncMock(return_value=True))
    bot = SimpleNamespace(send_message=AsyncMock())
    event = SimpleNamespace(
        out=False,
        chat_id=-100123,
        sender_id=321,
        raw_text="This message contains signal",
        message=SimpleNamespace(id=777),
        get_sender=AsyncMock(),
        get_chat=AsyncMock(),
    )
    service = LiveMonitorService(
        api_id=1,
        api_hash="hash",
        db=SimpleNamespace(),
        redis=redis,
        auth_service=SimpleNamespace(),
        user_service=user_service,
        keyword_service=keyword_service,
        monitor_state=monitor_state,
        signal_queue=SimpleNamespace(),
        blacklist_ids=set(),
        dedupe_ttl=60,
    )
    service._is_chat_ignored = AsyncMock(return_value=False)

    await service._handle_event(tg_id=123, bot=bot, event=event, own_id=None)

    user_service.is_allowed.assert_awaited_once_with(123)
    redis.set.assert_awaited_once_with("subscription:expired_notice:123", "1", ex=86400, nx=True)
    bot.send_message.assert_awaited_once()
    assert "Foydalanish muddati tugagan" in bot.send_message.await_args.args[1]
    event.get_sender.assert_not_awaited()
    event.get_chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_expired_user_notice_is_deduped():
    user_service = SimpleNamespace(is_allowed=AsyncMock(return_value=False))
    keyword_service = SimpleNamespace(list_keywords=AsyncMock(return_value=["signal"]))
    monitor_state = SimpleNamespace(is_enabled=AsyncMock(return_value=True))
    redis = SimpleNamespace(set=AsyncMock(return_value=False))
    bot = SimpleNamespace(send_message=AsyncMock())
    event = SimpleNamespace(
        out=False,
        chat_id=-100123,
        sender_id=321,
        raw_text="This message contains signal",
        message=SimpleNamespace(id=777),
        get_sender=AsyncMock(),
        get_chat=AsyncMock(),
    )
    service = LiveMonitorService(
        api_id=1,
        api_hash="hash",
        db=SimpleNamespace(),
        redis=redis,
        auth_service=SimpleNamespace(),
        user_service=user_service,
        keyword_service=keyword_service,
        monitor_state=monitor_state,
        signal_queue=SimpleNamespace(),
        blacklist_ids=set(),
        dedupe_ttl=60,
    )
    service._is_chat_ignored = AsyncMock(return_value=False)

    await service._handle_event(tg_id=123, bot=bot, event=event, own_id=None)

    bot.send_message.assert_not_awaited()
    event.get_sender.assert_not_awaited()
    event.get_chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_ignored_destination_chat_is_not_processed():
    user_service = SimpleNamespace(is_allowed=AsyncMock(return_value=True))
    keyword_service = SimpleNamespace(list_keywords=AsyncMock(return_value=["signal"]))
    monitor_state = SimpleNamespace(is_enabled=AsyncMock(return_value=True))
    redis = SimpleNamespace(set=AsyncMock(return_value=True))
    bot = SimpleNamespace(send_message=AsyncMock())
    event = SimpleNamespace(
        out=False,
        chat_id=-100123,
        sender_id=321,
        raw_text="This message contains signal",
        message=SimpleNamespace(id=777),
        get_sender=AsyncMock(),
        get_chat=AsyncMock(),
    )
    service = LiveMonitorService(
        api_id=1,
        api_hash="hash",
        db=SimpleNamespace(),
        redis=redis,
        auth_service=SimpleNamespace(),
        user_service=user_service,
        keyword_service=keyword_service,
        monitor_state=monitor_state,
        signal_queue=SimpleNamespace(),
        blacklist_ids=set(),
        dedupe_ttl=60,
    )
    service._is_chat_ignored = AsyncMock(return_value=True)

    await service._handle_event(tg_id=123, bot=bot, event=event, own_id=None)

    service._is_chat_ignored.assert_awaited_once_with(123, -100123)
    keyword_service.list_keywords.assert_not_awaited()
    redis.set.assert_not_awaited()
    bot.send_message.assert_not_awaited()
    event.get_sender.assert_not_awaited()
    event.get_chat.assert_not_awaited()


def test_signal_text_and_buttons_use_lichka_and_phone_button():
    profile = {
        "name": "Test User",
        "username": "@test_user",
        "phone": "+998901234567",
        "profile_link": "tg://resolve?domain=test_user",
    }

    text = LiveMonitorService._signal_text(
        1,
        "signal",
        "signal bor",
        "Test chat",
        profile,
        datetime.now(),
        "https://t.me/test_chat/1",
    )
    buttons = LiveMonitorService._signal_buttons(profile, "https://t.me/test_chat/1")

    assert "Lichkani ochish" in text
    assert buttons is not None
    assert "💬 <b>Yangi signal topildi</b>" in text
    assert "👤 <b>Yozgan:</b>" in text
    assert "🔑 <b>Topilgan kalit so'z:</b>" in text
    assert buttons.inline_keyboard[0][0].text == "👤 Lichkani ochish"
    assert buttons.inline_keyboard[1][0].text == "📞 Tel qilish: +998901234567"
    assert buttons.inline_keyboard[1][0].url == "tel:+998901234567"
    assert buttons.inline_keyboard[2][0].text == "🔗 Xabarni ochish"


def test_sender_profile_uses_private_chat_link_instead_of_profile_link():
    class Sender:
        id = 777
        first_name = "Test"
        last_name = "User"
        username = "test_user"
        phone = None

    profile = LiveMonitorService._sender_profile(Sender())

    assert profile["profile_link"] == "tg://resolve?domain=test_user"


def test_sender_profile_falls_back_to_openmessage_for_users_without_username_or_phone():
    class Sender:
        id = 777
        first_name = "Test"
        last_name = "User"
        username = None
        phone = None

    profile = LiveMonitorService._sender_profile(Sender())

    assert profile["profile_link"] == "tg://openmessage?user_id=777"
