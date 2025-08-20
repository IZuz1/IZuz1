import logging
import os

from dotenv import load_dotenv
from openai import OpenAI
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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1")
APP_PUBLIC_URL = os.getenv("APP_PUBLIC_URL")  # для HTTP-Referer (опционально)
APP_TITLE = os.getenv("APP_TITLE")            # для X-Title (опционально)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# OpenRouter: OpenAI-совместимый клиент + свой base_url
client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

WELCOME_TEXT = (
    "Привет! Я Telegram-бот через OpenRouter + DeepSeek R1. Пиши — отвечу.\n\n"
    "Команды:\n"
    "/start — приветствие\n"
    "/help — помощь"
)

HELP_TEXT = (
    "Отправь текст — верну ответ от модели DeepSeek R1 через OpenRouter.\n"
    "Показываю только финальный ответ (без CoT/рассуждений)."
)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)

def _extra_headers():
    # Опциональные заголовки для OpenRouter (идентификация приложения)
    hdrs = {}
    if APP_PUBLIC_URL:
        hdrs["HTTP-Referer"] = APP_PUBLIC_URL
    if APP_TITLE:
        hdrs["X-Title"] = APP_TITLE
    return hdrs or None

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        # Через OpenRouter используем OpenAI-совместимый Chat Completions
        resp = client.chat.completions.create(
            model=OPENROUTER_MODEL,  # напр. deepseek/deepseek-r1:free
            messages=[
                {"role": "system", "content": "Отвечай кратко и по делу. Не раскрывай ход рассуждений."},
                {"role": "user", "content": user_text},
            ],
            temperature=0.7,
            max_tokens=600,
            extra_headers=_extra_headers(),
        )

        ai_text = (resp.choices[0].message.content or "").strip()
        if not ai_text:
            ai_text = "Хмм, не смог сформировать ответ. Попробуй переформулировать."
        await update.message.reply_text(ai_text, disable_web_page_preview=True)

    except Exception as e:
        logging.exception("OpenRouter API error")
        await update.message.reply_text(f"Упс, произошла ошибка: {e}")

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN отсутствует. Укажи его в .env")
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY отсутствует. Укажи его в .env")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # Без asyncio.run: PTB сам управляет event loop
    app.run_polling()
