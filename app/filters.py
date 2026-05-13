from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message


class AdminFilter(BaseFilter):
    def __init__(self, admin_ids: set[int]):
        self.admin_ids = admin_ids

    async def __call__(self, message: Message) -> bool:
        return bool(message.from_user and message.from_user.id in self.admin_ids)
