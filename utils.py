from datetime import datetime, timezone
from html import escape

from telegram import Update
from telegram.ext import ContextTypes

SOURCE_NAMES = {
    "telegram": "Telegram",
    "telegram_channel": "Telegram-канал Pharma.Pro",
    "site": "Сайт Pharma.Pro",
    "website": "Сайт Pharma.Pro",
    "whatsapp": "WhatsApp",
    "max": "MAX",
    "advertising": "Реклама",
    "partner": "Рекомендация",
    "qr": "QR-код",
}


def get_source_name(context: ContextTypes.DEFAULT_TYPE) -> str:
    if not context.args:
        return context.user_data.get("source", "Telegram-бот")
    code = context.args[0].strip().lower()
    return SOURCE_NAMES.get(code, code)


def clear_request_keep_source(context: ContextTypes.DEFAULT_TYPE) -> None:
    source = context.user_data.get("source", "Telegram-бот")
    context.user_data.clear()
    context.user_data["source"] = source


def safe(value, default="Не указано") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return escape(text) if text else default


def make_request_id(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return f"{now:%y%m%d%H%M%S}-{str(user_id)[-4:]}"


def user_details_html(update: Update) -> str:
    user = update.effective_user
    full_name = escape(user.full_name or "Не указано")
    if user.username:
        username = escape(f"@{user.username}")
        profile_url = f"https://t.me/{user.username}"
    else:
        username = "не указан"
        profile_url = f"tg://user?id={user.id}"
    return (
        f"👤 <b>Имя:</b> {full_name}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f'👁 <b>Профиль:</b> <a href="{profile_url}">Открыть профиль</a>\n'
        f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>"
    )


def confirmation_text(context: ContextTypes.DEFAULT_TYPE) -> str:
    data = context.user_data
    lines = [
        "Проверьте информацию перед отправкой:",
        "",
        f"📋 Тип запроса: {data.get('request_type', 'Запрос')}",
    ]
    for key, label in [
        ("medicine", "💊 Препарат"),
        ("dosage", "💉 Дозировка"),
        ("quantity", "📦 Количество"),
        ("content_text", "📝 Информация"),
        ("attachment_label", "📎 Вложение"),
        ("location", "🌍 Страна и город"),
    ]:
        if data.get(key):
            lines.append(f"{label}: {data[key]}")
    lines += ["", "Всё указано верно?"]
    return "\n".join(lines)


def admin_card_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    data = context.user_data
    request_id = data.get("request_id") or make_request_id(update.effective_user.id)
    lines = [
        "📩 <b>Pharma.Pro • Новый запрос</b>",
        f"🔢 <b>Номер:</b> <code>{safe(request_id)}</code>",
        "",
        f"📋 <b>Тип:</b> {safe(data.get('request_type'), 'Запрос')}",
        f"📍 <b>Источник:</b> {safe(data.get('source'), 'Telegram-бот')}",
        "",
        user_details_html(update),
        "",
    ]
    for key, label in [
        ("medicine", "💊 <b>Препарат:</b>"),
        ("dosage", "💉 <b>Дозировка:</b>"),
        ("quantity", "📦 <b>Количество:</b>"),
        ("content_text", "📝 <b>Информация:</b>"),
        ("attachment_label", "📎 <b>Вложение:</b>"),
        ("location", "🌍 <b>Страна и город:</b>"),
    ]:
        if data.get(key):
            lines.append(f"{label} {safe(data.get(key))}")
    return "\n".join(lines)
