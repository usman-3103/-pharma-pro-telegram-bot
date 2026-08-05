import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import ADMIN_CHAT_ID
from keyboards import MAIN_KEYBOARD, SEARCH_KEYBOARD
from messages import HOW_IT_WORKS_TEXT, WELCOME_TEXT
from utils import clear_request_keep_source, get_source_name, safe, user_details_html

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["source"] = get_source_name(context)
    user = update.effective_user
    await update.message.reply_text(
        WELCOME_TEXT.format(first_name=user.first_name or ""),
        reply_markup=MAIN_KEYBOARD,
    )


async def start_and_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)
    return ConversationHandler.END


async def show_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Что вы хотите найти?",
        reply_markup=SEARCH_KEYBOARD,
    )


async def return_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_request_keep_source(context)
    await update.message.reply_text("Главное меню:", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


async def how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HOW_IT_WORKS_TEXT, reply_markup=MAIN_KEYBOARD)


async def contact_operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = safe(context.user_data.get("source", "Telegram-бот"))
    text = (
        "💬 <b>ПРОСЬБА СВЯЗАТЬСЯ</b>\n\n"
        f"{user_details_html(update)}\n"
        f"📍 <b>Источник:</b> {source}"
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await update.message.reply_text(
            "✅ Сообщение отправлено оператору.\nС вами свяжутся в Telegram.",
            reply_markup=MAIN_KEYBOARD,
        )
    except Exception:
        logger.exception("Failed to send operator request")
        await update.message.reply_text(
            "⚠️ Не удалось отправить сообщение. Попробуйте немного позже.",
            reply_markup=MAIN_KEYBOARD,
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_request_keep_source(context)
    await update.message.reply_text("Запрос отменён.", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите нужное действие с помощью кнопок.\n\n"
        "Для отмены отправьте /cancel или нажмите «❌ Отменить запрос».",
        reply_markup=MAIN_KEYBOARD,
    )


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Чтобы оформить запрос, выберите действие с помощью кнопок ниже.",
        reply_markup=MAIN_KEYBOARD,
    )
