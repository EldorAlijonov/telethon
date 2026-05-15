from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MonitoredChat, Signal


class MonitorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_chat(self, user_id: int, chat_id: int, title: str | None, username: str | None, active: bool = True) -> None:
        result = await self.session.execute(select(MonitoredChat).where(MonitoredChat.user_id == user_id, MonitoredChat.chat_id == chat_id))
        chat = result.scalar_one_or_none()
        if chat:
            chat.title = title
            chat.username = username
            chat.is_active = active
            return
        self.session.add(MonitoredChat(user_id=user_id, chat_id=chat_id, title=title, username=username, is_active=active))

    async def list_active_chats(self, user_id: int, limit: int = 100) -> list[MonitoredChat]:
        result = await self.session.execute(
            select(MonitoredChat).where(MonitoredChat.user_id == user_id, MonitoredChat.is_active.is_(True)).order_by(MonitoredChat.title.asc()).limit(limit)
        )
        return list(result.scalars())

    async def is_chat_blocked(self, user_id: int, chat_id: int) -> bool:
        result = await self.session.execute(
            select(MonitoredChat.is_active).where(MonitoredChat.user_id == user_id, MonitoredChat.chat_id == chat_id)
        )
        is_active = result.scalar_one_or_none()
        return is_active is False

    async def save_signal(
        self,
        user_id: int,
        chat_id: int,
        message_id: int,
        keyword: str,
        matched_text: str,
        source_chat: str | None,
        sender_info: str | None,
        message_link: str | None,
        message_at,
    ) -> Signal | None:
        signal = Signal(
                user_id=user_id,
                chat_id=chat_id,
                message_id=message_id,
                keyword=keyword,
                matched_text=matched_text,
                source_chat=source_chat,
                sender_info=sender_info,
                message_link=message_link,
                message_at=message_at,
            )
        self.session.add(signal)
        try:
            await self.session.flush()
            return signal
        except Exception:
            await self.session.rollback()
            return None
