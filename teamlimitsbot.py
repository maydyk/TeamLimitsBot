
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
from aiogram_dialog.widgets.kbd import Button, Calendar, Next, Row, SwitchTo, Row
from aiogram_dialog.widgets.input import TextInput, ManagedTextInput
from aiogram_dialog.widgets.text import Jinja
from datetime import date
from re import Match
from typing import Any, Dict, Optional

from details import or_empty, write_dialog_value

# Setup logging
logging.basicConfig(level=logging.INFO)

# Setup localozation
from international import _, N_, NConst, NFormat, NJinja, localize_router

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
    minimalCrews = State()
    maximalCrews = State()
    options = State()
    deadline = State() # calendar

    summary = State()

FINISHED_KEY = "finished"


async def create_team_getter(dialog_manager: DialogManager, **kwargs):
    return dialog_manager.dialog_data
    # minmbr = dialog_manager.find("minimalMembers").get_value()
    # print("Minimal members:", minmbr)
    # return {
    #     "title": dialog_manager.find("title").get_value(),
    #     "description": dialog_manager.find("description").get_value(),
    #     "minimalMembers": dialog_manager.find("minimalMembers").get_value(),
    #     "maximalMembers": dialog_manager.find("maximalMembers").get_value(),
    # }


def zeropositive(text: str) -> int:
    value = int(text)
    if value < 0:
        raise ValueError(f"Negative number {text}")
    return value


async def minimal_members_error(
        message: Message,
        dialog_: Any,
        manager: DialogManager,
        error_: ValueError
):
    await message.answer(_("team_minimal_members_error{value}").format(
        value = message.text
    ))


async def maximal_members_success(
        message: Message,
        dialog_: Any,
        manager: DialogManager,
        data: Any) -> None:
    minimalMembers = manager.dialog_data["minimalMembers"]
    maximalMembers = manager.find("maximalMembers").get_value()

    if minimalMembers:
        if minimalMembers <= maximalMembers:
            manager.dialog_data["maximalMembers"] = maximalMembers
            await manager.next()
        else:
            await message.answer(
                _("team_maximal_members_invalid{minimalMembers}{maximalMembers}")
                .format(
                    minimalMembers=minimalMembers,
                    maximalMembers=maximalMembers
                ))
    else:
        manager.dialog_data["maximalMembers"] = maximalMembers
        await manager.next()

    
async def maximal_members_error(
        message: Message,
        dialog_: Any,
        manager: DialogManager,
        error_: ValueError
):
    await message.answer(_("team_maximal_members_error{value}").format(
        value = message.text
    ))

async def set_max_to_min(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager) -> None:
    minimalMembers = manager.dialog_data["minimalMembers"]
    manager.dialog_data["maximalMembers"] = minimalMembers
       

create_team_dialog = Dialog(
    Window(
        NConst(N_("query_team_title")),
        TextInput(id="title", on_success=Next(on_click=write_dialog_value("title"))),
        state=CreateTeam.title,
    ),
    Window(
        NConst(N_("query_team_description")),
        TextInput(id="description", on_success=Next(on_click=write_dialog_value("description"))),
        Next(NConst(N_("skip_team_description")), on_click=write_dialog_value("description")),
        state=CreateTeam.description,
    ),
    Window(
        NConst(N_("query_team_minimal_members")),
        TextInput(
            id="minimalMembers",
            type_factory=zeropositive,
            on_success=Next(on_click=write_dialog_value("minimalMembers")),
            on_error=minimal_members_error),
        Next(NConst(N_("skip_team_minimal_members")), on_click=write_dialog_value("minimalMembers")),
        state=CreateTeam.minimalMembers,
    ),
    Window(
        NFormat(N_("query_team_maximal_members{minimalMembers}")),
        TextInput(
            id="maximalMembers",
            type_factory=zeropositive,
            on_success=maximal_members_success,
            on_error=maximal_members_error,
        ),
        Row(
            Next(
                NFormat(N_("set_team_max_as_min{minimalMembers}")),
                id="set_team_max_as_min",
                on_click=set_max_to_min,
                when=F["minimalMembers"],
            ),
            Next(
                NConst(N_("skip_team_maximal_members")),
                id="skip_team_maximal_members",
                on_click=write_dialog_value("maximalMembers"),
            ),
        ),
        state=CreateTeam.maximalMembers,
        getter=create_team_getter,
    ),
    Window(
        Jinja(
            "<u>Summary</u>:\n\n"
            "<b>Name</b>: {{title}}\n"
            "<b>Description</b>: {{description}}\n"
            "<b>Minimal members</b>: {{minimalMembers}}\n"
            "<b>Maximal members</b>: {{maximalMembers}}\n"
        ),
        state=CreateTeam.summary,
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


    