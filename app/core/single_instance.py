from __future__ import annotations

import socket


class SingleInstanceLock:
    def __init__(self, port: int):
        self.port = port
        self.socket: socket.socket | None = None

    def acquire(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        try:
            sock.bind(("127.0.0.1", self.port))
            sock.listen(1)
        except OSError as exc:
            sock.close()
            raise RuntimeError(
                "Bot allaqachon ishga tushgan. Ikkinchi polling instance 2FA va update flowlarni buzadi. "
                "Avval eski processni to'xtating: Stop-Process -Id (Get-Content bot.pid)"
            ) from exc
        self.socket = sock

    def release(self) -> None:
        if self.socket:
            self.socket.close()
            self.socket = None
