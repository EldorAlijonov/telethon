from __future__ import annotations

from time import monotonic

from app.db.session import Database
from app.repositories.keyword_repository import KeywordRepository
from app.repositories.user_repository import UserRepository


class KeywordService:
    def __init__(self, db: Database, default_keywords: list[str] | None = None):
        self.db = db
        self.default_keywords = self._normalize_many(default_keywords or [])
        self._cache: dict[int, tuple[float, list[str]]] = {}
        self._cache_ttl_seconds = 15.0

    @staticmethod
    def normalize(value: str) -> str:
        return " ".join((value or "").strip().lower().split())

    @classmethod
    def _normalize_many(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = cls.normalize(value)
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    async def ensure_defaults(self, tg_id: int) -> None:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return
            repo = KeywordRepository(session)
            existing = set(await repo.list_active(user.id))
            for keyword in self.default_keywords:
                if keyword not in existing:
                    await repo.add(user.id, keyword)

    async def list_keywords(self, tg_id: int) -> list[str]:
        now = monotonic()
        cached = self._cache.get(tg_id)
        if cached and cached[0] > now:
            return list(cached[1])

        await self.ensure_defaults(tg_id)
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return []
            keywords = await KeywordRepository(session).list_active(user.id)
        self._cache[tg_id] = (now + self._cache_ttl_seconds, list(keywords))
        return keywords

    def invalidate_cache(self, tg_id: int) -> None:
        self._cache.pop(tg_id, None)

    async def add_keyword(self, tg_id: int, keyword: str) -> tuple[bool, str]:
        keyword = self.normalize(keyword)
        if len(keyword) < 2 or len(keyword) > 128:
            return False, "Kalit so'z 2-128 belgi oralig'ida bo'lishi kerak."
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return False, "Foydalanuvchi topilmadi."
            ok = await KeywordRepository(session).add(user.id, keyword)
            if ok:
                self.invalidate_cache(tg_id)
            return (ok, "Kalit so'z qo'shildi." if ok else "Bu kalit so'z allaqachon mavjud.")

    async def delete_keyword(self, tg_id: int, keyword: str) -> bool:
        keyword = self.normalize(keyword)
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            deleted = bool(user and await KeywordRepository(session).delete(user.id, keyword))
        if deleted:
            self.invalidate_cache(tg_id)
        return deleted

    async def rename_keyword(self, tg_id: int, old_keyword: str, new_keyword: str) -> tuple[bool, str]:
        old_keyword = self.normalize(old_keyword)
        new_keyword = self.normalize(new_keyword)
        if not old_keyword or len(new_keyword) < 2:
            return False, "Eski va yangi kalit so'z to'g'ri kiritilishi kerak."
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return False, "Foydalanuvchi topilmadi."
            ok = await KeywordRepository(session).rename(user.id, old_keyword, new_keyword)
            if ok:
                self.invalidate_cache(tg_id)
            return (ok, "Kalit so'z yangilandi." if ok else "Kalit so'z topilmadi yoki yangi qiymat mavjud.")
