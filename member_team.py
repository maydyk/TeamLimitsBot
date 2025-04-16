"""
Module to show team client.

@Author: Denis Maydykovsky
"""

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import ChatEvent, Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import MessageInput
from details import (
    DStart,
    filter_command,
    even_hex,
    even_hex_pattern,
    even_hex_parse,
    parse_command,
)
from manage_crew import CreateCrew
from models import *
from international import _, localize_router, N_, NConst, NJinja
from repository import Repository, RepositoryError, make_person, make_person_team, get_person_team
from typing import Any, Dict, Final, Tuple

import re

class MemberTeam(StatesGroup):
    summary = State()


_ADD_MEMBER: Final[str] = fields(TeamSummary).canAddMember
_REMOVE_MEMBER: Final[str] = fields(TeamSummary).canRemoveMember
_ADD_MEMBER_CREW: Final[str] = fields(TeamSummary).canAddMemberCrew


def _get_member(dialog_manager: DialogManager) -> Tuple[int, PersonModel]:
    return make_person_team(dialog_manager.start_data)


async def _member_team_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    teamId, userPerson = _get_member(dialog_manager)

    teamSummary = await Repository().queryTeamSummary(teamId=teamId, member=userPerson)

    data = teamSummary.model_dump()
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
        callback.answer(_("member_team_add_member_failed{teamIdStr}{userName}").format(
            teamIdStr = even_hex(teamId),
            userName=userPerson.display_user_name(),
        ))


async def _on_remove_member(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager
) -> None:
    teamId, userPerson = _get_member(manager)
    await Repository().removeTeamMember(teamId=teamId, member=userPerson)    


async def _create_crew_start_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    teamId, *_ = _get_member(dialog_manager)
    return {
        fields(CrewModel).teamId : teamId
    }


_manage_crew_pattern: Final[re.Pattern] = even_hex_pattern("mc")
_take_crew_pattern: Final[re.Pattern] = even_hex_pattern("c")      


async def _handle_commands(message: Message, source: MessageInput, manager: DialogManager) -> None:

    teamId, userPerson = _get_member(manager)

    cmd: Final[str] = await parse_command(message, _manage_crew_pattern, _take_crew_pattern)
    
    if manage_crew := even_hex_parse(_manage_crew_pattern, cmd):
        crew = await Repository().queryLeaderCrew(manage_crew, make_person(message.from_user))
        if crew:
            await manager.start(
                CreateCrew.summary,
                data = crew.model_dump()
            )
        else:
            message.answer(_("msg_crew_not_found{crewIdStr}").format(
                crewIdStr = even_hex(manage_crew),
            ))
        return

    if take_crew := even_hex_parse(_take_crew_pattern, cmd):
        await Repository().setCrewMate(teamId = teamId, crewId = take_crew, mate = userPerson)
        return


async def _filter_commands(event: ChatEvent, **kwargs) -> bool:
    if isinstance(event, Message):
        return await filter_command(event, _manage_crew_pattern, _take_crew_pattern)
    else:
        return False


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
            data=_create_crew_start_data,
            when=F[_ADD_MEMBER_CREW],
        ),
        MessageInput(
            func=_handle_commands,
            content_types=ContentType.TEXT,
            filter=_filter_commands,
        ),
        state=MemberTeam.summary,
        parse_mode="html"
    ),
    getter=_member_team_getter,
)


member_team_router = Router()
member_team_router.include_router(member_team_dialog)

_member_pattern: Final[re.Pattern] = even_hex_pattern("t")

@member_team_router.message(Command(_member_pattern))
async def handle_member_team(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    """
    Start to participate in specified tem
    """
    teamId = even_hex_parse(_member_pattern, message.text.lstrip('/'))
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
        teamIdStr = even_hex(team.id)
        msg += _("msg_member_list_item{teamIdStr}{title}{description}").format(
            teamIdStr=teamIdStr,
            title=team.title,
            description=team.description,
        )
    await message.answer(msg)


def register_dispatcher(dp: Dispatcher) -> None:
    localize_router(member_team_router)
    dp.include_router(member_team_router)
