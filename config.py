import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "119207490"))
PORT = int(os.getenv("PORT", "10000"))

if not BOT_TOKEN:
    raise RuntimeError(
        "Переменная BOT_TOKEN не найдена. "
        "Добавьте токен Telegram-бота в Environment на Render."
    )
