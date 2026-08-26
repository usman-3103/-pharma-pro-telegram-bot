import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import ADMIN_CHAT_ID
from keyboards import CANCEL_KEYBOARD, CONTACT_KEYBOARD, MAIN_KEYBOARD, SEARCH_KEYBOARD
from messages import HOW_IT_WORKS_TEXT, WELCOME_TEXT
from utils import clear_request_keep_source, get_source_name, safe, user_details_html

logger = logging.getLogger(__name__)


def _needs_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    return not update.effective_user.username and not context.user_data.get("contact_phone")


async def _ask_for_contact(update: Update, context: ContextTypes.DEFAULT_TYPE, purpose: str):
    context.user_data["pending_contact_purpose"] = purpose
    await update.message.reply_text(
        "Чтобы оператор смог написать вам лично со своего Telegram-аккаунта, "
        "нужен доступный способ связи.\n\n"
        "У вас не указан публичный @username. Нажмите «📱 Поделиться контактом». "
        "Телефон будет передан только оператору вместе с вашим запросом.",
        reply_markup=CONTACT_KEYBOARD,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = get_source_name(context)
    context.user_data.clear()
    context.user_data["source"] = source
    user = update.effective_user
    await update.message.reply_text(
        WELCOME_TEXT.format(first_name=user.first_name or ""),
        reply_markup=MAIN_KEYBOARD,
    )


async def start_and_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)
    return ConversationHandler.END


async def show_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_request_keep_source(context)
    await update.message.reply_text("Что вы хотите найти?", reply_markup=SEARCH_KEYBOARD)
    return ConversationHandler.END


async def return_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_request_keep_source(context)
    await update.message.reply_text("Главное меню:", reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


async def how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_request_keep_source(context)
    await update.message.reply_text(HOW_IT_WORKS_TEXT, reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END


async def _send_operator_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = safe(context.user_data.get("source", "Telegram-бот"))
    text = (
        "💬 <b>ПРОСЬБА СВЯЗАТЬСЯ</b>\n\n"
        f"{user_details_html(update, context)}\n"
        f"📍 <b>Источник:</b> {source}"
    )
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def contact_operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    source = context.user_data.get("source", "Telegram-бот")
    clear_request_keep_source(context)
    context.user_data["source"] = source

    if _needs_contact(update, context):
        await _ask_for_contact(update, context, "operator")
        return ConversationHandler.END

    try:
        await _send_operator_request(update, context)
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
    return ConversationHandler.END


async def receive_shared_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        return

    if contact.user_id and contact.user_id != update.effective_user.id:
        await update.message.reply_text(
            "Пожалуйста, отправьте именно свой контакт кнопкой «📱 Поделиться контактом».",
            reply_markup=CONTACT_KEYBOARD,
        )
        return

    context.user_data["contact_phone"] = contact.phone_number
    purpose = context.user_data.pop("pending_contact_purpose", None)

    if purpose == "operator":
        try:
            await _send_operator_request(update, context)
            await update.message.reply_text(
                "✅ Контакт получен. Сообщение отправлено оператору.\n"
                "С вами свяжутся лично в Telegram.",
                reply_markup=MAIN_KEYBOARD,
            )
        except Exception:
            logger.exception("Failed to send operator request after contact")
            await update.message.reply_text(
                "⚠️ Контакт получен, но сейчас не удалось уведомить оператора. "
                "Попробуйте немного позже.",
                reply_markup=MAIN_KEYBOARD,
            )
        clear_request_keep_source(context)
        return

    # Для обычного запроса обработка продолжится внутри ConversationHandler.
    await update.message.reply_text(
        "✅ Контакт сохранён.",
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


async def unknown_in_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Не удалось распознать этот ответ. Ответьте на текущий вопрос, "
        "нажмите «💬 Связаться с оператором» или «❌ Отменить запрос».",
        reply_markup=CANCEL_KEYBOARD,
    )
