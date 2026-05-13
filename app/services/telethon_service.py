from __future__ import annotations

import asyncio
from dataclasses import dataclass

from redis.asyncio import Redis
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    FloodWaitError,
    PasswordHashInvalidError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    PhoneNumberBannedError,
    PhoneNumberFloodError,
    PhoneNumberInvalidError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession

from app.core.security import SessionCipher
from app.db.models import AuditAction
from app.db.session import Database
from app.repositories.audit_repository import AuditRepository
from app.repositories.session_repository import TelegramSessionRepository
from app.repositories.user_repository import UserRepository


@dataclass
class PendingLogin:
    client: TelegramClient
    phone: str
    phone_code_hash: str


class TelethonAuthService:
    def __init__(self, api_id: int, api_hash: str, db: Database, cipher: SessionCipher, redis: Redis, otp_ttl: int, max_attempts: int):
        self.api_id = api_id
        self.api_hash = api_hash
        self.db = db
        self.cipher = cipher
        self.redis = redis
        self.otp_ttl = otp_ttl
        self.max_attempts = max_attempts
        self.pending: dict[int, PendingLogin] = {}

    async def send_code(self, tg_id: int, phone: str) -> None:
        await self.cancel(tg_id)
        attempts_key = f"otp:attempts:{tg_id}"
        attempts = await self.redis.incr(attempts_key)
        if attempts == 1:
            await self.redis.expire(attempts_key, self.otp_ttl)
        if attempts > self.max_attempts:
            raise ValueError("Juda ko'p urinish. Biroz kutib qayta urinib ko'ring.")

        client = TelegramClient(StringSession(), self.api_id, self.api_hash)
        await client.connect()
        try:
            sent = await client.send_code_request(phone)
        except (PhoneNumberInvalidError, PhoneNumberBannedError, PhoneNumberUnoccupiedError, ApiIdInvalidError) as exc:
            await client.disconnect()
            raise ValueError("Telefon raqami yoki Telegram API sozlamalari noto'g'ri.") from exc
        except (FloodWaitError, PhoneNumberFloodError) as exc:
            await client.disconnect()
            wait = getattr(exc, "seconds", None)
            suffix = f" {wait} soniyadan keyin urinib ko'ring." if wait else ""
            raise ValueError("Telegram flood limitga tushdi." + suffix) from exc
        except Exception as exc:
            await client.disconnect()
            raise ValueError("Telegramga kod yuborishda xatolik yuz berdi.") from exc

        self.pending[tg_id] = PendingLogin(client=client, phone=phone, phone_code_hash=sent.phone_code_hash)

    async def sign_in_code(self, tg_id: int, code: str) -> str:
        login = self.pending.get(tg_id)
        if not login:
            raise ValueError("Avval telefon raqamini yuboring.")
        try:
            await login.client.sign_in(phone=login.phone, code=code, phone_code_hash=login.phone_code_hash)
            session = str(login.client.session.save())
            await self.cancel(tg_id)
            return session
        except PhoneCodeInvalidError as exc:
            raise ValueError("Kod noto'g'ri.") from exc
        except PhoneCodeExpiredError as exc:
            await self.cancel(tg_id)
            raise ValueError("Kod muddati tugagan. Qaytadan boshlang.") from exc
        except SessionPasswordNeededError as exc:
            raise ValueError("2FA_PASSWORD_NEEDED") from exc

    async def sign_in_password(self, tg_id: int, password: str) -> str:
        login = self.pending.get(tg_id)
        if not login:
            raise ValueError("Avval telefon raqamini yuboring.")
        try:
            await login.client.sign_in(password=password)
            return str(login.client.session.save())
        except PasswordHashInvalidError as exc:
            raise ValueError("Ikki bosqichli parol noto'g'ri.") from exc
        except Exception as exc:
            raise ValueError("2FA parolni tekshirishda xatolik yuz berdi. Qayta urinib ko'ring.") from exc
        finally:
            await self.cancel(tg_id)

    async def save_session(self, tg_id: int, phone: str, plain_session: str) -> None:
        encrypted = self.cipher.encrypt(plain_session)
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                raise ValueError("Foydalanuvchi topilmadi.")
            await TelegramSessionRepository(session).save(user.id, phone, encrypted)
            await AuditRepository(session).write(AuditAction.session_connected, target_tg_id=tg_id)

    async def get_plain_session(self, tg_id: int) -> tuple[str, str] | None:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if not user:
                return None
            item = await TelegramSessionRepository(session).get_by_user_id(user.id)
            if not item:
                return None
            return item.phone, self.cipher.decrypt(item.encrypted_session)

    async def revoke_session(self, tg_id: int) -> None:
        async with self.db.session() as session:
            user = await UserRepository(session).get_by_tg_id(tg_id)
            if user:
                await TelegramSessionRepository(session).revoke(user.id)
                await AuditRepository(session).write(AuditAction.session_revoked, target_tg_id=tg_id)

    async def cancel(self, tg_id: int) -> None:
        login = self.pending.pop(tg_id, None)
        if login:
            try:
                await login.client.disconnect()
            except Exception:
                pass

    async def cancel_all(self) -> None:
        await asyncio.gather(*(self.cancel(tg_id) for tg_id in list(self.pending)), return_exceptions=True)


TelethonService = TelethonAuthService
