# Telegram Monitoring Bot

Bu bot foydalanuvchilarni admin tasdig'idan o'tkazadi, Telegram akkaunt ulashga yordam beradi va kalit so'zlar bo'yicha chatlarni kuzatadi.

## Imkoniyatlar

- Telefon raqam orqali foydalanuvchi ro'yxatdan o'tkazish
- Admin panel orqali tasdiqlash, o'chirish va statistika ko'rish
- Tasdiqlangan foydalanuvchi uchun 30 kunlik foydalanish muddati
- Telegram ulanishini yoqish va uzish
- Kalit so'z qo'shish, tahrirlash va o'chirish
- Chatlarda kalit so'z topilganda foydalanuvchiga signal yuborish

## O'rnatish

1. Python 3.11 yoki undan yangiroq versiyani o'rnating.
2. Kerakli kutubxonalarni o'rnating:

```bash
pip install -r requirements.txt
```

3. `.env.example` faylidan `.env` yarating va qiymatlarni to'ldiring.

```env
BOT_TOKEN=123456:telegram_bot_token
ADMIN_ID=123456789
API_ID=123456
API_HASH=telegram_api_hash
DB_PATH=bot.db
BLACKLIST_IDS=
DEFAULT_KEYWORDS=ish|vakansiya|xizmat
LOG_LEVEL=INFO
```

## Ishga tushirish

```bash
python main.py
```

## Tekshirish

Avtomatik testlarni ishga tushirish:

```bash
python -m pytest -q
```

Real Telegram sozlamalarini pollingni boshlamasdan tekshirish:

```bash
python scripts/integration_smoke.py
```

Bu tekshiruv `.env` qiymatlarini, `bot.db` sxemasini, handlerlar ro'yxatdan o'tishini, Bot API tokenini va Telethon serveriga ulanishni tekshiradi. U foydalanuvchiga xabar yubormaydi va Telegram login kodi so'ramaydi.

## Sozlamalar

- `BOT_TOKEN` - BotFather bergan bot token.
- `ADMIN_ID` - adminning Telegram ID raqami.
- `API_ID` va `API_HASH` - my.telegram.org orqali olinadigan Telethon ma'lumotlari.
- `BLACKLIST_IDS` - kuzatishdan chiqariladigan chat yoki user ID lar, vergul bilan yoziladi.
- `DEFAULT_KEYWORDS` - yangi foydalanuvchiga avtomatik qo'shiladigan kalit so'zlar, `|` bilan ajratiladi.
- `LOG_LEVEL` - log darajasi: `INFO`, `DEBUG`, `WARNING`, `ERROR`.
