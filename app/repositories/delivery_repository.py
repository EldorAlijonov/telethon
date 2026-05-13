from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DeliveryStatus, SignalDelivery


class SignalDeliveryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pending(self, signal_id: int, recipient_tg_id: int) -> SignalDelivery:
        item = SignalDelivery(signal_id=signal_id, recipient_tg_id=recipient_tg_id, status=DeliveryStatus.pending)
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_by_signal_recipient(self, signal_id: int, recipient_tg_id: int) -> SignalDelivery | None:
        result = await self.session.execute(
            select(SignalDelivery).where(SignalDelivery.signal_id == signal_id, SignalDelivery.recipient_tg_id == recipient_tg_id)
        )
        return result.scalar_one_or_none()

    async def mark_delivered(self, delivery: SignalDelivery) -> None:
        delivery.status = DeliveryStatus.delivered
        delivery.delivered_at = datetime.now(UTC)
        delivery.attempts += 1

    async def mark_failed(self, delivery: SignalDelivery, error: str) -> None:
        delivery.status = DeliveryStatus.failed
        delivery.last_error = error[:1000]
        delivery.attempts += 1

    async def mark_dead_letter(self, delivery: SignalDelivery, error: str) -> None:
        delivery.status = DeliveryStatus.dead_letter
        delivery.last_error = error[:1000]
        delivery.attempts += 1
