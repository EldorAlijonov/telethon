import asyncio
import sys

from app.main import main

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError as exc:
        message = str(exc)
        if "Bot allaqachon ishga tushgan" in message:
            print(message)
            print()
            print("Qayta ishga tushirish:")
            print("powershell -ExecutionPolicy Bypass -File scripts\\restart_bot.ps1")
            print()
            print("To'xtatish:")
            print("Stop-Process -Id (Get-Content bot.pid)")
            sys.exit(2)
        raise
