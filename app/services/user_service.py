from __future__ import annotations

from datetime import UTC, datetime

from app.db.models import AuditAction, User, UserStatus
from app.db.session import Database
from app.repositories.audit_repository import AuditRepository
from app.repositories.session_repository import TelegramSessionRepository
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Database, default_access_days: int):
        self.db = db
        self.default_access_days = default_access_days

    async def register_or_update(self, tg_id: int, full_name: str | None, username: str | None, phone: str | None = None) -> User:
        async with self.db.session() as session:
            repo = UserRepository(session)
            user = await repo.upsert_user(tg_id, full_name, username, phone)
            await AuditRepository(session).write(AuditAction.user_registered, target_tg_id=tg_id)
            return user

    async def get(self, tg_id: int) -> User | None:
        async with self.db.session() as session:
            return await UserRepository(session).get_by_tg_id(tg_id)

    async def is_allowed(self, tg_id: int) -> bool:
        async with self.db.session() as session:
            repo = UserRepository(session)
            await repo.mark_expired_users()
            user = await repo.get_by_tg_id(tg_id)
            return bool(user and user.status == UserStatus.approved and user.expires_at and user.expires_at > datetime.now(UTC))

    async def approve(self, tg_id: int, admin_tg_id: int, access_days: int | None = None) -> bool:
        async with self.db.session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_tg_id(tg_id)
            if not user:
                return False
            days = access_days or self.default_access_days
            await repo.approve(user, admin_tg_id, days)
            await AuditRepository(session).write(AuditAction.user_approved, actor_tg_id=admin_tg_id, target_tg_id=tg_id, details={"access_days": days})
            return True

    async def block(self, tg_id: int, admin_tg_id: int, reason: str | None = None) -> bool:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return False
            await TelegramSessionRepository(session).revoke(user.id)
            await UserRepository(session).block(user, admin_tg_id, reason)
            await AuditRepository(session).write(AuditAction.user_blocked, actor_tg_id=admin_tg_id, target_tg_id=tg_id, details={"reason": reason})
            return True

    async def reject(self, tg_id: int, admin_tg_id: int, reason: str | None = None) -> bool:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return False
            await UserRepository(session).reject(user, admin_tg_id, reason)
            await AuditRepository(session).write(AuditAction.user_rejected, actor_tg_id=admin_tg_id, target_tg_id=tg_id, details={"reason": reason})
            return True

    async def delete(self, tg_id: int, admin_tg_id: int, reason: str | None = None) -> bool:
        async with self.db.session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_tg_id(tg_id)
            if not user:
                return False
            await TelegramSessionRepository(session).revoke(user.id)
            await AuditRepository(session).write(AuditAction.user_deleted, actor_tg_id=admin_tg_id, target_tg_id=tg_id, details={"reason": reason})
            await repo.delete(user)
            return True

    async def list_pending(self) -> list[User]:
        async with self.db.session() as session:
            return await UserRepository(session).list_by_status(UserStatus.pending)

    async def list_approved(self) -> list[User]:
        async with self.db.session() as session:
            return await UserRepository(session).list_by_status(UserStatus.approved)

    async def list_blocked(self) -> list[User]:
        async with self.db.session() as session:
            return await UserRepository(session).list_by_status(UserStatus.blocked)

    async def list_all(self) -> list[User]:
        async with self.db.session() as session:
            return await UserRepository(session).list_all()

    async def stats(self) -> dict[str, int]:
        async with self.db.session() as session:
            repo = UserRepository(session)
            await repo.mark_expired_users()
            return await repo.stats()
