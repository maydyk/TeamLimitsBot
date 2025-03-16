
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
from gettoken import TOKEN

# Welcome screen
import welcome

# Create team wizard
import create_team


async def main():

    # Main objects
    bot = Bot(token=TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    router = Router()

    localize_router(dp)
    localize_router(router)
    dp.include_router(router)

    welcome.register_dispatcher(dp)
    create_team.register_dispatcher(dp)
    
    setup_dialogs(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


    