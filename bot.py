import logging
import os

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Ваш Telegram ID — сюда бот отправляет новые заявки
ADMIN_CHAT_ID = 119207490

# Токен берётся из защищённой переменной BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")

# Этапы заполнения заявки
MEDICINE, DOSAGE, QUANTITY, LOCATION = range(4)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🔎 Найти препарат", "📦 Проверить наличие"],
        ["🇹🇷 Турецкий аналог", "🚚 Доставка"],
        ["👨‍💼 Связаться с менеджером"],
    ],
    resize_keyboard=True,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное приветствие."""
    user = update.effective_user

    await update.message.reply_text(
        f"Здравствуйте, {user.first_name}! 👋\n\n"
        "Добро пожаловать в Pharma.Pro.\n\n"
        "Здесь вы можете:\n"
        "🔎 найти информацию о препарате;\n"
        "📦 отправить запрос на проверку наличия;\n"
        "🇹🇷 уточнить турецкое название или аналог;\n"
        "🚚 узнать основную информацию о доставке.\n\n"
        "Напишите название лекарства или выберите действие ниже.\n\n"
        "Информация в боте не заменяет консультацию врача.",
        reply_markup=MAIN_KEYBOARD,
    )


async def begin_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает сбор заявки."""
    context.user_data.clear()

    await update.message.reply_text(
        "Напишите полное название препарата:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return MEDICINE


async def receive_medicine(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["medicine"] = update.message.text.strip()

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
    context.user_data["dosage"] = update.message.text.strip()

    await update.message.reply_text(
        "Сколько упаковок вам требуется?\n\n"
        "Например: 1, 2 или 3 упаковки.",
    )
    return QUANTITY


async def receive_quantity(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["quantity"] = update.message.text.strip()

    await update.message.reply_text(
        "Укажите страну и город.\n\n"
        "Например: Россия, Москва.",
    )
    return LOCATION


async def receive_location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data["location"] = update.message.text.strip()

    user = update.effective_user

username = f"@{user.username}" if user.username else "не указан"

if user.username:
    profile_link = f"https://t.me/{user.username}"
else:
    profile_link = f"tg://user?id={user.id}"

source = context.user_data.get("source", "Telegram-бот")

application_text = (
    "📩 НОВЫЙ ЗАПРОС PHARMA.PRO\n\n"
    f"👤 Имя: {user.full_name}\n"
    f"🔗 Telegram: {username}\n"
    f"👁 Профиль: {profile_link}\n"
    f"🆔 Telegram ID: {user.id}\n"
    f"📍 Источник: {source}\n\n"
    f"💊 Препарат: {context.user_data['medicine']}\n"
    f"💉 Дозировка: {context.user_data['dosage']}\n"
    f"📦 Количество: {context.user_data['quantity']}\n"
    f"🌍 Страна и город: {context.user_data['location']}"
)

    # Отправляем заявку владельцу бота
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=application_text,
    )

    await update.message.reply_text(
        "✅ Ваш запрос принят!\n\n"
        "Менеджер проверит информацию и свяжется с вами "
        "в Telegram.\n\n"
        "Пожалуйста, не отправляйте в бот диагнозы, рецепты "
        "и другие медицинские документы.",
        reply_markup=MAIN_KEYBOARD,
    )

    context.user_data.clear()
    return ConversationHandler.END


async def delivery_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "🚚 Условия и возможность доставки зависят от препарата "
        "и страны получения.\n\n"
        "Для проверки нажмите «📦 Проверить наличие» и заполните запрос.",
        reply_markup=MAIN_KEYBOARD,
    )


async def contact_manager(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    user = update.effective_user
    username = f"@{user.username}" if user.username else "не указан"

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=(
            "👨‍💼 КЛИЕНТ ПРОСИТ СВЯЗАТЬСЯ\n\n"
            f"Имя: {user.full_name}\n"
            f"Username: {username}\n"
            f"Telegram ID: {user.id}"
        ),
    )

    await update.message.reply_text(
        "✅ Запрос отправлен менеджеру.\n"
        "С вами свяжутся в Telegram.",
        reply_markup=MAIN_KEYBOARD,
    )


async def cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    context.user_data.clear()

    await update.message.reply_text(
        "Заполнение заявки отменено.",
        reply_markup=MAIN_KEYBOARD,
    )
    return ConversationHandler.END


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "Выберите нужное действие с помощью кнопок.\n\n"
        "Для отмены заполнения заявки отправьте /cancel.",
        reply_markup=MAIN_KEYBOARD,
    )


async def unknown_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await update.message.reply_text(
        "Чтобы отправить запрос, нажмите кнопку "
        "«🔎 Найти препарат» или «📦 Проверить наличие».",
        reply_markup=MAIN_KEYBOARD,
    )


def main():
    if not TOKEN:
        raise ValueError(
            "Не найдена переменная BOT_TOKEN. "
            "Добавьте токен в защищённые переменные проекта."
        )

    app = Application.builder().token(TOKEN).build()

    request_conversation = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex(
                    r"^(🔎 Найти препарат|📦 Проверить наличие|"
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
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_handler(request_conversation)

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^🚚 Доставка$"),
            delivery_info,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^👨‍💼 Связаться с менеджером$"),
            contact_manager,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            unknown_message,
        )
    )

    print("Бот Pharma.Pro запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
