import asyncio, os

from aiogram import Bot, Dispatcher
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from db import Base

from dotenv import dotenv_values, load_dotenv

from handlers import commands, create_order, process_order

from middlewares import DbSessionMiddleware, LocaleMiddleware


async def main():
    load_dotenv(".env")
    config = dotenv_values(".env")

    engine = create_async_engine(url=config["DB_URL"], echo=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bot = Bot(config["TOKEN"])

    # Setup dispatcher and bind routers to it
    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware(session_pool=sessionmaker))
    dp.update.middleware(LocaleMiddleware(locale_dir="locale"))

    # Register handlers
    dp.include_router(commands.router)
    dp.include_router(create_order.router)
    dp.include_router(process_order.router)

    # Run bot
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
