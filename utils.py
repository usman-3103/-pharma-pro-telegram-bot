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


def user_details_html(update: Update, context: ContextTypes.DEFAULT_TYPE | None = None) -> str:
    user = update.effective_user
    full_name = escape(user.full_name or "Не указано")
    phone = None
    if context is not None:
        phone = context.user_data.get("contact_phone")

    if user.username:
        username = escape(f"@{user.username}")
        profile_line = (
            f'👁 <b>Профиль:</b> '
            f'<a href="https://t.me/{user.username}">Открыть профиль</a>'
        )
    else:
        username = "не указан"
        profile_line = "👁 <b>Профиль:</b> нет публичного username"

    lines = [
        f"👤 <b>Имя:</b> {full_name}",
        f"🔗 <b>Username:</b> {username}",
        profile_line,
        f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>",
    ]
    if phone:
        lines.append(f"📱 <b>Телефон:</b> {safe(phone)}")
    return "\n".join(lines)


def _numbered_lines(value: str) -> str:
    items = [line.strip() for line in str(value).splitlines() if line.strip()]
    return "\n".join(f"{i}. {item}" for i, item in enumerate(items, 1))


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
    ]:
        if data.get(key):
            lines.append(f"{label}: {data[key]}")
    if data.get("content_text"):
        content = data["content_text"]
        if data.get("request_type") == "Список препаратов":
            content = _numbered_lines(content)
        lines.append(f"📝 Информация:\n{content}")
    if data.get("attachment_label"):
        lines.append(f"📎 Вложения: {data['attachment_label']}")
    if data.get("location"):
        lines.append(f"🌍 Страна и город: {data['location']}")
    lines += ["", "Всё указано верно?"]
    return "\n".join(lines)


def admin_card_html(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    data = context.user_data
    request_id = data.get("request_id") or make_request_id(update.effective_user.id)
    lines = [
        "📩 <b>НОВЫЙ ЗАПРОС PHARMA.PRO</b>",
        f"🔢 <b>Номер:</b> <code>{safe(request_id)}</code>",
        "",
        f"📋 <b>Тип:</b> {safe(data.get('request_type'), 'Запрос')}",
        f"📍 <b>Источник:</b> {safe(data.get('source'), 'Telegram-бот')}",
        "",
        user_details_html(update, context),
        "",
    ]
    for key, label in [
        ("medicine", "💊 <b>Препарат:</b>"),
        ("dosage", "💉 <b>Дозировка:</b>"),
        ("quantity", "📦 <b>Количество:</b>"),
    ]:
        if data.get(key):
            lines.append(f"{label} {safe(data.get(key))}")
    if data.get("content_text"):
        content = data["content_text"]
        if data.get("request_type") == "Список препаратов":
            content = _numbered_lines(content)
        lines.append(f"📝 <b>Информация:</b>\n{safe(content)}")
    if data.get("attachment_label"):
        lines.append(f"📎 <b>Вложения:</b> {safe(data.get('attachment_label'))}")
    if data.get("location"):
        lines.append(f"🌍 <b>Страна и город:</b> {safe(data.get('location'))}")
    return "\n".join(lines)
