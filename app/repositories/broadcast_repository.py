from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BroadcastJob, BroadcastStatus


class BroadcastRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, admin_tg_id: int, text: str, total_count: int) -> BroadcastJob:
        job = BroadcastJob(admin_tg_id=admin_tg_id, text=text, total_count=total_count)
        self.session.add(job)
        await self.session.flush()
        return job

    async def get(self, job_id: int) -> BroadcastJob | None:
        result = await self.session.execute(select(BroadcastJob).where(BroadcastJob.id == job_id))
        return result.scalar_one_or_none()

    async def mark_running(self, job: BroadcastJob) -> None:
        job.status = BroadcastStatus.running

    async def finish(self, job: BroadcastJob, sent_count: int, failed_count: int) -> None:
        job.sent_count = sent_count
        job.failed_count = failed_count
        job.status = BroadcastStatus.finished

    async def fail(self, job: BroadcastJob, sent_count: int, failed_count: int) -> None:
        job.sent_count = sent_count
        job.failed_count = failed_count
        job.status = BroadcastStatus.failed
