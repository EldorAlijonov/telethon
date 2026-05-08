import asyncio
from types import SimpleNamespace

import app.services.telethon_service as telethon_module
from app.services.telethon_service import TelethonService


class FakeTelegramClient:
    mode = "ok"
    created = []

    def __init__(self, session, api_id, api_hash):
        self.disconnected = False
        self.session = SimpleNamespace(save=lambda: "saved-session")
        FakeTelegramClient.created.append(self)

    async def connect(self):
        return None

    async def disconnect(self):
        self.disconnected = True

    async def send_code_request(self, phone):
        if FakeTelegramClient.mode == "fail":
            raise RuntimeError("network down")
        return SimpleNamespace(phone_code_hash="phone-code-hash")


def test_send_code_disconnects_client_when_request_fails(monkeypatch):
    monkeypatch.setattr(telethon_module, "TelegramClient", FakeTelegramClient)
    FakeTelegramClient.mode = "fail"
    FakeTelegramClient.created = []
    service = TelethonService(1, "hash")

    async def run():
        try:
            await service.send_code(10, "+998901234567")
        except ValueError as exc:
            assert "kod yuborishda" in str(exc)
        else:
            raise AssertionError("send_code should raise ValueError")

    asyncio.run(run())

    assert FakeTelegramClient.created[-1].disconnected
    assert 10 not in service.pending_clients


def test_send_code_keeps_client_pending_after_success(monkeypatch):
    monkeypatch.setattr(telethon_module, "TelegramClient", FakeTelegramClient)
    FakeTelegramClient.mode = "ok"
    FakeTelegramClient.created = []
    service = TelethonService(1, "hash")

    async def run():
        await service.send_code(10, "+998901234567")
        assert not FakeTelegramClient.created[-1].disconnected
        assert service.pending_clients[10]["phone_code_hash"] == "phone-code-hash"
        await service.cancel_all()

    asyncio.run(run())

    assert FakeTelegramClient.created[-1].disconnected
    assert service.pending_clients == {}
