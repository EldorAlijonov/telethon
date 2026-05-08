from __future__ import annotations

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
    PhoneNumberUnoccupiedError,
    SessionPasswordNeededError,
)
from telethon.sessions import StringSession


class TelethonService:
    def __init__(self, api_id: int, api_hash: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.pending_clients: dict[int, dict] = {}

    async def send_code(self, tg_id: int, phone: str) -> None:
        await self.cancel(tg_id)
        client = TelegramClient(StringSession(), self.api_id, self.api_hash)
        await client.connect()
        code_sent = False
        try:
            result = await client.send_code_request(phone)
            code_sent = True
        except (PhoneNumberInvalidError, PhoneNumberBannedError, PhoneNumberUnoccupiedError, ApiIdInvalidError) as exc:
            raise ValueError("Telefon raqami yoki API ma'lumotlari noto'g'ri") from exc
        except (FloodWaitError, PhoneNumberFloodError) as exc:
            raise ValueError("Juda ko'p urinish bo'ldi. Biroz kutib qayta urinib ko'ring") from exc
        except Exception as exc:
            raise ValueError("Telegramga kod yuborishda xatolik yuz berdi. Qayta urinib ko'ring") from exc
        finally:
            if not code_sent:
                await client.disconnect()

        self.pending_clients[tg_id] = {
            'client': client,
            'phone': phone,
            'phone_code_hash': result.phone_code_hash,
        }

    async def sign_in(self, tg_id: int, code: str) -> str:
        data = self.pending_clients.get(tg_id)
        if not data:
            raise ValueError('Avval telefon raqamini yuboring')
        client: TelegramClient = data['client']
        try:
            await client.sign_in(phone=data['phone'], code=code, phone_code_hash=data['phone_code_hash'])
            session = str(client.session.save())
            await self.cancel(tg_id)
            return session
        except PhoneCodeInvalidError:
            raise ValueError("Kod noto'g'ri")
        except PhoneCodeExpiredError:
            raise ValueError("Kodning muddati tugagan. Qaytadan urinib ko'ring")
        except SessionPasswordNeededError:
            raise ValueError('2FA_PASSWORD_NEEDED')

    async def sign_in_with_password(self, tg_id: int, password: str) -> str:
        data = self.pending_clients.get(tg_id)
        if not data:
            raise ValueError('Avval telefon raqamini yuboring va kod oling')
        client: TelegramClient = data['client']
        try:
            await client.sign_in(password=password)
            return str(client.session.save())
        except PasswordHashInvalidError:
            raise ValueError("Ikki bosqichli parol noto'g'ri")
        except Exception:
            raise ValueError('Parol bilan kirishda xatolik yuz berdi')
        finally:
            await self.cancel(tg_id)

    async def cancel(self, tg_id: int) -> None:
        data = self.pending_clients.pop(tg_id, None)
        if data and data.get('client'):
            try:
                await data['client'].disconnect()
            except Exception:
                pass

    async def cancel_all(self) -> None:
        for tg_id in list(self.pending_clients):
            await self.cancel(tg_id)
