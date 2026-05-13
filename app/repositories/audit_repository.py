from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditAction, AuditLog


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def write(self, action: AuditAction, actor_tg_id: int | None = None, target_tg_id: int | None = None, details: dict | None = None) -> None:
        self.session.add(AuditLog(action=action, actor_tg_id=actor_tg_id, target_tg_id=target_tg_id, details=details or {}))
