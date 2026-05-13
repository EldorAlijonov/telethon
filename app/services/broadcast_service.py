from __future__ import annotations

import asyncio

import structlog
from aiogram import Bot

from app.db.models import AuditAction
from app.db.session import Database
from app.repositories.audit_repository import AuditRepository
from app.repositories.broadcast_repository import BroadcastRepository
from app.services.user_service import UserService

logger = structlog.get_logger(__name__)


class BroadcastService:
    def __init__(self, db: Database, user_service: UserService):
        self.db = db
        self.user_service = user_service

    async def send_to_approved_users(self, bot: Bot, admin_tg_id: int, text: str) -> dict[str, int]:
        users = await self.user_service.list_approved()
        async with self.db.session() as session:
            repo = BroadcastRepository(session)
            job = await repo.create(admin_tg_id=admin_tg_id, text=text, total_count=len(users))
            await repo.mark_running(job)
            await AuditRepository(session).write(AuditAction.broadcast_created, actor_tg_id=admin_tg_id, details={"job_id": job.id, "total": len(users)})
            job_id = job.id

        sent = 0
        failed = 0
        for user in users:
            try:
                await bot.send_message(user.tg_id, text)
                sent += 1
                await asyncio.sleep(0.04)
            except Exception as exc:
                failed += 1
                logger.warning("broadcast_send_failed", tg_id=user.tg_id, error=type(exc).__name__)

        async with self.db.session() as session:
            repo = BroadcastRepository(session)
            job = await repo.get(job_id)
            if job:
                await repo.finish(job, sent_count=sent, failed_count=failed)
        return {"total": len(users), "sent": sent, "failed": failed}
