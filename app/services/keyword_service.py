from __future__ import annotations

from app.database import Database
from app.utils import now_str


class KeywordService:
    def __init__(self, db: Database, default_keywords: list[str] | None = None):
        self.db = db
        self.default_keywords = self._normalize_many(default_keywords or [])

    @staticmethod
    def _normalize_many(values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            item = (value or '').strip().lower()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def _normalize_one(value: str) -> str:
        return (value or '').strip().lower()

    def ensure_default_keywords(self, tg_id: int) -> int:
        if not self.default_keywords:
            return 0

        inserted = 0
        with self.db.connect() as conn:
            c = conn.cursor()
            for keyword in self.default_keywords:
                c.execute(
                    'SELECT 1 FROM keyword_rules WHERE tg_id = ? AND keyword = ?',
                    (tg_id, keyword),
                )
                if c.fetchone():
                    continue
                c.execute(
                    """
                    INSERT INTO keyword_rules (tg_id, keyword, is_active, created_at)
                    VALUES (?, ?, 1, ?)
                    """,
                    (tg_id, keyword, now_str()),
                )
                inserted += 1
        return inserted

    def get_keywords(self, tg_id: int) -> list[str]:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute(
                """
                SELECT keyword
                FROM keyword_rules
                WHERE tg_id = ? AND is_active = 1
                ORDER BY keyword ASC
                """,
                (tg_id,),
            )
            rows = [row['keyword'] for row in c.fetchall()]

        if rows:
            return rows

        if self.default_keywords:
            self.ensure_default_keywords(tg_id)
            return self.get_keywords(tg_id)

        return []

    def add_keyword(self, tg_id: int, keyword: str) -> tuple[bool, str]:
        keyword = self._normalize_one(keyword)
        if not keyword:
            return False, 'Kalit so‘z bo‘sh bo‘lmasligi kerak.'

        with self.db.connect() as conn:
            c = conn.cursor()
            try:
                c.execute(
                    """
                    INSERT INTO keyword_rules (tg_id, keyword, is_active, created_at)
                    VALUES (?, ?, 1, ?)
                    """,
                    (tg_id, keyword, now_str()),
                )
                return True, 'Kalit so‘z qo‘shildi.'
            except Exception:
                return False, 'Bu kalit so‘z allaqachon mavjud.'

    def delete_keyword(self, tg_id: int, keyword: str) -> bool:
        keyword = self._normalize_one(keyword)
        if not keyword:
            return False
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute(
                'DELETE FROM keyword_rules WHERE tg_id = ? AND keyword = ?',
                (tg_id, keyword),
            )
            return c.rowcount > 0

    def edit_keyword(self, tg_id: int, old_keyword: str, new_keyword: str) -> tuple[bool, str]:
        old_keyword = self._normalize_one(old_keyword)
        new_keyword = self._normalize_one(new_keyword)

        if not old_keyword or not new_keyword:
            return False, 'Eski va yangi kalit so‘z kiritilishi kerak.'

        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT 1 FROM keyword_rules WHERE tg_id = ? AND keyword = ?',
                (tg_id, old_keyword),
            )
            if not c.fetchone():
                return False, 'Eski kalit so‘z topilmadi.'

            c.execute(
                'SELECT 1 FROM keyword_rules WHERE tg_id = ? AND keyword = ?',
                (tg_id, new_keyword),
            )
            if c.fetchone():
                return False, 'Yangi kalit so‘z allaqachon mavjud.'

            c.execute(
                'UPDATE keyword_rules SET keyword = ? WHERE tg_id = ? AND keyword = ?',
                (new_keyword, tg_id, old_keyword),
            )
            return True, 'Kalit so‘z yangilandi.'
