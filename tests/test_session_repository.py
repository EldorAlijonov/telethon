from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.db.models import TelegramSession
from app.repositories.session_repository import TelegramSessionRepository


@pytest.mark.asyncio
async def test_save_reactivates_existing_revoked_session():
    existing = TelegramSession(
        user_id=1,
        phone="+998900000000",
        encrypted_session="old",
        revoked_at=datetime(2026, 5, 18, tzinfo=UTC),
    )
    result = SimpleNamespace(scalar_one_or_none=Mock(return_value=existing))
    session = SimpleNamespace(execute=AsyncMock(return_value=result), add=Mock(), flush=AsyncMock())

    saved = await TelegramSessionRepository(session).save(1, "+998911111111", "new")

    assert saved is existing
    assert existing.phone == "+998911111111"
    assert existing.encrypted_session == "new"
    assert existing.revoked_at is None
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
