from __future__ import annotations

import time
from collections import defaultdict


class LocalRedis:
    def __init__(self):
        self.values: dict[str, tuple[bytes, float | None]] = {}
        self.streams: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
        self.counter = 0

    async def ping(self) -> bool:
        return True

    async def get(self, key: str):
        item = self.values.get(key)
        if not item:
            return None
        value, expires_at = item
        if expires_at and expires_at <= time.time():
            self.values.pop(key, None)
            return None
        return value

    async def set(self, key: str, value, ex: int | None = None, nx: bool = False):
        if nx and await self.get(key) is not None:
            return None
        raw = value if isinstance(value, bytes) else str(value).encode("utf-8")
        self.values[key] = (raw, time.time() + ex if ex else None)
        return True

    async def delete(self, key: str) -> int:
        existed = key in self.values
        self.values.pop(key, None)
        return int(existed)

    async def incr(self, key: str) -> int:
        current = await self.get(key)
        value = int(current.decode("utf-8")) if current else 0
        value += 1
        await self.set(key, str(value))
        return value

    async def expire(self, key: str, seconds: int) -> bool:
        item = self.values.get(key)
        if not item:
            return False
        value, _ = item
        self.values[key] = (value, time.time() + seconds)
        return True

    async def xadd(self, name: str, fields: dict, maxlen: int | None = None, approximate: bool = True) -> str:
        self.counter += 1
        message_id = f"{int(time.time() * 1000)}-{self.counter}"
        self.streams[name].append((message_id, {k: str(v) for k, v in fields.items()}))
        if maxlen and len(self.streams[name]) > maxlen:
            self.streams[name] = self.streams[name][-maxlen:]
        return message_id

    async def xgroup_create(self, *args, **kwargs):
        return True

    async def xreadgroup(self, *args, **kwargs):
        return []

    async def xack(self, *args, **kwargs):
        return 1

    async def aclose(self, *args, **kwargs) -> None:
        self.values.clear()
