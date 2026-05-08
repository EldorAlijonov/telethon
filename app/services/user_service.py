from __future__ import annotations

from app.database import Database
from app.utils import add_30_days_str, now_dt, now_str, parse_dt


class UserService:
    def __init__(self, db: Database):
        self.db = db

    def create_or_update_user(self, tg_id: int, full_name: str, username: str | None, phone: str | None = None) -> None:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,))
            row = c.fetchone()
            if row:
                current = dict(row)
                c.execute(
                    'UPDATE users SET full_name = ?, username = ?, phone = ?, updated_at = ? WHERE tg_id = ?',
                    (full_name, username, phone if phone is not None else current.get('phone'), now_str(), tg_id),
                )
                return
            c.execute(
                '''
                INSERT INTO users (
                    tg_id, full_name, username, phone, status,
                    approved_at, expires_at, telethon_phone,
                    telethon_session, telethon_connected_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'pending', NULL, NULL, NULL, NULL, NULL, ?, ?)
                ''',
                (tg_id, full_name, username, phone, now_str(), now_str()),
            )

    def save_phone(self, tg_id: int, phone: str, full_name: str, username: str | None) -> None:
        self.create_or_update_user(tg_id, full_name, username, phone)

    def get_user_by_tg_id(self, tg_id: int) -> dict | None:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,))
            row = c.fetchone()
            return dict(row) if row else None

    def get_pending_users(self) -> list[dict]:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE status = 'pending' ORDER BY id DESC")
            return [dict(r) for r in c.fetchall()]

    def get_approved_users(self) -> list[dict]:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE status = 'approved' ORDER BY id DESC")
            return [dict(r) for r in c.fetchall()]

    def get_all_users(self) -> list[dict]:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users ORDER BY id DESC')
            return [dict(r) for r in c.fetchall()]

    def approve_user(self, tg_id: int) -> bool:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM users WHERE tg_id = ?', (tg_id,))
            if not c.fetchone():
                return False
            c.execute(
                'UPDATE users SET status = ?, approved_at = ?, expires_at = ?, updated_at = ? WHERE tg_id = ?',
                ('approved', now_str(), add_30_days_str(), now_str(), tg_id),
            )
            return True

    def delete_user(self, tg_id: int) -> bool:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM users WHERE tg_id = ?', (tg_id,))
            if not c.fetchone():
                return False
            c.execute('DELETE FROM users WHERE tg_id = ?', (tg_id,))
            c.execute('DELETE FROM keyword_rules WHERE tg_id = ?', (tg_id,))
            c.execute('DELETE FROM monitor_settings WHERE tg_id = ?', (tg_id,))
            return True

    def is_user_allowed(self, tg_id: int) -> bool:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE tg_id = ?', (tg_id,))
            row = c.fetchone()
            if not row:
                return False
            user = dict(row)
            if user.get('status') != 'approved':
                return False
            exp = parse_dt(user.get('expires_at'))
            if not exp:
                return False
            if exp < now_dt():
                c.execute(
                    "UPDATE users SET status = 'expired', telethon_phone = NULL, telethon_session = NULL, telethon_connected_at = NULL, updated_at = ? WHERE tg_id = ?",
                    (now_str(), tg_id),
                )
                c.execute('UPDATE monitor_settings SET is_enabled = 0, updated_at = ? WHERE tg_id = ?', (now_str(), tg_id))
                return False
            return True

    def save_telethon_session(self, tg_id: int, phone: str, session: str) -> None:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE users SET telethon_phone = ?, telethon_session = ?, telethon_connected_at = ?, updated_at = ? WHERE tg_id = ?',
                (phone, session, now_str(), now_str(), tg_id),
            )

    def clear_telethon_session(self, tg_id: int) -> None:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute(
                'UPDATE users SET telethon_phone = NULL, telethon_session = NULL, telethon_connected_at = NULL, updated_at = ? WHERE tg_id = ?',
                (now_str(), tg_id),
            )
            c.execute('UPDATE monitor_settings SET is_enabled = 0, updated_at = ? WHERE tg_id = ?', (now_str(), tg_id))

    def has_telethon_session(self, tg_id: int) -> bool:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute('SELECT telethon_session FROM users WHERE tg_id = ?', (tg_id,))
            row = c.fetchone()
            return bool(row and row['telethon_session'])

    def get_user_stats(self) -> dict:
        with self.db.connect() as conn:
            c = conn.cursor()
            c.execute(
                "UPDATE users SET status = 'expired', telethon_phone = NULL, telethon_session = NULL, telethon_connected_at = NULL, updated_at = ? WHERE status = 'approved' AND expires_at IS NOT NULL AND expires_at < datetime('now')",
                (now_str(),),
            )
            c.execute('UPDATE monitor_settings SET is_enabled = 0, updated_at = ? WHERE tg_id IN (SELECT tg_id FROM users WHERE status = \'expired\')', (now_str(),))
            c.execute('SELECT COUNT(*) FROM users')
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
            pending = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM users WHERE status = 'approved' AND expires_at >= datetime('now')")
            active = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM users WHERE status = 'expired'")
            expired = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM users WHERE status = 'approved' AND expires_at >= datetime('now') AND telethon_session IS NOT NULL AND telethon_session != ''")
            telethon_connected = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM monitor_settings WHERE is_enabled = 1")
            monitoring_enabled = c.fetchone()[0]
            return {
                'total': total,
                'pending': pending,
                'active': active,
                'expired': expired,
                'telethon_connected': telethon_connected,
                'monitoring_enabled': monitoring_enabled,
            }
