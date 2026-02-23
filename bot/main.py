import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv

from bot.db import DB
from bot.llm_gigachat import from_env
from bot.prompt import PROMPT_SQL_SYSTEM
from bot.sql_guard import validate_sql

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]



bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

db = DB(DATABASE_URL)
llm = from_env()


@dp.message(F.text)
async def handle_text(message: Message):
    user_text = (message.text or "").strip()
    if not user_text:
        return

    try:
        sql = await llm.to_sql(PROMPT_SQL_SYSTEM, user_text)
        validate_sql(sql)
        value = await db.fetch_value(sql)
        await message.answer(str(value))
    except Exception as e:
        logging.exception("Error")
        await message.answer("-1")


async def main():
    await db.start()
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())