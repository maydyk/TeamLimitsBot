
'''
TeamLimitsBot
A Telegram bot to manage number of participants of some event.
@Author: Denis Maydykovsky 

Usage: python3 TeamLimitsBot.py <YOUR BOT TOKEN>
'''
import asyncio
import logging

from aiogram import F, Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

# Setup logging
logging.basicConfig(level=logging.INFO)

# Setup localization
from international import _, localize_router

# Extract token
from config import config

# Welcome screen
import welcome

# Create (and manage) team wizard
import manage_team

# Client for members and crews
import member_team

# Our data
from repository import Repository


async def main():

    # Main objects
    bot = Bot(token=config.TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    router = Router()

    localize_router(dp)
    localize_router(router)
    dp.include_router(router)

    welcome.register_dispatcher(dp)
    manage_team.register_dispatcher(dp)
    member_team.register_dispatcher(dp)
    
    setup_dialogs(dp)

    # Close the repository even exception
    async with Repository.build(config.make_db_url()):
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
        

if __name__ == "__main__":
    asyncio.run(main())



    