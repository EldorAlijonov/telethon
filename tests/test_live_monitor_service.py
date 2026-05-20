from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.live_monitor_service import LiveMonitorService, SignalRoute


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
    service._signal_route = AsyncMock(return_value=None)

    await service._handle_event(tg_id=123, bot=bot, event=event, own_id=None)

    service._signal_route.assert_awaited_once_with(123, -100123)
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
    service._signal_route = AsyncMock(return_value=None)

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
    service._signal_route = AsyncMock(return_value=False)

    await service._handle_event(tg_id=123, bot=bot, event=event, own_id=None)

    service._signal_route.assert_awaited_once_with(123, -100123)
    keyword_service.list_keywords.assert_awaited_once_with(123)
    redis.set.assert_not_awaited()
    bot.send_message.assert_not_awaited()
    event.get_sender.assert_not_awaited()
    event.get_chat.assert_not_awaited()


def test_signal_text_and_buttons_keep_phone_in_text_without_phone_button():
    profile = {
        "name": "Test User",
        "username": "@test_user",
        "phone": "+998901234567",
        "profile_link": "https://t.me/test_user",
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
    assert buttons.inline_keyboard[0][0].url == "https://t.me/test_user"
    assert "+998901234567" in text
    assert len(buttons.inline_keyboard) == 2
    assert buttons.inline_keyboard[1][0].url == "https://t.me/test_chat/1"
    assert "Xabarni ochish" in buttons.inline_keyboard[1][0].text


def test_sender_profile_uses_private_chat_link_instead_of_profile_link():
    class Sender:
        id = 777
        first_name = "Test"
        last_name = "User"
        username = "test_user"
        phone = None

    profile = LiveMonitorService._sender_profile(Sender())

    assert profile["profile_link"] == "https://t.me/test_user"


def test_sender_profile_falls_back_to_openmessage_for_users_without_username_or_phone():
    class Sender:
        id = 777
        first_name = "Test"
        last_name = "User"
        username = None
        phone = None

    profile = LiveMonitorService._sender_profile(Sender())

    assert profile["profile_link"] is None


@pytest.mark.asyncio
async def test_signal_queue_receives_full_signal_payload(monkeypatch):
    class FakeDb:
        def session(self):
            return self

        async def __aenter__(self):
            return SimpleNamespace()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeUserRepository:
        def __init__(self, session):
            pass

        async def get_by_tg_id(self, tg_id):
            return SimpleNamespace(id=42, signal_destination_chat_id=-100999)

    class FakeMonitorRepository:
        def __init__(self, session):
            pass

        async def save_signal(self, **kwargs):
            return SimpleNamespace(id=123)

    class FakeDeliveryRepository:
        def __init__(self, session):
            pass

        async def create_pending(self, signal_id, target_chat_id):
            return SimpleNamespace(id=1)

        async def get_by_signal_recipient(self, signal_id, target_chat_id):
            return SimpleNamespace(id=1)

        async def mark_delivered(self, delivery):
            pass

    class FakeAuditRepository:
        def __init__(self, session):
            pass

        async def write(self, *args, **kwargs):
            pass

    monkeypatch.setattr("app.services.live_monitor_service.UserRepository", FakeUserRepository)
    monkeypatch.setattr("app.services.live_monitor_service.MonitorRepository", FakeMonitorRepository)
    monkeypatch.setattr("app.services.live_monitor_service.SignalDeliveryRepository", FakeDeliveryRepository)
    monkeypatch.setattr("app.services.live_monitor_service.AuditRepository", FakeAuditRepository)

    user_service = SimpleNamespace(is_allowed=AsyncMock(return_value=True))
    keyword_service = SimpleNamespace(list_keywords=AsyncMock(return_value=["signal"]))
    monitor_state = SimpleNamespace(is_enabled=AsyncMock(return_value=True))
    redis = SimpleNamespace(set=AsyncMock(return_value=True))
    signal_queue = SimpleNamespace(publish_signal=AsyncMock(), publish_retry=AsyncMock())
    bot = SimpleNamespace(send_message=AsyncMock())
    sender = SimpleNamespace(id=321, first_name="Test", last_name="Sender", username="sender_user", phone="+998901234567", bot=False)
    chat = SimpleNamespace(title="Source Chat", username="source_chat")
    message_at = datetime(2026, 5, 20, 10, 0)
    event = SimpleNamespace(
        out=False,
        chat_id=-100123,
        sender_id=321,
        raw_text="This message contains signal",
        message=SimpleNamespace(id=777, date=message_at),
        get_sender=AsyncMock(return_value=sender),
        get_chat=AsyncMock(return_value=chat),
    )
    service = LiveMonitorService(
        api_id=1,
        api_hash="hash",
        db=FakeDb(),
        redis=redis,
        auth_service=SimpleNamespace(),
        user_service=user_service,
        keyword_service=keyword_service,
        monitor_state=monitor_state,
        signal_queue=signal_queue,
        blacklist_ids=set(),
        dedupe_ttl=60,
    )
    service._signal_route = AsyncMock(return_value=SignalRoute(user_id=42, target_chat_id=-100999))

    await service._handle_event(tg_id=123, bot=bot, event=event, own_id=None)

    payload = signal_queue.publish_signal.await_args.args[0]
    assert payload["signal_id"] == 123
    assert payload["tg_id"] == 123
    assert payload["target_chat_id"] == -100999
    assert payload["chat_id"] == -100123
    assert payload["message_id"] == 777
    assert payload["matched_text"] == "This message contains signal"
    assert payload["source_chat"] == "Source Chat"
    assert payload["sender_name"] == "Test Sender"
    assert payload["sender_username"] == "@sender_user"
    assert payload["sender_phone"] == "+998901234567"
    assert payload["sender_profile_link"] == "https://t.me/sender_user"
    assert payload["message_link"] == "https://t.me/source_chat/777"
    assert payload["message_at"] == message_at.isoformat()
    assert payload["delivered"] == 1
    assert payload["delivery_error"] is None
