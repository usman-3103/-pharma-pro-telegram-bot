import logging
import asyncio
import threading

from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters

from config import BOT_TOKEN
from handlers.common import (
    cancel, contact_operator, help_command, how_it_works, receive_shared_contact,
    return_to_main, show_search_menu, start, start_and_end, unknown_in_request, unknown_message,
)
from handlers.requests import (
    CONFIRM, CONTACT, FLEXIBLE_CONTENT, LOCATION, SINGLE_DOSAGE, SINGLE_NAME, SINGLE_QUANTITY,
    begin_analog, begin_list, begin_photo_or_list, begin_single,
    receive_flexible_content, receive_location, receive_more_attachment, receive_request_contact,
    receive_single_dosage, receive_single_name, receive_single_quantity,
    restart_request, send_request, wrong_single_name_type,
)
from health import run_health_server

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def error_handler(update, context):
    logger.error(
        "Unhandled bot error",
        exc_info=(type(context.error), context.error, context.error.__traceback__),
    )


def build_request_conversation():
    cancel_button = filters.Regex(r"^❌ Отменить запрос$")
    main_action = filters.Regex(
        r"^(🔍 Найти препарат|📷 Отправить рецепт или список|ℹ️ Как это работает|"
        r"💬 Связаться с оператором|↩️ Вернуться в меню|💊 Один препарат|"
        r"📋 Список препаратов|🔄 Подобрать турецкий аналог)$"
    )
    normal_text = filters.TEXT & ~filters.COMMAND & ~cancel_button & ~main_action

    fallbacks = [
        CommandHandler("cancel", cancel),
        CommandHandler("start", start_and_end),
        MessageHandler(cancel_button, cancel),
        MessageHandler(filters.Regex(r"^💬 Связаться с оператором$"), contact_operator),
        MessageHandler(filters.Regex(r"^🔍 Найти препарат$"), show_search_menu),
        MessageHandler(filters.Regex(r"^↩️ Вернуться в меню$"), return_to_main),
        MessageHandler(filters.Regex(r"^ℹ️ Как это работает$"), how_it_works),
        CommandHandler("help", help_command),
        MessageHandler(filters.ALL, unknown_in_request),
    ]

    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^💊 Один препарат$"), begin_single),
            MessageHandler(filters.Regex(r"^📋 Список препаратов$"), begin_list),
            MessageHandler(filters.Regex(r"^🔄 Подобрать турецкий аналог$"), begin_analog),
            MessageHandler(filters.Regex(r"^📷 Отправить рецепт или список$"), begin_photo_or_list),
        ],
        states={
            SINGLE_NAME: [
                MessageHandler(normal_text, receive_single_name),
                MessageHandler(filters.PHOTO | filters.Document.ALL, wrong_single_name_type),
            ],
            SINGLE_DOSAGE: [MessageHandler(normal_text, receive_single_dosage)],
            SINGLE_QUANTITY: [MessageHandler(normal_text, receive_single_quantity)],
            FLEXIBLE_CONTENT: [
                MessageHandler(
                    (normal_text | filters.PHOTO | filters.Document.ALL),
                    receive_flexible_content,
                )
            ],
            LOCATION: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, receive_more_attachment),
                MessageHandler(normal_text, receive_location),
            ],
            CONFIRM: [
                MessageHandler(filters.Regex(r"^✅ Отправить запрос$"), send_request),
                MessageHandler(filters.Regex(r"^✏️ Заполнить заново$"), restart_request),
            ],
            CONTACT: [
                MessageHandler(filters.CONTACT, receive_request_contact),
                MessageHandler(filters.Regex(r"^↩️ Вернуться в меню$"), return_to_main),
            ],
        },
        fallbacks=fallbacks,
        allow_reentry=True,
    )


def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(build_request_conversation())

    app.add_handler(MessageHandler(filters.Regex(r"^🔍 Найти препарат$"), show_search_menu))
    app.add_handler(MessageHandler(filters.Regex(r"^↩️ Вернуться в меню$"), return_to_main))
    app.add_handler(MessageHandler(filters.Regex(r"^ℹ️ Как это работает$"), how_it_works))
    app.add_handler(MessageHandler(filters.Regex(r"^💬 Связаться с оператором$"), contact_operator))
    app.add_handler(MessageHandler(filters.CONTACT, receive_shared_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))
    app.add_error_handler(error_handler)

    logger.info("Pharma.Pro Bot final version started")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
