from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.live_monitor_service import LiveMonitorService


@pytest.mark.asyncio
async def test_expired_user_does_not_receive_matching_signal():
    user_service = SimpleNamespace(is_allowed=AsyncMock(return_value=False))
    keyword_service = SimpleNamespace(list_keywords=AsyncMock(return_value=["signal"]))
    monitor_state = SimpleNamespace(is_enabled=AsyncMock(return_value=True))
    redis = SimpleNamespace(set=AsyncMock())
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
    service._is_chat_blocked = AsyncMock(return_value=False)

    await service._handle_event(tg_id=123, bot=bot, event=event, own_id=None)

    user_service.is_allowed.assert_awaited_once_with(123)
    bot.send_message.assert_not_awaited()
    redis.set.assert_not_awaited()
    event.get_sender.assert_not_awaited()
    event.get_chat.assert_not_awaited()
