from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TelegramSession


class TelegramSessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> TelegramSession | None:
        result = await self.session.execute(select(TelegramSession).where(TelegramSession.user_id == user_id, TelegramSession.revoked_at.is_(None)))
        return result.scalar_one_or_none()

    async def save(self, user_id: int, phone: str, encrypted_session: str) -> TelegramSession:
        existing = await self.get_by_user_id(user_id)
        if existing:
            existing.phone = phone
            existing.encrypted_session = encrypted_session
            existing.connected_at = datetime.now(UTC)
            existing.revoked_at = None
            return existing
        item = TelegramSession(user_id=user_id, phone=phone, encrypted_session=encrypted_session)
        self.session.add(item)
        await self.session.flush()
        return item

    async def revoke(self, user_id: int) -> None:
        existing = await self.get_by_user_id(user_id)
        if existing:
            existing.revoked_at = datetime.now(UTC)
