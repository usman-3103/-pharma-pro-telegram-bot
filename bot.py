import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуйте! 👋\n\n"
        "Я Pharma Pro — ваш помощник по поиску потенциальных клиентов.\n\n"
        "Нажмите /help, чтобы узнать, что я умею."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я могу помочь организовать поиск потенциальных клиентов.\n\n"
        "Команды:\n"
        "/start — запустить бота\n"
        "/help — помощь"
    )


def main():
    if not TOKEN:
        raise ValueError("Не найден BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    print("Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()
