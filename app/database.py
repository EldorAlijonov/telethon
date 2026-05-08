from __future__ import annotations

import sqlite3
from contextlib import contextmanager


class Database:
    def __init__(self, db_path: str = 'bot.db'):
        self.db_path = db_path
        self.init_db()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connect() as conn:
            c = conn.cursor()
            c.execute(
                '''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER UNIQUE NOT NULL,
                    full_name TEXT,
                    username TEXT,
                    phone TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    approved_at TEXT,
                    expires_at TEXT,
                    telethon_phone TEXT,
                    telethon_session TEXT,
                    telethon_connected_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            c.execute(
                '''
                CREATE TABLE IF NOT EXISTS keyword_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tg_id INTEGER NOT NULL,
                    keyword TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    UNIQUE(tg_id, keyword)
                )
                '''
            )
            c.execute(
                '''
                CREATE TABLE IF NOT EXISTS monitor_settings (
                    tg_id INTEGER PRIMARY KEY,
                    is_enabled INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                '''
            )
            c.execute('CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_users_expires_at ON users(expires_at)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_keyword_rules_tg_id ON keyword_rules(tg_id)')
