from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Config:
    bot_token: str
    admin_id: int
    db_path: str
    api_id: int
    api_hash: str
    blacklist_ids: set[int]
    default_keywords: list[str]
    log_level: str


def _parse_int_set(value: str | None) -> set[int]:
    if not value:
        return set()

    result = set()
    for item in value.split(","):
        item = item.strip()
        if item.lstrip("-").isdigit():
            result.add(int(item))
    return result


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} .env faylda topilmadi")
    return value


def _require_int_env(name: str) -> int:
    value = _require_env(name)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} butun son bo'lishi kerak") from exc


def _parse_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip().lower() for item in value.split("|") if item.strip()]


def load_config() -> Config:
    bot_token = _require_env("BOT_TOKEN")
    admin_id = _require_int_env("ADMIN_ID")
    api_id = _require_int_env("API_ID")
    api_hash = _require_env("API_HASH")

    db_path = os.getenv("DB_PATH", "bot.db").strip() or "bot.db"
    blacklist_ids = _parse_int_set(os.getenv("BLACKLIST_IDS"))
    default_keywords = _parse_keywords(os.getenv("DEFAULT_KEYWORDS"))
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"

    return Config(
        bot_token=bot_token,
        admin_id=admin_id,
        db_path=db_path,
        api_id=api_id,
        api_hash=api_hash,
        blacklist_ids=blacklist_ids,
        default_keywords=default_keywords,
        log_level=log_level,
    )
