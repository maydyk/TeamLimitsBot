
'''
TeamLimitsBot
A Telegram bot to manage number of participants of some event.
@Author: Denis Maydykovsky 

Usage: python3 TeamLimitsBot.py <YOUR BOT TOKEN>
'''
import aiogram
import aiogram_dialog
import aiosqlite
import asyncio
import logging
import sqlalchemy

from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs
from contextlib import asynccontextmanager
from dependency_injector import containers
from dependency_injector.wiring import Provide, inject

# Main application container
from teamlimits.application import Application, bound_resources

# Setup localization
from teamlimits.user.tg_bot.international import localize_router

# Welcome screen
import teamlimits.user.tg_bot.welcome as welcome

# Create (and manage) team wizard
import teamlimits.user.tg_bot.manage_team as manage_team

# Client for members and crews
import teamlimits.user.tg_bot.member_team as member_team

# Create (and manage) crew wizard
import teamlimits.user.tg_bot.manage_crew as manage_crew

import teamlimits.user.tg_bot.make_person as make_person


@inject
async def main(application: Application = Provide[Application]):

    # Setup logging
    logging.basicConfig(level=logging.DEBUG if __debug__ else logging.ERROR)

    # Disable annoying messages from the libraries
    if __debug__:
        logging.getLogger(aiogram.__name__).setLevel(logging.ERROR)
        logging.getLogger(asyncio.__name__).setLevel(logging.ERROR)
        logging.getLogger(aiogram_dialog.__name__).setLevel(logging.ERROR)
        logging.getLogger(aiosqlite.__name__).setLevel(logging.ERROR)
        logging.getLogger(sqlalchemy.__name__).setLevel(logging.ERROR)


    async with bound_resources(application):
        # Main objects
        bot = Bot(token=application.settings.TOKEN())
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        router = Router()

        # Setup localization
        localize_router(dp)
        localize_router(router)
        
        # Append modules
        dp.include_router(router)
        welcome.register_dispatcher(dp)
        manage_team.register_dispatcher(dp)
        member_team.register_dispatcher(dp)
        manage_crew.register_dispatcher(dp)
        setup_dialogs(dp)

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)


def setup_application(application: Application):
    application.wire([
        __name__,
        welcome.__name__,
        manage_crew.__name__,
        manage_team.__name__,
        member_team.__name__,
        ])
                    

if __name__ == "__main__":
    # Setup DI
    application = Application()
    setup_application(application)
    make_person.setup()


    # Main routine
    asyncio.run(main())



    