"""
Module to show team client.

@Author: Denis Maydykovsky
"""
import re

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ContentType, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import ChatEvent, Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import MessageInput
from typing import Any, Dict, Final, Tuple

from teamlimits.details.even_hex import even_hex, even_hex_pattern, even_hex_parse
from teamlimits.models.base import CrewModel, OutcastModel, MemberModel
from teamlimits.models.fields import fields
from teamlimits.repository.models_view import TeamView
from teamlimits.repository.repository import Repository, RepositoryError

from teamlimits.user.tg_bot.details import (
    DStart,
    filter_command,
    parse_command,
)
from teamlimits.user.tg_bot.international import _, localize_router, N_, NConst, NJinja
from teamlimits.user.tg_bot.make_person import make_person, get_member, set_person_team
from teamlimits.user.tg_bot.manage_crew import CreateCrew


class MemberTeam(StatesGroup):
    summary = State()


_ADD_MEMBER: Final[str] = fields(TeamView).canAddMember
_REMOVE_MEMBER: Final[str] = fields(TeamView).canRemoveMember
_ADD_MEMBER_CREW: Final[str] = fields(TeamView).canAddMemberCrew
_HAS_DEADLINE: Final[str] = fields(TeamView).deadline
_HAS_ACTIVE_CREWS: Final[str] = fields(TeamView).hasActiveCrews
_HAS_QUEUED_CREWS: Final[str] = fields(TeamView).hasQueuedCrews
_HAS_ACTIVE_MEMBERS: Final[str] = fields(TeamView).hasActiveMembers
_HAS_QUEUED_MEMBERS: Final[str] = fields(TeamView).hasQueuedMembers
_HAS_DEFAULT_CREW: Final[str] = fields(TeamView).hasDefaultCrew


def _get_member(dialog_manager: DialogManager) -> MemberModel:
    return get_member(dialog_manager.start_data)


async def _member_team_getter(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    member = _get_member(dialog_manager)

    teamSummary = await Repository().queryTeamView(member)

    data = teamSummary.model_dump()
    return data


async def _on_add_member(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:    
    member = _get_member(manager)
    try:
        # NOTE: Team configuration can be changed until a member is trying to add itself.
        await Repository().addTeamMember(member=member, crewId=None)
    except RepositoryError as e:
        callback.answer(_("member_team_add_member_failed{teamIdStr}{userName}").format(
            teamIdStr = even_hex(member.teamId),
            userName=member.display_user_name(),
        ))


async def _on_remove_member(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager
) -> None:
    member = _get_member(manager)
    await Repository().removeTeamMember(member)    


async def _create_crew_start_data(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    member = _get_member(dialog_manager)
    return {
        fields(CrewModel).teamId : member.teamId
    }


_manage_crew_pattern: Final[re.Pattern] = even_hex_pattern("mc")
_take_crew_pattern: Final[re.Pattern] = even_hex_pattern("c")      


async def _handle_commands(message: Message, source: MessageInput, manager: DialogManager) -> None:

    member = _get_member(manager)

    cmd: Final[str] = await parse_command(message, _manage_crew_pattern, _take_crew_pattern)
    
    if manage_crew := even_hex_parse(_manage_crew_pattern, cmd):
        crew = await Repository().queryLeaderCrew(manage_crew, make_person(message.from_user))
        if crew:
            await manager.start(
                CreateCrew.summary,
                data = crew.model_dump()
            )
        else:
            message.answer(_("msg_crew_not  _found{crewIdStr}").format(
                crewIdStr = even_hex(manage_crew),
            ))
        return

    if take_crew := even_hex_parse(_take_crew_pattern, cmd):
        await Repository().setCrewMate(mate=member, crewId = take_crew)
        return


async def _filter_commands(event: ChatEvent, **kwargs) -> bool:
    if isinstance(event, Message):
        return await filter_command(event, _manage_crew_pattern, _take_crew_pattern)
    else:
        return False


member_team_dialog = Dialog(
    Window(
        NJinja(N_("member_team_summary_header")),
        NJinja(N_("member_team_summary_total")),
        NJinja(N_("member_team_summary_deadline"), when=F[_HAS_DEADLINE]),
        NJinja(N_("member_team_summary_active_crews"), when=F[_HAS_ACTIVE_CREWS]),
        NJinja(N_("member_team_summary_queued_crews"), when=F[_HAS_QUEUED_CREWS]),
        NJinja(N_("member_team_summary_active_members"), when=F[_HAS_ACTIVE_MEMBERS]),
        NJinja(N_("member_team_summary_queued_members"), when=F[_HAS_QUEUED_MEMBERS]),
        NJinja(N_("member_team_summary_default_crew"), when=F[_HAS_DEFAULT_CREW]),
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
        if await Repository().canViewTeam(person.combineId(MemberModel, teamId)):
            await dialog_manager.start(
                state=MemberTeam.summary,
                data=set_person_team(teamId, person),
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
    headers = await Repository().queryMemberTeamHeaders(person)
    
    # Build text
    msg = _("msg_member_list_head")
    for header in headers:
        msg += _("msg_member_list_item{teamIdStr}{title}{description}").format(
            teamIdStr=header.teamIdStr(),
            title=header.title,
            description=header.description,
        )
    await message.answer(msg)


def register_dispatcher(dp: Dispatcher) -> None:
    localize_router(member_team_router)
    dp.include_router(member_team_router)
