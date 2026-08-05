import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import ADMIN_CHAT_ID
from keyboards import CANCEL_KEYBOARD, CONFIRM_KEYBOARD, MAIN_KEYBOARD
from messages import REQUEST_ACCEPTED_TEXT, SEND_ERROR_TEXT
from utils import admin_card_html, clear_request_keep_source, confirmation_text, make_request_id

logger = logging.getLogger(__name__)

(SINGLE_NAME, SINGLE_DOSAGE, SINGLE_QUANTITY, FLEXIBLE_CONTENT, LOCATION, CONFIRM) = range(6)


def reset_for_request(update, context, request_type):
    source = context.user_data.get("source", "Telegram-бот")
    context.user_data.clear()
    context.user_data.update(
        source=source,
        request_type=request_type,
        request_id=make_request_id(update.effective_user.id),
    )


async def begin_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_for_request(update, context, "Один препарат")
    await update.message.reply_text(
        "Напишите полное название препарата:",
        reply_markup=CANCEL_KEYBOARD,
    )
    return SINGLE_NAME


async def receive_single_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["medicine"] = update.message.text.strip()
    await update.message.reply_text(
        "Укажите дозировку.\n\nНапример: 10 мг, 20 мг или 100 мл.\n"
        "Если не знаете, напишите «Не знаю».",
        reply_markup=CANCEL_KEYBOARD,
    )
    return SINGLE_DOSAGE


async def receive_single_dosage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["dosage"] = update.message.text.strip()
    await update.message.reply_text(
        "Сколько упаковок требуется?\n\nНапример: 1, 2 или 3.",
        reply_markup=CANCEL_KEYBOARD,
    )
    return SINGLE_QUANTITY


async def receive_single_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["quantity"] = update.message.text.strip()
    await ask_location(update)
    return LOCATION


async def begin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await begin_flexible(
        update,
        context,
        "Список препаратов",
        "Отправьте весь список одним сообщением.\n\n"
        "Можно написать текстом, прислать фотографию или документ.",
    )


async def begin_analog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await begin_flexible(
        update,
        context,
        "Подбор турецкого аналога",
        "Отправьте название одного или нескольких препаратов, "
        "фотографию упаковки, рецепта или документ.\n\n"
        "По возможности укажите дозировку и форму выпуска.",
    )


async def begin_photo_or_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await begin_flexible(
        update,
        context,
        "Фото рецепта или список",
        "Отправьте информацию текстом, фотографией или документом.",
    )


async def begin_flexible(update, context, request_type, prompt):
    reset_for_request(update, context, request_type)
    await update.message.reply_text(prompt, reply_markup=CANCEL_KEYBOARD)
    return FLEXIBLE_CONTENT


async def receive_flexible_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.text:
        context.user_data["content_text"] = message.text.strip()
    elif message.photo:
        context.user_data.update(
            attachment_type="photo",
            attachment_file_id=message.photo[-1].file_id,
            attachment_label="Фотография",
        )
        if message.caption:
            context.user_data["content_text"] = message.caption.strip()
    elif message.document:
        filename = message.document.file_name or "без названия"
        context.user_data.update(
            attachment_type="document",
            attachment_file_id=message.document.file_id,
            attachment_label=f"Документ: {filename}",
        )
        if message.caption:
            context.user_data["content_text"] = message.caption.strip()
    else:
        await message.reply_text(
            "Отправьте текст, фотографию или документ.",
            reply_markup=CANCEL_KEYBOARD,
        )
        return FLEXIBLE_CONTENT
    await ask_location(update)
    return LOCATION


async def ask_location(update: Update):
    await update.message.reply_text(
        "Укажите страну и город получения.\n\nНапример: Россия, Москва.",
        reply_markup=CANCEL_KEYBOARD,
    )


async def receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["location"] = update.message.text.strip()
    await update.message.reply_text(
        confirmation_text(context),
        reply_markup=CONFIRM_KEYBOARD,
    )
    return CONFIRM


async def restart_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_type = context.user_data.get("request_type")
    if request_type == "Один препарат":
        return await begin_single(update, context)
    if request_type == "Список препаратов":
        return await begin_list(update, context)
    if request_type == "Подбор турецкого аналога":
        return await begin_analog(update, context)
    return await begin_photo_or_list(update, context)


async def send_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_card_html(update, context),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        file_id = context.user_data.get("attachment_file_id")
        attachment_type = context.user_data.get("attachment_type")
        caption = (
            "📎 Вложение к запросу\n"
            f"Номер: {context.user_data.get('request_id', 'не указан')}\n"
            f"Тип: {context.user_data.get('request_type', 'Запрос')}\n"
            f"Имя: {update.effective_user.full_name}\n"
            f"Telegram ID: {update.effective_user.id}"
        )
        if file_id and attachment_type == "photo":
            await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=file_id, caption=caption)
        elif file_id and attachment_type == "document":
            await context.bot.send_document(chat_id=ADMIN_CHAT_ID, document=file_id, caption=caption)

        await update.message.reply_text(
            REQUEST_ACCEPTED_TEXT,
            reply_markup=MAIN_KEYBOARD,
        )
    except Exception:
        logger.exception("Failed to send request")
        await update.message.reply_text(SEND_ERROR_TEXT, reply_markup=MAIN_KEYBOARD)

    clear_request_keep_source(context)
    return ConversationHandler.END
