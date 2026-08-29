import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import ADMIN_CHAT_ID
from keyboards import CANCEL_KEYBOARD, CONFIRM_KEYBOARD, CONTACT_KEYBOARD, MAIN_KEYBOARD
from messages import REQUEST_ACCEPTED_TEXT, SEND_ERROR_TEXT
from utils import admin_card_html, clear_request_keep_source, confirmation_text, make_request_id
from stats import EVENT_REQUEST, get_last_source, record_event

logger = logging.getLogger(__name__)

(SINGLE_NAME, SINGLE_DOSAGE, SINGLE_QUANTITY, FLEXIBLE_CONTENT, LOCATION, CONFIRM, CONTACT) = range(7)


def reset_for_request(update, context, request_type):
    source = context.user_data.get("source") or get_last_source(update.effective_user.id) or "Telegram-бот"
    context.user_data.clear()
    context.user_data.update(
        source=source,
        request_type=request_type,
        request_id=make_request_id(update.effective_user.id),
        attachments=[],
    )


async def begin_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_for_request(update, context, "Один препарат")
    await update.message.reply_text(
        "Напишите полное название препарата:",
        reply_markup=CANCEL_KEYBOARD,
    )
    return SINGLE_NAME


async def wrong_single_name_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здесь нужно написать название препарата текстом.\n\n"
        "Если хотите отправить фотографию упаковки, рецепт, список или файл — "
        "нажмите «📷 Отправить рецепт или список».",
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
        "Отправьте весь список одним сообщением или несколькими фотографиями.\n\n"
        "Можно написать текстом, прислать фотографии или документ.",
    )


async def begin_analog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await begin_flexible(
        update,
        context,
        "Подбор турецкого аналога",
        "Отправьте название одного или нескольких препаратов, фотографию упаковки, "
        "рецепта или документ. Можно отправить несколько фотографий.\n\n"
        "По возможности укажите дозировку и форму выпуска.",
    )


async def begin_photo_or_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await begin_flexible(
        update,
        context,
        "Фото рецепта или список",
        "Отправьте информацию текстом, фотографией или документом. "
        "Можно отправить несколько фотографий подряд.",
    )


async def begin_flexible(update, context, request_type, prompt):
    reset_for_request(update, context, request_type)
    await update.message.reply_text(prompt, reply_markup=CANCEL_KEYBOARD)
    return FLEXIBLE_CONTENT


def add_attachment(message, context):
    attachments = context.user_data.setdefault("attachments", [])
    if message.photo:
        attachments.append({
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "label": "Фотография",
        })
    elif message.document:
        filename = message.document.file_name or "без названия"
        attachments.append({
            "type": "document",
            "file_id": message.document.file_id,
            "label": f"Документ: {filename}",
        })
    if message.caption:
        caption = message.caption.strip()
        if caption:
            previous = context.user_data.get("content_text")
            context.user_data["content_text"] = f"{previous}\n{caption}" if previous else caption


def update_attachment_label(context):
    attachments = context.user_data.get("attachments", [])
    if not attachments:
        context.user_data.pop("attachment_label", None)
        return
    photos = sum(1 for item in attachments if item["type"] == "photo")
    documents = sum(1 for item in attachments if item["type"] == "document")
    parts = []
    if photos:
        parts.append(f"фото: {photos}")
    if documents:
        parts.append(f"документов: {documents}")
    context.user_data["attachment_label"] = ", ".join(parts)


async def receive_flexible_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.text:
        context.user_data["content_text"] = message.text.strip()
    elif message.photo or message.document:
        add_attachment(message, context)
        update_attachment_label(context)
    else:
        await message.reply_text(
            "Отправьте текст, фотографию или документ.",
            reply_markup=CANCEL_KEYBOARD,
        )
        return FLEXIBLE_CONTENT
    await ask_location(update)
    return LOCATION


async def receive_more_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_attachment(update.message, context)
    update_attachment_label(context)
    count = len(context.user_data.get("attachments", []))
    await update.message.reply_text(
        f"✅ Вложение добавлено. Всего вложений: {count}.\n\n"
        "Можете отправить ещё или укажите страну и город получения.",
        reply_markup=CANCEL_KEYBOARD,
    )
    return LOCATION


async def ask_location(update: Update):
    await update.message.reply_text(
        "Укажите страну и город получения.\n\n"
        "Если нужно, перед ответом можете отправить ещё фотографии.\n"
        "Например: Россия, Москва.",
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


async def _deliver_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_card_html(update, context),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        attachments = context.user_data.get("attachments", [])
        base_caption = (
            "📎 Вложение к запросу\n"
            f"Номер: {context.user_data.get('request_id', 'не указан')}\n"
            f"Тип: {context.user_data.get('request_type', 'Запрос')}\n"
            f"Имя: {update.effective_user.full_name}\n"
            f"Telegram ID: {update.effective_user.id}"
        )
        total = len(attachments)
        for index, item in enumerate(attachments, start=1):
            caption = f"{base_caption}\nВложение: {index}/{total}" if total > 1 else base_caption
            if item["type"] == "photo":
                await context.bot.send_photo(
                    chat_id=ADMIN_CHAT_ID,
                    photo=item["file_id"],
                    caption=caption,
                )
            elif item["type"] == "document":
                await context.bot.send_document(
                    chat_id=ADMIN_CHAT_ID,
                    document=item["file_id"],
                    caption=caption,
                )

        record_event(
            update.effective_user.id,
            EVENT_REQUEST,
            context.user_data.get("source", "Telegram-бот"),
        )
        await update.message.reply_text(REQUEST_ACCEPTED_TEXT, reply_markup=MAIN_KEYBOARD)
        clear_request_keep_source(context)
        return ConversationHandler.END
    except Exception:
        logger.exception("Failed to send request")
        await update.message.reply_text(SEND_ERROR_TEXT, reply_markup=MAIN_KEYBOARD)
        return CONFIRM


async def send_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user.username and not context.user_data.get("contact_phone"):
        context.user_data["pending_contact_purpose"] = "request"
        await update.message.reply_text(
            "Перед отправкой нужен способ связи с вами.\n\n"
            "У вас не указан публичный @username, поэтому оператор может не суметь "
            "открыть ваш профиль. Нажмите «📱 Поделиться контактом». "
            "Телефон будет виден только оператору вместе с запросом.",
            reply_markup=CONTACT_KEYBOARD,
        )
        return CONTACT
    return await _deliver_request(update, context)


async def receive_request_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    if not contact:
        await update.message.reply_text(
            "Нажмите кнопку «📱 Поделиться контактом» или вернитесь в меню.",
            reply_markup=CONTACT_KEYBOARD,
        )
        return CONTACT
    if contact.user_id and contact.user_id != update.effective_user.id:
        await update.message.reply_text(
            "Пожалуйста, отправьте именно свой контакт кнопкой «📱 Поделиться контактом».",
            reply_markup=CONTACT_KEYBOARD,
        )
        return CONTACT

    context.user_data["contact_phone"] = contact.phone_number
    context.user_data.pop("pending_contact_purpose", None)
    return await _deliver_request(update, context)

