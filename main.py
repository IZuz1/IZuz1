import logging
import os
import mimetypes
from io import BytesIO

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

client = genai.Client()  # берёт GEMINI_API_KEY из окружения

WELCOME_TEXT = (
    "Привет! Я Telegram-бот на Google Gemini. Напиши текст или пришли голос — отвечу.\n\n"
    "Команды:\n"
    "/start — приветствие\n"
    "/help — помощь"
)

HELP_TEXT = (
    "Отправь текст или голосовое/аудио/видео-заметку — я распознаю речь и отвечу.\n"
    "Показываю только финальный ответ, без промежуточных рассуждений."
)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)

# ---------- ТЕКСТ ----------
async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction="Отвечай кратко и по делу. Не раскрывай ход рассуждений.",
                temperature=0.7,
                max_output_tokens=600,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        ai_text = (resp.text or "").strip() or "Хмм, не смог сформировать ответ. Попробуй переформулировать."
        await update.message.reply_text(ai_text, disable_web_page_preview=True)

    except Exception as e:
        logging.exception("Gemini API error")
        await update.message.reply_text(f"Упс, произошла ошибка: {e}")

# ---------- ГОЛОС/АУДИО/ВИДЕО (STT) ----------
# >>> добавлено для голоса
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    if not msg:
        return

    # Определяем источник и file_id
    tg_file = None
    display_kind = None
    if msg.voice:         # голосовая заметка (.ogg/opus)
        tg_file = msg.voice
        display_kind = "voice"
    elif msg.audio:       # аудиофайл (mp3/ogg/wav/etc)
        tg_file = msg.audio
        display_kind = "audio"
    elif msg.video_note:  # видеозаметка (обычно .mp4/.webm с аудиодорожкой)
        tg_file = msg.video_note
        display_kind = "video_note"
    else:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_AUDIO)

    try:
        # 1) Скачиваем файл в память
        file_obj = await context.bot.get_file(tg_file.file_id)
        buf = BytesIO()
        await file_obj.download(out=buf)  # PTB v22: File.download(out=BytesIO)
        audio_bytes = buf.getvalue()

        # 2) Определяем mime type
        mime = None
        # (а) пробуем из Telegram-объекта
        if hasattr(tg_file, "mime_type") and getattr(tg_file, "mime_type", None):
            mime = tg_file.mime_type
        # (б) если у файла есть расширение в пути — попробуем по нему
        if not mime and getattr(file_obj, "file_path", None):
            mime, _ = mimetypes.guess_type(file_obj.file_path)
        # (в) дефолт: голос чаще всего .ogg/opus
        if not mime:
            mime = "audio/ogg"

        # 3) Просим Gemini сделать транскрипт (статус: "только текст")
        stt_prompt = "Преобразуй речь в текст на русском языке. Верни только транскрипт без лишних слов."
        stt_resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(stt_prompt),
                        types.Part(
                            inline_data=types.Blob(
                                mime_type=mime,
                                data=audio_bytes,
                            )
                        ),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=800,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        transcript = (stt_resp.text or "").strip()
        if not transcript:
            await msg.reply_text("Не удалось распознать речь. Попробуй записать чуть чётче/громче.")
            return

        # 4) Делаем обычный ответ модели на распознанный текст
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=transcript,
            config=types.GenerateContentConfig(
                system_instruction="Отвечай кратко и по делу. Не раскрывай ход рассуждений.",
                temperature=0.7,
                max_output_tokens=600,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        answer = (resp.text or "").strip() or "Хмм, не смог ответить на это."

        # 5) Покажем и распознанный текст, и ответ
        await msg.reply_text(
            f"_Распознанный текст ({display_kind}):_\n{transcript}\n\n{answer}",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

    except Exception as e:
        logging.exception("STT/Gemini error")
        await update.message.reply_text(f"Ошибка распознавания/ответа: {e}")

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN отсутствует. Укажи его в .env")

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))

    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler))
    # >>> добавлено для голоса
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO_NOTE, voice_handler))

    app.run_polling()
