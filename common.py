import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import ADMIN_CHAT_ID, TELEGRAM_BUSINESS_CHAT_LINK
from keyboards import CANCEL_KEYBOARD, CONTACT_KEYBOARD, SEARCH_KEYBOARD, main_keyboard_for
from messages import HOW_IT_WORKS_TEXT, WELCOME_TEXT
from utils import clear_request_keep_source, get_source_name, safe, user_details_html
from stats import (
    EVENT_OPERATOR,
    EVENT_START,
    build_stats_period_report,
    build_stats_summary,
    get_last_source,
    record_event,
)

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
    user = update.effective_user
    source = get_source_name(context)
    if not context.args and source == "Telegram-бот":
        source = get_last_source(user.id) or source
    context.user_data.clear()
    context.user_data["source"] = source
    record_event(user.id, EVENT_START, source)
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_keyboard_for(update.effective_user.id),
    )


async def start_and_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)
    return ConversationHandler.END


async def show_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["source"] = context.user_data.get("source") or get_last_source(update.effective_user.id) or "Telegram-бот"
    clear_request_keep_source(context)
    await update.message.reply_text("Что вы хотите найти?", reply_markup=SEARCH_KEYBOARD)
    return ConversationHandler.END


async def return_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["source"] = context.user_data.get("source") or get_last_source(update.effective_user.id) or "Telegram-бот"
    clear_request_keep_source(context)
    await update.message.reply_text("Главное меню:", reply_markup=main_keyboard_for(update.effective_user.id))
    return ConversationHandler.END


async def how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["source"] = context.user_data.get("source") or get_last_source(update.effective_user.id) or "Telegram-бот"
    clear_request_keep_source(context)
    await update.message.reply_text(HOW_IT_WORKS_TEXT, reply_markup=main_keyboard_for(update.effective_user.id))
    return ConversationHandler.END


async def _send_operator_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_source = context.user_data.get("source") or get_last_source(update.effective_user.id) or "Telegram-бот"
    context.user_data["source"] = raw_source
    source = safe(raw_source)
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
    record_event(update.effective_user.id, EVENT_OPERATOR, raw_source)


async def contact_operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct operator button: hand the user off to Telegram Business.

    The existing request-submission flow is not changed. If the Business link has
    not been configured yet, the previous operator-request behavior remains as a
    safe fallback.
    """
    source = context.user_data.get("source") or get_last_source(update.effective_user.id) or "Telegram-бот"
    clear_request_keep_source(context)
    context.user_data["source"] = source

    if TELEGRAM_BUSINESS_CHAT_LINK:
        record_event(update.effective_user.id, EVENT_OPERATOR, source)
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("💬 Открыть чат с оператором", url=TELEGRAM_BUSINESS_CHAT_LINK)]]
        )
        await update.message.reply_text(
            "Нажмите кнопку ниже, чтобы открыть чат с оператором Pharma Pro.\n\n"
            "В Telegram уже будет подготовлено короткое сообщение — вам останется нажать «Отправить».",
            reply_markup=markup,
        )
        return ConversationHandler.END

    # Safe fallback until TELEGRAM_BUSINESS_CHAT_LINK is added in Railway.
    if _needs_contact(update, context):
        await _ask_for_contact(update, context, "operator")
        return ConversationHandler.END

    try:
        await _send_operator_request(update, context)
        await update.message.reply_text(
            "✅ Сообщение отправлено оператору.\nС вами свяжутся в Telegram.",
            reply_markup=main_keyboard_for(update.effective_user.id),
        )
    except Exception:
        logger.exception("Failed to send operator request")
        await update.message.reply_text(
            "⚠️ Не удалось отправить сообщение. Попробуйте немного позже.",
            reply_markup=main_keyboard_for(update.effective_user.id),
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
                reply_markup=main_keyboard_for(update.effective_user.id),
            )
        except Exception:
            logger.exception("Failed to send operator request after contact")
            await update.message.reply_text(
                "⚠️ Контакт получен, но сейчас не удалось уведомить оператора. "
                "Попробуйте немного позже.",
                reply_markup=main_keyboard_for(update.effective_user.id),
            )
        clear_request_keep_source(context)
        return

    # Для обычного запроса обработка продолжится внутри ConversationHandler.
    await update.message.reply_text(
        "✅ Контакт сохранён.",
        reply_markup=main_keyboard_for(update.effective_user.id),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["source"] = context.user_data.get("source") or get_last_source(update.effective_user.id) or "Telegram-бот"
    clear_request_keep_source(context)
    await update.message.reply_text("Запрос отменён.", reply_markup=main_keyboard_for(update.effective_user.id))
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выберите нужное действие с помощью кнопок.\n\n"
        "Для отмены отправьте /cancel или нажмите «❌ Отменить запрос».",
        reply_markup=main_keyboard_for(update.effective_user.id),
    )


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Чтобы оформить запрос, выберите действие с помощью кнопок ниже.",
        reply_markup=main_keyboard_for(update.effective_user.id),
    )


async def unknown_in_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Не удалось распознать этот ответ. Ответьте на текущий вопрос, "
        "нажмите «💬 Связаться с оператором» или «❌ Отменить запрос».",
        reply_markup=CANCEL_KEYBOARD,
    )


def _stats_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Сегодня", callback_data="stats:today"),
                InlineKeyboardButton("7 дней", callback_data="stats:7d"),
            ],
            [
                InlineKeyboardButton("30 дней", callback_data="stats:30d"),
                InlineKeyboardButton("Всё время", callback_data="stats:all"),
            ],
        ]
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("Команда недоступна.")
        return
    await update.message.reply_text(build_stats_summary(), reply_markup=_stats_markup())


async def stats_period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if query.from_user.id != ADMIN_CHAT_ID:
        await query.answer("Команда недоступна.", show_alert=True)
        return
    period = query.data.split(":", 1)[1] if ":" in query.data else "today"
    try:
        text = build_stats_period_report(period)
    except ValueError:
        text = "⚠️ Неизвестный период статистики."
    await query.edit_message_text(text=text, reply_markup=_stats_markup())
