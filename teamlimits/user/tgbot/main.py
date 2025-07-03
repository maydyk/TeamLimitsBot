
'''
TeamLimitsBot
A Telegram bot to manage number of participants of some event.
@Author: Denis Maydykovsky 

Usage: python3 TeamLimitsBot.py <YOUR BOT TOKEN>
'''
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

import aiogram
import aiogram_dialog
import aiosqlite
import asyncio
import logging
import sqlalchemy


# Setup localization
from .international import localize_router

# Extract token and DB connection
from . import config

# Welcome screen
from . import welcome

# Create (and manage) team wizard
from . import manage_team

# Client for members and crews
from . import member_team

# Create (and manage) crew wizard
from . import manage_crew

# Our data
from ...repository.repository import Repository


async def main():

    # Setup logging
    logging.basicConfig(level=logging.DEBUG if __debug__ else logging.ERROR)


    # Disable annoying messages from the libraries
    if __debug__:
        logging.getLogger(aiogram.__name__).setLevel(logging.ERROR)
        logging.getLogger(asyncio.__name__).setLevel(logging.ERROR)
        logging.getLogger(aiogram_dialog.__name__).setLevel(logging.ERROR)
        logging.getLogger(aiosqlite.__name__).setLevel(logging.ERROR)
        logging.getLogger(sqlalchemy.__name__).setLevel(logging.ERROR)


    # Read config
    settings = config.Config()

    # Main objects
    bot = Bot(token=settings.TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    router = Router()

    localize_router(dp)
    localize_router(router)
    dp.include_router(router)

    welcome.register_dispatcher(dp)
    manage_team.register_dispatcher(dp)
    member_team.register_dispatcher(dp)
    manage_crew.register_dispatcher(dp)
    
    setup_dialogs(dp)

    # Close the repository even exception
    async with Repository.build(settings.make_db_url()):
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())



    