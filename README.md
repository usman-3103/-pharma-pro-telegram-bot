# Pharma Pro Telegram Bot

Основной Telegram-бот Pharma Pro.

Возможности:

- один препарат;
- список препаратов одним сообщением;
- подбор турецкого аналога;
- текст, фотографии и документы;
- подтверждение перед отправкой;
- номер и источник запроса;
- имя, username и безопасный способ связи;
- связь с оператором;
- учёт источников и администраторская статистика `/stats`;
- Health Check для Railway.

Railway:

- Build Command: `pip install -r requirements.txt`
- Start Command: `python main.py`
- Variables: `BOT_TOKEN`, `ADMIN_CHAT_ID`
- Для постоянной статистики подключите Railway Volume и задайте `STATS_DB_PATH=/data/pharma_stats.sqlite3` (если Volume смонтирован в `/data`).
- Часовой пояс статистики по умолчанию: `Europe/Istanbul`; при необходимости задаётся через `STATS_TIMEZONE`.
