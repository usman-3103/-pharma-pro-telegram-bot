import logging
import os
import threading
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Ваш Telegram ID — сюда бот отправляет новые запросы
ADMIN_CHAT_ID = 119207490

# Токен берётся из защищённой переменной BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")

# Этапы заполнения запроса
MEDICINE, DOSAGE, QUANTITY, LOCATION = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🔎 Найти препарат", "📦 Проверить наличие"],
        ["🇹🇷 Турецкий аналог", "🚚 Доставка"],
        ["👨‍💼 Связаться с менеджером"],
    ],
    resize_keyboard=True,
)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Служебная проверка работы бота для Render."""

    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )
        self.end_headers()
        self.wfile.write(
            "Pharma.Pro bot is running".encode("utf-8")
        )

    def log_message(self, format, *args):
        return


def run_health_server():
    """Открывает порт, необходимый для Render Web Service."""

    port = int(os.getenv("PORT", "10000"))

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        HealthCheckHandler,
    )

    logger.info(
        "Служебный сервер запущен на порту %s",
        port,
    )

    server.serve_forever()


def get_source_name(context: ContextTypes.DEFAULT_TYPE):
    """Определяет, откуда пользователь перешёл в бот."""

    if not context.args:
        return context.user_data.get(
            "source",
            "Telegram-бот",
        )

    source_code = context.args[0].strip()

    source_names = {
        "telegram": "Telegram",
        "telegram_channel": "Telegram-канал Pharma.Pro",
        "site": "Сайт Pharma.Pro",
        "website": "Сайт Pharma.Pro",
        "whatsapp": "WhatsApp",
        "max": "MAX",
        "advertising": "Реклама",
        "partner": "Рекомендация партнёра",
    }

    return source_names.get(
        source_code,
        source_code,
    )


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Главное приветствие."""

    user = update.effective_user

    context.user_data["source"] = get_source_name(
        context
    )

    await update.message.reply_text(
        f"Здравствуйте, {user.first_name}! 👋\n\n"
        "Добро пожаловать в Pharma.Pro.\n\n"
        "Здесь вы можете:\n"
        "🔎 найти информацию о препарате;\n"
        "📦 отправить запрос на проверку наличия;\n"
        "🇹🇷 уточнить турецкое название или аналог;\n"
        "🚚 узнать основную информацию о доставке.\n\n"
        "Напишите название лекарства или выберите "
        "действие ниже.\n\n"
        "Информация в боте не заменяет консультацию врача.",
        reply_markup=MAIN_KEYBOARD,
    )


async def begin_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """Начинает сбор запроса."""

    source = context.user_data.get(
        "source",
        "Telegram-бот",
    )

    context.user_data.clear()

    context.user_data["source"] = source
    context.user_data["request_type"] = (
        update.message.text.strip()
    )

    await update.message.reply_text(
        "Напишите полное название препарата:",
        reply_markup=ReplyKeyboardRemove(),
    )

    return MEDICINE


async def receive_medicine(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["medicine"] = (
        update.message.text.strip()
    )

    await update.message.reply_text(
        "Укажите дозировку препарата.\n\n"
        "Например: 10 мг, 20 мг или 100 мл.\n"
        "Если не знаете, напишите: «Не знаю».",
    )

    return DOSAGE


async def receive_dosage(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["dosage"] = (
        update.message.text.strip()
    )

    await update.message.reply_text(
        "Сколько упаковок вам требуется?\n\n"
        "Например: 1, 2 или 3 упаковки.",
    )

    return QUANTITY


async def receive_quantity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["quantity"] = (
        update.message.text.strip()
    )

    await update.message.reply_text(
        "Укажите страну и город.\n\n"
        "Например: Россия, Москва.",
    )

    return LOCATION


async def receive_location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["location"] = (
        update.message.text.strip()
    )

    user = update.effective_user

    full_name = escape(
        user.full_name or "Не указано"
    )

    if user.username:
        username = escape(
            f"@{user.username}"
        )
        profile_link = (
            f"https://t.me/{user.username}"
        )
    else:
        username = "не указан"
        profile_link = (
            f"tg://user?id={user.id}"
        )

    request_type = escape(
        context.user_data.get(
            "request_type",
            "Запрос на препарат",
        )
    )

    source = escape(
        context.user_data.get(
            "source",
            "Telegram-бот",
        )
    )

    medicine = escape(
        context.user_data.get(
            "medicine",
            "Не указано",
        )
    )

    dosage = escape(
        context.user_data.get(
            "dosage",
            "Не указано",
        )
    )

    quantity = escape(
        context.user_data.get(
            "quantity",
            "Не указано",
        )
    )

    location = escape(
        context.user_data.get(
            "location",
            "Не указано",
        )
    )

    request_text = (
        "📩 <b>НОВЫЙ ЗАПРОС PHARMA.PRO</b>\n\n"
        f"📋 <b>Тип запроса:</b> {request_type}\n"
        f"📍 <b>Источник:</b> {source}\n\n"
        f"👤 <b>Имя:</b> {full_name}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f'👁 <b>Профиль:</b> '
        f'<a href="{profile_link}">'
        "Открыть профиль</a>\n"
        f"🆔 <b>Telegram ID:</b> "
        f"<code>{user.id}</code>\n\n"
        f"💊 <b>Препарат:</b> {medicine}\n"
        f"💉 <b>Дозировка:</b> {dosage}\n"
        f"📦 <b>Количество:</b> {quantity}\n"
        f"🌍 <b>Страна и город:</b> {location}"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=request_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        await update.message.reply_text(
            "✅ Ваш запрос принят!\n\n"
            "Менеджер проверит информацию и свяжется "
            "с вами в Telegram.\n\n"
            "Пожалуйста, не отправляйте в бот диагнозы, "
            "рецепты и другие медицинские документы.",
            reply_markup=MAIN_KEYBOARD,
        )

    except Exception:
        logger.exception(
            "Не удалось отправить запрос администратору"
        )

        await update.message.reply_text(
            "⚠️ Не удалось отправить запрос.\n\n"
            "Пожалуйста, попробуйте ещё раз немного позже.",
            reply_markup=MAIN_KEYBOARD,
        )

    saved_source = context.user_data.get(
        "source",
        "Telegram-бот",
    )

    context.user_data.clear()
    context.user_data["source"] = saved_source

    return ConversationHandler.END


async def delivery_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🚚 Условия и возможность доставки зависят "
        "от препарата и страны получения.\n\n"
        "Для проверки нажмите «📦 Проверить наличие» "
        "и заполните запрос.",
        reply_markup=MAIN_KEYBOARD,
    )


async def contact_manager(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user

    full_name = escape(
        user.full_name or "Не указано"
    )

    if user.username:
        username = escape(
            f"@{user.username}"
        )
        profile_link = (
            f"https://t.me/{user.username}"
        )
    else:
        username = "не указан"
        profile_link = (
            f"tg://user?id={user.id}"
        )

    source = escape(
        context.user_data.get(
            "source",
            "Telegram-бот",
        )
    )

    manager_text = (
        "👨‍💼 <b>ПРОСЬБА СВЯЗАТЬСЯ</b>\n\n"
        f"👤 <b>Имя:</b> {full_name}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f'👁 <b>Профиль:</b> '
        f'<a href="{profile_link}">'
        "Открыть профиль</a>\n"
        f"🆔 <b>Telegram ID:</b> "
        f"<code>{user.id}</code>\n"
        f"📍 <b>Источник:</b> {source}"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=manager_text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        await update.message.reply_text(
            "✅ Запрос отправлен менеджеру.\n"
            "С вами свяжутся в Telegram.",
            reply_markup=MAIN_KEYBOARD,
        )

    except Exception:
        logger.exception(
            "Не удалось отправить запрос менеджеру"
        )

        await update.message.reply_text(
            "⚠️ Не удалось отправить запрос.\n"
            "Пожалуйста, попробуйте немного позже.",
            reply_markup=MAIN_KEYBOARD,
        )


async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    saved_source = context.user_data.get(
        "source",
        "Telegram-бот",
    )

    context.user_data.clear()
    context.user_data["source"] = saved_source

    await update.message.reply_text(
        "Заполнение запроса отменено.",
        reply_markup=MAIN_KEYBOARD,
    )

    return ConversationHandler.END


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "Выберите нужное действие с помощью кнопок.\n\n"
        "Для отмены заполнения запроса отправьте /cancel.",
        reply_markup=MAIN_KEYBOARD,
    )


async def unknown_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "Чтобы отправить запрос, нажмите кнопку "
        "«🔎 Найти препарат» или "
        "«📦 Проверить наличие».",
        reply_markup=MAIN_KEYBOARD,
    )


async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):
    logger.error(
        "Необработанная ошибка при работе бота",
        exc_info=(
            type(context.error),
            context.error,
            context.error.__traceback__,
        ),
    )


def main():
    if not TOKEN:
        raise ValueError(
            "Не найдена переменная BOT_TOKEN. "
            "Добавьте токен в защищённые переменные проекта."
        )

    health_thread = threading.Thread(
        target=run_health_server,
        daemon=True,
    )

    health_thread.start()

    app = Application.builder().token(TOKEN).build()

    request_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"^(🔎 Найти препарат|"
                    r"📦 Проверить наличие|"
                    r"🇹🇷 Турецкий аналог)$"
                ),
                begin_request,
            )
        ],
        states={
            MEDICINE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_medicine,
                )
            ],
            DOSAGE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_dosage,
                )
            ],
            QUANTITY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_quantity,
                )
            ],
            LOCATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    receive_location,
                )
            ],
        },
        fallbacks=[
            CommandHandler(
                "cancel",
                cancel,
            ),
            CommandHandler(
                "start",
                start,
            ),
        ],
    )

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "cancel",
            cancel,
        )
    )

    app.add_handler(
        request_conversation
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"^🚚 Доставка$"
            ),
            delivery_info,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(
                r"^👨‍💼 Связаться с менеджером$"
            ),
            contact_manager,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            unknown_message,
        )
    )

    app.add_error_handler(
        error_handler
    )

    logger.info(
        "Бот Pharma.Pro запущен!"
    )

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
