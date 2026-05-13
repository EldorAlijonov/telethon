from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Keyword


class KeywordRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_active(self, user_id: int) -> list[str]:
        result = await self.session.execute(
            select(Keyword.keyword).where(Keyword.user_id == user_id, Keyword.is_active.is_(True)).order_by(Keyword.keyword.asc())
        )
        return [row[0] for row in result.all()]

    async def add(self, user_id: int, keyword: str) -> bool:
        self.session.add(Keyword(user_id=user_id, keyword=keyword, is_active=True))
        try:
            await self.session.flush()
            return True
        except IntegrityError:
            await self.session.rollback()
            return False

    async def delete(self, user_id: int, keyword: str) -> bool:
        result = await self.session.execute(select(Keyword).where(Keyword.user_id == user_id, Keyword.keyword == keyword))
        item = result.scalar_one_or_none()
        if not item:
            return False
        await self.session.delete(item)
        return True

    async def rename(self, user_id: int, old_keyword: str, new_keyword: str) -> bool:
        result = await self.session.execute(select(Keyword).where(Keyword.user_id == user_id, Keyword.keyword == old_keyword))
        item = result.scalar_one_or_none()
        if not item:
            return False
        item.keyword = new_keyword
        try:
            await self.session.flush()
            return True
        except IntegrityError:
            await self.session.rollback()
            return False
