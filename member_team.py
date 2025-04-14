"""
Module to show team client.

@Author: Denis Maydykovsky
"""

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.kbd import Button
from details import (
    DStart,
    dynamic_dialog_start_data,
    even_hex,
    even_hex_pattern,
    even_hex_parse,
)
from manage_crew import CreateCrew
from models import PersonModel, MemberModel, fields
from international import _, localize_router, N_, NConst, NJinja
from repository import Repository, RepositoryError, make_person, make_person_team, get_person_team
from typing import Any, Dict, Final, Tuple

import datetime

class MemberTeam(StatesGroup):
    summary = State()


_ADD_MEMBER: Final[str] = "addMember"
_REMOVE_MEMBER: Final[str] = "removeMember"
_ADD_MEMBER_CREW: Final[str] = "addMemberCrew"


def _get_member(dialog_manager: DialogManager) -> Tuple[int, PersonModel]:
    return make_person_team(dialog_manager.start_data)


async def _member_team_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    teamId, userPerson = _get_member(dialog_manager)

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
            "crews": teamSummary.crews,
            _ADD_MEMBER: not (teamSummary.team.suspendCompanions and teamSummary.as_member),
            _REMOVE_MEMBER: teamSummary.as_member,
            _ADD_MEMBER_CREW: teamSummary.team.enableCrews or teamSummary.as_admin,

                        
        }
    )
    return data


async def _on_add_member(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:    
    teamId, userPerson = _get_member(manager)
    try:
        # NOTE: Team configuration can be changed until a member is trying to add itself.
        await Repository().addTeamMember(teamId=teamId, crewId=None, member=userPerson)
    except RepositoryError as e:
        callback.answer(_("member_team_add_member_failed{teamId}{userName}").format(
            teamId = even_hex(teamId),
            userName=userPerson.display_user_name(),
        ))



async def _on_remove_member(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager
) -> None:
    teamId, userPerson = _get_member(manager)
    await Repository().removeTeamMember(teamId=teamId, member=userPerson)    
        

member_team_dialog = Dialog(
    Window(
        NJinja(N_("member_team_summary")),
        Button(
            text = NConst(text = N_("member_team_add")),
            id=_ADD_MEMBER,
            on_click=_on_add_member,
            when=F[_ADD_MEMBER],
        ),
        Button(
            text = NConst(text = N_("member_team_remove")),
            id = _REMOVE_MEMBER,
            on_click=_on_remove_member,
            when=F[_REMOVE_MEMBER],
        ),
        DStart(
            text = NConst(text = N_("add_member_crew")),
            id = _ADD_MEMBER_CREW,
            state=CreateCrew.title,
            data=dynamic_dialog_start_data,
            when=F[_ADD_MEMBER_CREW],
        ),
        state=MemberTeam.summary,
        parse_mode="html"
    ),
    getter=_member_team_getter,
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
        person = make_person(message.from_user)
        if await Repository().checkOutcastMember(teamId, person):
            await dialog_manager.start(
                state=MemberTeam.summary,
                data=get_person_team(teamId, person),
                mode=StartMode.RESET_STACK
            )
        else:
            await message.answer(_("msg_member_team_disallow"))


@member_team_router.message(Command("member"))
async def handle_team_list(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    """
    Show list of available teams.
    """

    person = make_person(message.from_user)
    teams = await Repository().queryMemberTeams(member=person)
    
    # Build text
    msg = _("msg_member_list_head")
    for team in teams:
        teamId = even_hex(team.id)
        msg += _("msg_member_list_item{teamId}{title}{description}").format(
            teamId=teamId,
            title=team.title,
            description=team.description,
        )
    await message.answer(msg)




def register_dispatcher(dp: Dispatcher) -> None:
    localize_router(member_team_router)
    dp.include_router(member_team_router)
