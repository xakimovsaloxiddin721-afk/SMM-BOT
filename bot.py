import asyncio
import logging
import os

from aiogram import Bot, Dispatcher

from database import db
from start import router as start_router
from admin import router as admin_router
from numbers import router as numbers_router
from stars import router as stars_router
from nakrutka import router as nakrutka_router


async def main():
    logging.basicConfig(level=logging.INFO)

    bot_token = os.getenv("BOT_TOKEN")

    if not bot_token:
        raise RuntimeError("BOT_TOKEN topilmadi!")

    await db.init()

    bot = Bot(token=bot_token)
    dp = Dispatcher()

    dp.include_router(start_router)
    dp.include_router(admin_router)
    dp.include_router(numbers_router)
    dp.include_router(stars_router)
    dp.include_router(nakrutka_router)

    print("🤖 Bot ishga tushdi!")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
