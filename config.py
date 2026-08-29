import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "119207490"))
PORT = int(os.getenv("PORT", "10000"))
STATS_DB_PATH = os.getenv("STATS_DB_PATH", "data/pharma_stats.sqlite3")
STATS_TIMEZONE = os.getenv("STATS_TIMEZONE", "Europe/Istanbul")

if not BOT_TOKEN:
    raise RuntimeError(
        "Переменная BOT_TOKEN не найдена. "
        "Добавьте токен Telegram-бота в Variables на Railway."
    )
