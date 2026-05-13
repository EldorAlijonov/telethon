from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_int_set(value: str | set[int] | None) -> set[int]:
    if value is None or value == "":
        return set()
    if isinstance(value, set):
        return value
    result: set[int] = set()
    for item in str(value).split(","):
        item = item.strip()
        if item.lstrip("-").isdigit():
            result.add(int(item))
    return result


def _parse_int_list(value: str | list[int] | None) -> list[int]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [int(item.strip()) for item in str(value).split(",") if item.strip().isdigit()]


def _parse_str_list(value: str | list[str] | None, separator: str = "|") -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [item.strip() for item in str(value).split(separator) if item.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_ids_raw: str = Field(default="", alias="ADMIN_IDS")
    legacy_admin_id: int | None = Field(default=None, alias="ADMIN_ID")
    api_id: int = Field(alias="API_ID")
    api_hash: str = Field(alias="API_HASH")

    database_url: str = Field(default="postgresql+asyncpg://bot:bot_password@localhost:5432/telegram_monitor", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    secret_key: str = Field(default="change-this-32-byte-minimum-secret-key", alias="SECRET_KEY")
    session_encryption_key: str | None = Field(default=None, alias="SESSION_ENCRYPTION_KEY")

    default_access_days: int = Field(default=30, alias="DEFAULT_ACCESS_DAYS")
    default_keywords_raw: str = Field(default="", alias="DEFAULT_KEYWORDS")
    blacklist_ids_raw: str = Field(default="", alias="BLACKLIST_IDS")
    mandatory_channels_raw: str = Field(default="", alias="MANDATORY_CHANNELS")

    signal_dedupe_ttl_seconds: int = Field(default=1800, alias="SIGNAL_DEDUPE_TTL_SECONDS")
    otp_ttl_seconds: int = Field(default=300, alias="OTP_TTL_SECONDS")
    otp_max_attempts: int = Field(default=5, alias="OTP_MAX_ATTEMPTS")
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    metrics_port: int = Field(default=9108, alias="METRICS_PORT")
    signal_stream: str = Field(default="signals:v1", alias="SIGNAL_STREAM")
    signal_retry_stream: str = Field(default="signals:retry:v1", alias="SIGNAL_RETRY_STREAM")
    signal_dlq_stream: str = Field(default="signals:dlq:v1", alias="SIGNAL_DLQ_STREAM")
    app_lock_port: int = Field(default=29731, alias="APP_LOCK_PORT")

    @property
    def effective_admin_ids(self) -> set[int]:
        ids = set(_parse_int_list(self.admin_ids_raw))
        if self.legacy_admin_id:
            ids.add(self.legacy_admin_id)
        return ids

    @property
    def default_keywords(self) -> list[str]:
        return [item.lower() for item in _parse_str_list(self.default_keywords_raw)]

    @property
    def blacklist_ids(self) -> set[int]:
        return _parse_int_set(self.blacklist_ids_raw)

    @property
    def mandatory_channels(self) -> list[str]:
        return _parse_str_list(self.mandatory_channels_raw, separator=",")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if len(settings.secret_key) < 32:
        raise ValueError("SECRET_KEY kamida 32 ta belgidan iborat bo'lishi kerak")
    if not settings.effective_admin_ids:
        raise ValueError("ADMIN_IDS yoki ADMIN_ID sozlanishi shart")
    return settings
