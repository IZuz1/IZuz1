import logging
import os
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor
from dotenv import load_dotenv

# Load token from .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Setup
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Пользовательские лимиты на цитаты
user_last_quote_time = {}

# Цитаты INSANITY (100 штук)
INSANITY_QUOTES = [
    "Ты — не бренд. Ты диагноз.",
    "Мама — твой первый маркетолог.",
    "Креатив без риска — это PowerPoint, а не искусство.",
    "Если идея не пугает — она не живая.",
    "Идея — это вирус. Если она никого не заразила, это просто мысль.",
    "Умеренные креаторы попадают в презентации. Безумные — в историю.",
    "Люди не хотят рекламу. Люди хотят культ.",
    "Ты не придумываешь идеи. Ты просто открываешь дверь безумию.",
    "Если ты хочешь всем угодить — иди печь булочки.",
    "Контент — это кровь. И ты её должен пролить.",
    "Каждая идея должна звучать как заголовок на войне.",
    "Ты не креатор, если ни разу не облажался красиво.",
    "Вирусность начинается там, где заканчивается стыд.",
    "Если фокус-группа всё поняла — значит ты не доработал.",
    "Бренд — это личность. А личность без травмы неинтересна.",
    "Копирайтинг — это поэзия под наркозом.",
    "Хорошая идея — как первая сигарета: немного страшно и невозможно забыть.",
    "Нормальность — это болезнь, которую мы лечим креативом.",
    "Чем проще мысль — тем глубже шок.",
    "Скучные бренды умирают стоя."
] + [
    f"INSANITY #{i}: {s}"
    for i, s in enumerate([
        "Будь неузнаваемым. Тогда тебя невозможно скопировать.",
        "Любая настоящая идея — это акт сопротивления.",
        "Если все согласны — значит, никто не чувствует.",
        "Ирония — это броня креатора.",
        "Продай боль. Люди купят честность.",
        "Хайп — это побочный эффект глубины.",
        "Истории работают, когда в них кто-то страдает.",
        "Бренд без безумия — как сторис без звука.",
        "Пиши так, как будто завтра тебя забанят.",
        "Если идея не вызывает истерику в чате — переделывай.",
        "Фидбек — это шёпот страха. Игнорируй его.",
        "Инсайт — это когда ты стыдишься, но киваешь.",
        "Спроси себя: что бы сделал художник с психозом?", 
        "Красота в несовершенстве. Деньги — в безумии.",
        "Брендинг — это татуировка на подсознании.",
        "Снимай рекламные манифесты, а не ролики.",
        "Будь резонансом, а не эхом.",
        "Пусть они боятся запускать твою идею. Тогда она сработает.",
        "Сделай так, чтобы они смеялись, потом плакали, потом репостили.",
        "Невозможно — это просто ещё не пошло в тренды."
    ], start=10)
]

# /start
@dp.message_handler(commands=['start'])
async def start_cmd(message: Message):
    await message.answer(
        "🤖 *INSANITY BOT активирован.*\n"
        "Это не бот. Это вызов.\n\n"
        "Команда доступна: `/quote` — дай мне креативную цитату, которая звучит как пощёчина."
    )

# /quote — цитата от INSANITY (1 раз в сутки)
@dp.message_handler(commands=['quote'])
async def quote(message: Message):
    user_id = message.from_user.id
    now = datetime.now()

    if user_id in user_last_quote_time:
        last_time = user_last_quote_time[user_id]
        if now - last_time < timedelta(days=1):
            remaining = timedelta(days=1) - (now - last_time)
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            await message.answer(f"🛑 Сегодня ты уже получал свою дозу безумия. Возвращайся через {hours} ч. {minutes} мин.")
            return

    quote = random.choice(INSANITY_QUOTES)
    user_last_quote_time[user_id] = now
    await message.answer(f"🧠 *INSANITY говорит:*\n\n_{quote}_", parse_mode="Markdown")

# Run the bot
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
