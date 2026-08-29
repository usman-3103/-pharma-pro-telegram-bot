from telegram import KeyboardButton, ReplyKeyboardMarkup

from config import ADMIN_CHAT_ID

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🔍 Найти препарат"],
        ["📷 Отправить рецепт или список"],
        ["ℹ️ Как это работает", "💬 Связаться с оператором"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие",
)

ADMIN_MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🔍 Найти препарат"],
        ["📷 Отправить рецепт или список"],
        ["ℹ️ Как это работает", "💬 Связаться с оператором"],
        ["📊 Статистика"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие",
)


def main_keyboard_for(user_id: int):
    return ADMIN_MAIN_KEYBOARD if user_id == ADMIN_CHAT_ID else MAIN_KEYBOARD


SEARCH_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["💊 Один препарат"],
        ["📋 Список препаратов"],
        ["🔄 Подобрать турецкий аналог"],
        ["↩️ Вернуться в меню"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите вариант",
)

CANCEL_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["💬 Связаться с оператором"],
        ["❌ Отменить запрос"],
    ],
    resize_keyboard=True,
)

CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["✅ Отправить запрос"],
        ["💬 Связаться с оператором"],
        ["✏️ Заполнить заново", "❌ Отменить запрос"],
    ],
    resize_keyboard=True,
)

CONTACT_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📱 Поделиться контактом", request_contact=True)],
        ["↩️ Вернуться в меню"],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Поделитесь контактом",
)
