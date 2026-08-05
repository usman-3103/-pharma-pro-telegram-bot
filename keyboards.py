from telegram import ReplyKeyboardMarkup

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🔍 Найти препарат"],
        ["📷 Отправить рецепт или список"],
        ["ℹ️ Как это работает", "💬 Связаться с оператором"],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие",
)

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
    [["❌ Отменить запрос"]],
    resize_keyboard=True,
)

CONFIRM_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["✅ Отправить запрос"],
        ["✏️ Заполнить заново", "❌ Отменить запрос"],
    ],
    resize_keyboard=True,
)
