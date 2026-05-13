from __future__ import annotations

from aiogram import Bot


class SubscriptionGuardService:
    def __init__(self, mandatory_channels: list[str], admin_ids: set[int]):
        self.mandatory_channels = mandatory_channels
        self.admin_ids = admin_ids

    async def missing_channels(self, bot: Bot, tg_id: int) -> list[str]:
        if tg_id in self.admin_ids or not self.mandatory_channels:
            return []
        missing: list[str] = []
        for channel in self.mandatory_channels:
            try:
                member = await bot.get_chat_member(channel, tg_id)
                if member.status in {"left", "kicked"}:
                    missing.append(channel)
            except Exception:
                missing.append(channel)
        return missing

    async def ensure_allowed(self, bot: Bot, tg_id: int) -> tuple[bool, str]:
        missing = await self.missing_channels(bot, tg_id)
        if not missing:
            return True, ""
        rows = "\n".join(f"- {channel}" for channel in missing)
        return False, "Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:\n\n" + rows
