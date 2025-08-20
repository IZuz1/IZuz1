import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Клиент возьмёт ключ из GEMINI_API_KEY автоматически (или можно client = genai.Client(api_key=...))
client = genai.Client()

WELCOME_TEXT = (
    "Привет! Я Telegram-бот на Google Gemini. Напиши сообщение — отвечу.\n\n"
    "Команды:\n"
    "/start — приветствие\n"
    "/help — помощь"
)

HELP_TEXT = (
    "Отправь текст — я верну ответ от модели Gemini.\n"
    "Показываю только финальный ответ, без промежуточных рассуждений."
)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        # Stateless-вызов Gemini. По желанию можно добавить свою память чата (history) поверх.
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction="Отвечай кратко и по делу. Не раскрывай ход рассуждений.",
                temperature=0.7,
                max_output_tokens=600,
                # Отключаем 'thinking' для 2.5 flash (снижает расход и исключает CoT-вывод)
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        ai_text = (resp.text or "").strip()
        if not ai_text:
            ai_text = "Хмм, не смог сформировать ответ. Попробуй переформулировать."

        await update.message.reply_text(ai_text, disable_web_page_preview=True)

    except Exception as e:
        logging.exception("Gemini API error")
        await update.message.reply_text(f"Упс, произошла ошибка: {e}")

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN отсутствует. Укажи его в .env")
    # GEMINI_API_KEY читает сам клиент (переменная окружения обязательна)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # Без asyncio.run: PTB сам управляет event loop
    app.run_polling()
