from __future__ import annotations

from app.database import Database
from app.utils import now_str


class MonitorService:
    def __init__(self, db: Database):
        self.db = db

    def is_enabled(self, tg_id: int) -> bool:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT is_enabled FROM monitor_settings WHERE tg_id = ?', (tg_id,))
            row = c.fetchone()
            return bool(row and row['is_enabled'])

    def set_enabled(self, tg_id: int, enabled: bool) -> None:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM monitor_settings WHERE tg_id = ?', (tg_id,))
            if c.fetchone():
                c.execute('UPDATE monitor_settings SET is_enabled = ?, updated_at = ? WHERE tg_id = ?', (1 if enabled else 0, now_str(), tg_id))
            else:
                c.execute('INSERT INTO monitor_settings (tg_id, is_enabled, created_at, updated_at) VALUES (?, ?, ?, ?)', (tg_id, 1 if enabled else 0, now_str(), now_str()))
