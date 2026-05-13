from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

import structlog


TOKEN_RE = re.compile(r"(\d{6,}:[A-Za-z0-9_-]{20,})")
HASH_RE = re.compile(r"(?i)(api_hash|secret|password|session|token)=([^&\s]+)")
TASHKENT_TZ = timezone(timedelta(hours=5), "Asia/Tashkent")


def mask_sensitive(_, __, event_dict):
    for key, value in list(event_dict.items()):
        if key.lower() in {"token", "password", "session", "api_hash", "secret"}:
            event_dict[key] = "***"
        elif isinstance(value, str):
            value = TOKEN_RE.sub("***", value)
            value = HASH_RE.sub(lambda m: f"{m.group(1)}=***", value)
            event_dict[key] = value
    return event_dict


def add_tashkent_timestamp(_, __, event_dict):
    event_dict["timestamp"] = datetime.now(TASHKENT_TZ).isoformat()
    return event_dict


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO), format="%(message)s")
    structlog.configure(
        processors=[
            mask_sensitive,
            structlog.contextvars.merge_contextvars,
            add_tashkent_timestamp,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper(), logging.INFO)),
        cache_logger_on_first_use=True,
    )
