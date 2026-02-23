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

def normalize_sql(sql: str) -> str:
    s = (sql or "").strip()

    # убрать ```sql ... ``` или ``` ... ```
    if s.startswith("```"):
        s = s.strip().strip("`").strip()
        lines = s.splitlines()
        if lines and lines[0].lower().strip() == "sql":
            s = "\n".join(lines[1:]).strip()

    # отрезать всё после первого ';'
    if ";" in s:
        s = s.split(";", 1)[0].strip()

    # убрать возможный префикс "SQL:"/"sql:"
    if s.lower().startswith("sql:"):
        s = s[4:].strip()

    return s

@dp.message(F.text)
async def handle_text(message: Message):
    user_text = (message.text or "").strip()
    if not user_text:
        return

    sql = await llm.to_sql(PROMPT_SQL_SYSTEM, user_text)
    sql = normalize_sql(sql)

    try:
        validate_sql(sql)
    except Exception as e:
        repair_prompt = (
            PROMPT_SQL_SYSTEM
            + "\n\nВАЖНО: Верни ТОЛЬКО SQL-SELECT без Markdown и без текста вокруг."
        )
        sql = await llm.to_sql(repair_prompt, user_text)
        sql = normalize_sql(sql)
        validate_sql(sql)
    
    value = await db.fetch_value(sql)
    await message.answer(str(value))


async def main():
    await db.start()
    try:
        await dp.start_polling(bot)
    finally:
        await db.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())