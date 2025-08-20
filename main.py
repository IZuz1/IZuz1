import logging
import os

from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- настройка ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# --- OpenAI client ---
client = OpenAI(api_key=OPENAI_API_KEY)

WELCOME_TEXT = (
    "Привет! Я бот-посредник к модели ИИ. Напиши мне сообщение — отвечу.\n\n"
    "Команды:\n"
    "/start — приветствие\n"
    "/help — помощь"
)

HELP_TEXT = (
    "Просто отправь текст — я верну ответ от модели OpenAI.\n\n"
    "Подсказки:\n"
    "• Сообщения короче → ответ быстрее.\n"
    "• Если нужен стиль (список, код, шаги) — скажи об этом явно."
)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text

    # показать "печатает..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        # Вариант через Responses API (актуальный способ в SDK):
        # https://platform.openai.com/docs/guides/text / api-reference
        resp = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "system",
                    "content": "Ты дружелюбный и лаконичный помощник на русском языке.",
                },
                {
                    "role": "user",
                    "content": user_text,
                },
            ],
            # Можно немного ограничить длину и “болтливость”
            max_output_tokens=600,
        )

        # Унифицированный доступ к тексту (первый текстовый фрагмент)
        ai_text = resp.output_text

        if not ai_text:
            ai_text = "Хмм, не смог сформировать ответ. Попробуй переформулировать."

        await update.message.reply_text(ai_text, disable_web_page_preview=True)

    except Exception as e:
        logging.exception("OpenAI error")
        await update.message.reply_text(f"Упс, произошла ошибка: {e}")

if __name__ == "__main__":
    # строим приложение как раньше
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))

    # ВАЖНО: без asyncio.run и без await — этот вызов блокирующий и сам рулит циклом
    app.run_polling()
