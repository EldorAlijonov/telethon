from __future__ import annotations

from datetime import UTC, datetime
from math import ceil

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

    async def set_signal_destination(self, tg_id: int, chat_id: int, title: str | None) -> bool:
        async with self.db.session() as session:
            repo = UserRepository(session)
            user = await repo.get_by_tg_id(tg_id)
            if not user:
                return False
            await repo.set_signal_destination(user, chat_id, title)
            return True

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
            return await UserRepository(session).list_by_status(UserStatus.approved, limit=10000)

    async def list_approved_with_active_sessions(self) -> list[User]:
        async with self.db.session() as session:
            repo = UserRepository(session)
            await repo.mark_expired_users()
            return await repo.list_approved_with_active_sessions()

    async def list_blocked(self) -> list[User]:
        async with self.db.session() as session:
            return await UserRepository(session).list_by_status(UserStatus.blocked)

    async def list_all(self) -> list[User]:
        async with self.db.session() as session:
            return await UserRepository(session).list_all()

    async def list_page(self, kind: str, page: int, page_size: int = 5) -> dict[str, object]:
        page = max(page, 1)
        page_size = max(1, min(page_size, 20))
        offset = (page - 1) * page_size
        status_by_kind = {
            "approved": UserStatus.approved,
            "blocked": UserStatus.blocked,
            "pending": UserStatus.pending,
            "all": None,
        }
        if kind not in status_by_kind:
            raise ValueError("Unknown user list kind")
        async with self.db.session() as session:
            repo = UserRepository(session)
            await repo.mark_expired_users()
            status = status_by_kind[kind]
            if status is None:
                total = await repo.count_all()
                users = await repo.list_all(limit=page_size, offset=offset)
            else:
                total = await repo.count_by_status(status)
                users = await repo.list_by_status(status, limit=page_size, offset=offset)
        total_pages = max(1, ceil(total / page_size))
        if page > total_pages:
            return await self.list_page(kind, total_pages, page_size)
        return {
            "users": users,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    async def stats(self) -> dict[str, int]:
        async with self.db.session() as session:
            repo = UserRepository(session)
            await repo.mark_expired_users()
            return await repo.stats()
