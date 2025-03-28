"""
Module to show team client.

@Author: Denis Maydykovsky
"""

from aiogram import Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.kbd import Button

from details import (
    even_hex,
    even_hex_pattern,
    even_hex_parse,
    dialog_copy_start_data,
)
from models import MemberModel, fields
from international import localize_router, N_, NConst, NJinja
from repository import Repository, make_person
from typing import Final

class MemberTeam(StatesGroup):
    summary = State()


_USER_ID: Final[str] = fields(MemberModel).userId
_TEAM_ID: Final[str] = fields(MemberModel).teamId

_ADD_MEMBER: Final[str] = "addMember"

async def member_team_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    teamId = dialog_manager.start_data[_TEAM_ID]

    data = await Repository().queryTeamSummary(teamId)

    pass

member_team_dialog = Dialog(
    Window(
        NJinja(N_("member_team_summary")),
        Button(
            NConst(N_("member_team_add")),
            id=_ADD_MEMBER,
        ),
        state=MemberTeam.summary,
    ),
    # on_start=dialog_copy_start_data,
)

member_team_router = Router()
member_team_router.include_router(member_team_dialog)

member_pattern = even_hex_pattern("t")

@member_team_router.message(Command(member_pattern))
async def handle_member_team(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    """
    Start to participate in specified tem
    """
    teamId = even_hex_parse(member_pattern, message.text.lstrip('/'))
    if teamId is not None:
        if await Repository().allowPersonTeam(teamId, make_person(message.from_user)):
            dialog_manager.start(
                state=MemberTeam.summary,
                data={_TEAM_ID: teamId},
                mode=StartMode.RESET_STACK
            )
    else:
        print(f"Team is not ex")





def register_dispatcher(dp: Dispatcher) -> None:
    localize_router(member_team_router)
    dp.include_router(member_team_router)
