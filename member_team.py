"""
Module to show team client.

@Author: Denis Maydykovsky
"""

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.kbd import Button
from details import (
    even_hex,
    even_hex_pattern,
    even_hex_parse,
    dialog_copy_start_data,
    dialog_data_getter
)
from models import MemberModel, fields
from international import _, localize_router, N_, NConst, NJinja
from repository import Repository, make_person
from typing import Any, Dict, Final

import datetime

class MemberTeam(StatesGroup):
    summary = State()


_USER_PERSON: Final[str] = fields(MemberModel).userId
_TEAM_ID: Final[str] = fields(MemberModel).teamId

_ADD_MEMBER: Final[str] = "addMember"
_REMOVE_MEMBER: Final[str] = "removeMember"
_ADD_MEMBER_CREW: Final[str] = "addMemberCrew"

async def member_team_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    teamId = dialog_manager.start_data[_TEAM_ID]
    userPerson = dialog_manager.start_data[_USER_PERSON]

    teamSummary = await Repository().queryTeamSummary(teamId=teamId, member=userPerson)

    data = teamSummary.team.model_dump()
    data.update(
        # Add synthetic members
        {
            "teamId" : even_hex(teamSummary.team.id), 
            "as_admin": teamSummary.as_admin,
            "as_member": teamSummary.as_member,
            "totalMembers": len(teamSummary.members),
            "currentDate": datetime.datetime.now(),
            "deadlineLeft": (teamSummary.team.deadline - datetime.datetime.now()).days() 
                if teamSummary.team.deadline is not None else None,
            "members": teamSummary.members,
            _ADD_MEMBER: not (teamSummary.team.suspendCompanions and teamSummary.as_member)

                        
        }
    )
    return data


async def on_add_member(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
) -> None:    
    teamId = manager.start_data[_TEAM_ID]
    userPerson = manager.start_data[_USER_PERSON]
    await Repository().addTeamMember(teamId=teamId, crewId=None, member=userPerson)
    

async def on_remove_member(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager
) -> None:
    teamId = manager.start_data[_TEAM_ID]
    userPerson = manager.start_data[_USER_PERSON]
    await Repository().removeTeamMember(teamId=teamId, member=userPerson)    
    
member_team_dialog = Dialog(
    Window(
        NJinja(N_("member_team_summary")),
        Button(
            NConst(N_("member_team_add")),
            id=_ADD_MEMBER,
            on_click=on_add_member,
            when=F[_ADD_MEMBER],
        ),
        Button(
            NConst(N_("member_team_remove")),
            id = _REMOVE_MEMBER,
            on_click=on_remove_member,
            when=F["as_member"],
        ),
        Button(
            NConst(N_("add_member_crew")),
            id = _ADD_MEMBER_CREW,
            when=F["enableCrews"],
        ),
        state=MemberTeam.summary,
        parse_mode="html"
    ),
    getter=member_team_getter,
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
        if await Repository().checkOutcastMember(teamId, make_person(message.from_user)):
            await dialog_manager.start(
                state=MemberTeam.summary,
                data={
                    _TEAM_ID: teamId,
                    _USER_PERSON:make_person(message.from_user)
                },
                mode=StartMode.RESET_STACK
            )
        else:
            await message.answer(_("msg_member_team_disallow"))




def register_dispatcher(dp: Dispatcher) -> None:
    localize_router(member_team_router)
    dp.include_router(member_team_router)
