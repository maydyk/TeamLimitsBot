
'''
TeamLimitsBot
A Telegram bot to manage number of participans of some event.
@Author: Denis Maydykovsky 

Usage: python3 TeamLimitsBot.py <YOUR BOT TOKEN>
'''
import asyncio
import logging

from aiogram import F, Bot, Dispatcher, Router
from aiogram.filters import Command, StateFilter, CommandObject, and_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.handlers import CallbackQueryHandler
from aiogram.types import (
    Message, 
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram_dialog import Data, Dialog, DialogManager, setup_dialogs, StartMode, Window
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.kbd import Calendar
from aiogram_dialog.widgets.kbd import Next, SwitchTo
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.text import Const, Jinja
from datetime import date
from re import Match
from typing import Any, Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)

# Setup localozation
from international import _, N_, NConst, NJinja, localize_router

# Extract token
from gettoken import TOKEN

# Welcome screen
import welcome


# Main objects
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()

class CreateTeam(StatesGroup):
    title = State()
    description = State()
    minimalMembers = State()
    maximalMembers = State()
    deadline = State()
    customCrews = State()
    minimalCrews = State()
    maximalCrews = State()

    preview = State()

FINISHED_KEY = "finished"

CANCEL_EDIT = SwitchTo(
    Const("Отменить редактирование"),
    when=F["dialog_data"][FINISHED_KEY],
    id="cnl_edt",
    state=CreateTeam.preview,
)

async def next_or_end(event, widget, dialog_manager: DialogManager, *_):
    if dialog_manager.dialog_data.get(FINISHED_KEY):
        await dialog_manager.switch_to(CreateTeam.preview)
    else:
        await dialog_manager.next()


async def create_team_getter(dialog_manager: DialogManager, **kwargs):
    dialog_manager.dialog_data[FINISHED_KEY] = True
    return {
        "title": dialog_manager.find("title").get_value(),
        "description": dialog_manager.find("description").get_value(),
        "minimalMembers": dialog_manager.find("minimalMembers").get_value(),
        "maximalMembers": dialog_manager.find("maximalMembers").get_value(),
    }

create_team_dialog = Dialog(
    Window(
        NConst(N_("query_team_title")),
        TextInput(id="title", on_success=next_or_end),
        CANCEL_EDIT,
        state=CreateTeam.title,
    ),
    Window(
        NConst(N_("query_team_description")),
        TextInput(id="description", on_success=next_or_end),
        CANCEL_EDIT,
        state=CreateTeam.description,
    ),
    Window(
        NConst(N_("query_team_minimal_members")),
        TextInput(id="minimalMembers", on_success=next_or_end),
        CANCEL_EDIT,
        state=CreateTeam.minimalMembers,
    ),
    Window(
        NConst(N_("query_team_maximal_members")),
        TextInput(id="maximalMembers", on_success=next_or_end),
        CANCEL_EDIT,
        state=CreateTeam.maximalMembers,
    ),
    Window(
        Jinja(
            "<u>Summary</u>:\n\n"
            "<b>Name></b>: {{title}}\n"
            "<b>Description</b>: {{description}}\n"
            "<b>Minimal members</b>: {{minimalMembers}}\n"
            "<b>Maximal members</b>: {{maximalMembers}}\n"
        ),
        SwitchTo(
            NConst(N_("change_team_title")),
            id="to_name",
            state=CreateTeam.title,
        ),
        SwitchTo(
            NConst(N_("change_team_description")),
            id="to_description",
            state=CreateTeam.description,
        ),
        SwitchTo(
            NConst(N_("change_team_minimal_members")),
            id="to_minimalMembers",
            state=CreateTeam.minimalMembers,
        ),
        SwitchTo(
            NConst(N_("change_team_maximal_members")),
            id="to_maximalMembers",
            state=CreateTeam.maximalMembers,
        ),
        state=CreateTeam.preview,
        getter=create_team_getter,
        parse_mode="html",
    )
)

@router.message(Command("create"))
async def handle_create_team(message: Message, state: FSMContext, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(CreateTeam.title, mode=StartMode.RESET_STACK)

async def main():

    localize_router(dp)
    localize_router(router)
    localize_router(create_team_dialog)
    
    dp.include_router(router)
    dp.include_router(create_team_dialog)

    welcome.register_dispatcher(dp)
    
    setup_dialogs(dp)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


    