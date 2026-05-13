from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Approval, Subscription, User, UserStatus


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_user(self, tg_id: int, full_name: str | None, username: str | None, phone: str | None = None) -> User:
        user = await self.get_by_tg_id(tg_id)
        if user:
            user.full_name = full_name
            user.username = username
            if phone:
                user.phone = phone
            return user
        user = User(tg_id=tg_id, full_name=full_name, username=username, phone=phone, status=UserStatus.pending)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_tg_id(self, tg_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.tg_id == tg_id))
        return result.scalar_one_or_none()

    async def list_by_status(self, status: UserStatus, limit: int = 50) -> list[User]:
        result = await self.session.execute(select(User).where(User.status == status).order_by(User.id.desc()).limit(limit))
        return list(result.scalars())

    async def list_all(self, limit: int = 100) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.id.desc()).limit(limit))
        return list(result.scalars())

    async def approve(self, user: User, admin_tg_id: int, access_days: int) -> None:
        now = datetime.now(UTC)
        user.status = UserStatus.approved
        user.approved_at = now
        user.expires_at = now + timedelta(days=access_days)
        self.session.add(Approval(user_id=user.id, admin_tg_id=admin_tg_id, decision="approved", access_days=access_days))
        self.session.add(Subscription(user_id=user.id, expires_at=user.expires_at, is_active=True))

    async def block(self, user: User, admin_tg_id: int, reason: str | None = None) -> None:
        user.status = UserStatus.blocked
        self.session.add(Approval(user_id=user.id, admin_tg_id=admin_tg_id, decision="blocked", reason=reason))
        await self.session.execute(update(Subscription).where(Subscription.user_id == user.id).values(is_active=False))

    async def reject(self, user: User, admin_tg_id: int, reason: str | None = None) -> None:
        user.status = UserStatus.rejected
        self.session.add(Approval(user_id=user.id, admin_tg_id=admin_tg_id, decision="rejected", reason=reason))

    async def delete(self, user: User) -> None:
        await self.session.delete(user)

    async def mark_expired_users(self) -> int:
        result = await self.session.execute(
            update(User)
            .where(User.status == UserStatus.approved, User.expires_at < datetime.now(UTC))
            .values(status=UserStatus.expired)
        )
        return int(result.rowcount or 0)

    async def stats(self) -> dict[str, int]:
        rows = {}
        for status in UserStatus:
            result = await self.session.execute(select(func.count()).select_from(User).where(User.status == status))
            rows[status.value] = int(result.scalar_one())
        total = await self.session.scalar(select(func.count()).select_from(User))
        return {"total": int(total or 0), **rows}
