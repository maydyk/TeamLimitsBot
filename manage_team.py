"""
module _manage_team

Contains a dialog wizard to create or manage a new team.

@Author: Denis Maydykovsky
"""

from aiogram import F, Dispatcher, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    CallbackQuery,
)

from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.api.entities import Data
from aiogram_dialog.widgets.input import TextInput, ManagedTextInput
from aiogram_dialog.widgets.kbd import (
    Button,
    Calendar,
    Cancel,
    Checkbox,
    Next,
    Row,
    SwitchTo,
)

from confirmation_dialog import make_confirmation_dialog
from details import (
    DStart,
    dynamic_dialog_data_items,
    even_hex,
    even_hex_pattern,
    even_hex_parse,
    dialog_data_getter,
    dialog_copy_start_data,
    dialog_filter_cancel,
    initialize_checkboxes,
    write_dialog_data,
    write_calendar_date,
    write_checkbox_state,
    write_dialog_value,
    zero_positive,
)

from wizard import wizard_control, wizard_preview, Preview

# Setup localization
from international import _, localize_router, N_, NConst, NFormat, NJinja
from typing import Any, Dict, Final

from repository import Repository, make_person
from models import TeamModel
from model_fields import fields


class CreateTeam(StatesGroup):
    title = State()
    description = State()
    minimalMembers = State()
    maximalMembers = State()
    enableCrews = State()
    minimalCrews = State()
    maximalCrews = State()
    deadline = State()
    options = State()

    summary = State()


# Constants widget IDs
_ID: Final[str] = fields(TeamModel).id
_TEAM_ID_STR: Final[str] = "teamIdStr" # A sting representation of _ID
_TITLE: Final[str] = fields(TeamModel).title
_ASK_DESCRIPTION: Final[str] = "askDescription"
_DESCRIPTION: Final[str] = fields(TeamModel).description
_RESET_DESCRIPTION: Final[str] = "resetDescription"
_MINIMAL_MEMBERS: Final[str] = fields(TeamModel).minimalMembers
_RESET_MINIMAL_MEMBERS: Final[str] = "resetMinimalMembers"
_MAXIMAL_MEMBERS: Final[str] = fields(TeamModel).maximalMembers
_FIXED_MAXIMAL_MEMBERS: Final[str] = "fixedMaximalMembers"
_RESET_MAXIMAL_MEMBERS: Final[str] = "resetMaximalMembers"
_ENABLE_CREWS: Final[str] = fields(TeamModel).enableCrews
_SETUP_CREWS_LIMIT: Final[str] = "setupCrewsLimit"
_RESET_CREWS_LIMIT: Final[str] = "resetCrewsLimit"
_MINIMAL_CREWS: Final[str] = fields(TeamModel).minimalCrews
_RESET_MINIMAL_CREWS: Final[str] = "resetMinimalCrews"
_MAXIMAL_CREWS: Final[str] = fields(TeamModel).maximalCrews
_FIXED_MAXIMAL_CREWS: Final[str] = "fixMaximalCrews"
_RESET_MAXIMAL_CREWS: Final[str] = "skipMaximalCrews"
_ENABLE_DEADLINE: Final[str] = "enableDeadline"
_DEADLINE: Final[str] = fields(TeamModel).deadline
_DEADLINE_NEXT: Final[str] = "deadline_next"
_SUSPEND_COMPANIONS: Final[str] = fields(TeamModel).suspendCompanions
_SUSPEND_RECRUITMENT: Final[str] = fields(TeamModel).suspendRecruitment
_SUSPEND_PENDING_QUEUE: Final[str] = fields(TeamModel).suspendPendingQueue
_SUSPEND_DEADLINE_QUEUE: Final[str] = fields(TeamModel).suspendDeadlineQueue
_OPTIONS_NEXT: Final[str] = "optionsNext"
_MANAGE_TEAM: Final[str] = "manageTeam"
_CANCEL_TEAM: Final[str] = "cancelTeam"
_DELETE_TEAM: Final[str] = "deleteTeam"
_INSERT_TEAM: Final[str] = "insertTeam"
_UPDATE_TEAM: Final[str] = "updateTeam"


class ConfirmDeleteTeam(StatesGroup):
    confirm = State()

_delete_team_confirmation = make_confirmation_dialog(
    text = N_("delete_team_confirmation{teamIdStr}{title}"),
    no = N_("delete_team_confirmation_no"),
    yes= N_("delete_team_confirmation_yes"),
    result=_DELETE_TEAM,
    state=ConfirmDeleteTeam.confirm
)


async def _on_query_title(
        callback: CallbackQuery,
        source: ManagedTextInput,
        manager: DialogManager,
        data: Any,
    ) -> None:
    """
    Team title success handler:
        switch to the next (description) if checkbox was checked
        or switch directly to maximumMembers
    """
    
    if await Repository().checkTeamTitleIsUnique(data):
        manager.dialog_data[_TITLE] = data

        if manager.dialog_data.get(_ASK_DESCRIPTION):
            await manager.next()
        else:
            await manager.switch_to(CreateTeam.minimalMembers)
    else:
        await callback.answer(_("create_team_duplicated_title{title}").format(
            title=data
        ))


async def _start_create_team(start_data: Dict|None, dialog_manager: DialogManager) -> None:
    # Get data from start
    await dialog_copy_start_data(start_data, dialog_manager)

    # Setup intermediate values
    if start_data:
        dialog_manager.dialog_data[_ASK_DESCRIPTION] = bool(start_data.get(_DESCRIPTION))
        dialog_manager.dialog_data[_ENABLE_DEADLINE] = bool(start_data.get(_DEADLINE))

    # Initialize checkboxes state
    await initialize_checkboxes(
        dialog_manager,
        _ASK_DESCRIPTION,
        _ENABLE_CREWS,
        _ENABLE_DEADLINE,
        _SUSPEND_COMPANIONS,
        _SUSPEND_RECRUITMENT,
        _SUSPEND_PENDING_QUEUE,
        _SUSPEND_DEADLINE_QUEUE,
        )

    
async def _minimal_members_error(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        error: ValueError
    ) -> None:
    await message.answer(_("create_team_minimal_members_error{value}").format(
        value = message.text
    ))


async def _maximal_members_success(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        data: Any
    ) -> None:
    minimalMembers = manager.dialog_data.get(_MINIMAL_MEMBERS) or 0
    maximalMembers = data
    
    if minimalMembers <= maximalMembers:
        manager.dialog_data[_MAXIMAL_MEMBERS] = maximalMembers
        await manager.next()
    else:
        await message.answer(
            _("create_team_maximal_members_invalid{minimalMembers}{maximalMembers}")
            .format(
                minimalMembers=minimalMembers,
                maximalMembers=maximalMembers,
            ))

async def _maximal_members_error(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        error_: ValueError
    ) -> None:
    await message.answer(_("create_team_maximal_members_error{value}").format(
        value = message.text
    ))


async def _fixed_maximal_members(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager
    ) -> None:
    minimalMembers = manager.dialog_data.get(_MINIMAL_MEMBERS)
    manager.dialog_data[_MAXIMAL_MEMBERS] = minimalMembers
       

async def reset_crews_limit(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    manager.dialog_data[_MINIMAL_CREWS] = 0
    manager.dialog_data[_MAXIMAL_CREWS] = 0
    

async def minimal_crews_error(
    message: Message,
    source: ManagedTextInput,
    manager: DialogManager,
    error_: ValueError
    ) -> None:
    await message.answer(_("create_team_minimal_crews_error{value}").format(
        value = message.text
    ))


async def maximal_crews_success(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        data: Any) -> None:
    minimalCrews = manager.dialog_data.get(_MINIMAL_CREWS) or 0
    maximalCrews = data

    if minimalCrews <= maximalCrews:
        manager.dialog_data[_MAXIMAL_CREWS] = maximalCrews
        await manager.next()
    else:
        await message.answer(
            _("create_team_maximal_crews_invalid{minimalCrews}{maximalCrews}").format(
                minimalCrews=minimalCrews,
                maximalCrews=maximalCrews,
            )
        )

async def maximal_crews_error(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        error: ValueError,
        ) -> None:
    await message.answer(_("create_team_maximal_crews_error{value}").format(
        value = message.text
    ))    


async def fixed_maximal_crews(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    minimalCrews = manager.dialog_data.get(_MINIMAL_CREWS)
    manager.dialog_data[_MAXIMAL_CREWS] = minimalCrews


async def _manage_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    manager.dialog_data[_MANAGE_TEAM] = True


async def _cancel_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    
    # Define farewell
    text = None
    data = manager.dialog_data
    if _ID in data:
        text = _("manage_team_was_cancelled{title}")
    else:
        text = _("create_team_was_cancelled{title}")
    
    # Put message and delete dialog
    await callback.message.answer(text.format(
        title=data[_TITLE]
    ))
    await callback.message.delete()


async def _insert_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    
    team_values = manager.dialog_data
    assert(not _ID in team_values)

    try:
        person = make_person(callback.from_user)
        team = TeamModel(**team_values)
        teamId = await Repository().insertTeam(person=person, team=team)

        await manager.done()
        await callback.answer(_("create_team_inserted{teamIdStr}{title}").format(
            teamIdStr=even_hex(teamId),
            title=team.title,
            )
        )
        
    except Exception as e:
        print(e)
        breakpoint()
        await callback.answer(
            _("create_team_insert_failed{title}")
            .format(
                title=team_values.get(_TITLE, ""),
            )
        )
        pass


async def _update_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:

    team_values = manager.dialog_data.copy()
    assert(_ID in team_values)

    try:
        team = TeamModel(**team_values)
        teamId = await Repository().updateTeam(team=team)

        await manager.done()
        await callback.message.answer(_("create_team_updated{teamIdStr}{title}").format(
            teamIdStr=even_hex(teamId),
            title=team_values[_TITLE],
            )
        )
    except Exception as e:
        print(e)
        breakpoint()
        await callback.message.answer(_("create_team_update_failed{title}").format(
            title=team_values.get(_TITLE, ""),
            )
        )
        pass


async def _team_summary_result(data: Data, result: Any, dialog_manager: DialogManager) -> None:
    print("_team_summary_result", data, result)
    if result == _DELETE_TEAM:
        teamId = data[_ID]
        print(f"Delete the team {even_hex(teamId)}")
        try:
            await Repository().deleteTeam(teamId)

            # Remove ID from dictionary
            # Now we are being in state as a new team was created
            dialog_manager.dialog_data.pop(_ID, "")
            dialog_manager.dialog_data.pop(_TEAM_ID_STR, "")
        except:
            breakpoint()
            # TODO: How to show a message here?
            pass
    pass


# Row with manage controls
_manage_team_wizard = wizard_control(
    homeState=CreateTeam.summary,
    showWizard=_MANAGE_TEAM,
    back=N_("create_team_back"),
    home=N_("create_team_home"),
    next=N_("create_team_next"),
)

def _preview(key: str) -> Preview:
    return wizard_preview(
        text = N_("create_team_preview{preview}"),
        showPreview=_MANAGE_TEAM,
        key_source=key,
    )


# Main team dialog wizard
_create_team_dialog = Dialog(
    # Query for team name and provide [v] checkbox to include description.
    Window(
        NConst(text=N_("create_team_query_title")),
        _preview(key=_TITLE),
        Checkbox(
            checked_text=NConst(N_("create_team_ask_description_checked")),
            unchecked_text=NConst(N_("create_team_ask_description_unchecked")),
            id=_ASK_DESCRIPTION,
            on_state_changed=write_checkbox_state,
        ),
        _manage_team_wizard,
        TextInput(
            id=_TITLE,
            on_success=_on_query_title,
            filter=dialog_filter_cancel,
        ),
        state=CreateTeam.title,
        getter=dialog_data_getter,
    ),
    
    # Query team description with [reset] button.
    Window(
        NConst(text=N_("create_team_query_description")),
        _preview(key=_DESCRIPTION),
        TextInput(
            id=_DESCRIPTION,
            on_success=Next(on_click=write_dialog_value(_DESCRIPTION)),
            filter=dialog_filter_cancel,
        ),
        Next(
            text=NConst(text=N_("create_team_reset_description")),
            id=_RESET_DESCRIPTION,
            on_click=write_dialog_data(_DESCRIPTION, ""),
        ),
        _manage_team_wizard,
        state=CreateTeam.description,
        getter=dialog_data_getter,
    ),
    
    # Query for team minimal members with [reset] button.
    # Zero or skip for minimalMembers
    Window(
        NConst(text=N_("create_team_query_minimal_members")),
        _preview(key=_MINIMAL_MEMBERS),
        Next(
            text=NConst(text=N_("create_team_reset_minimal_members")),
            id=_RESET_MINIMAL_MEMBERS,
            on_click=write_dialog_data(_MINIMAL_MEMBERS, 0),
        ),
        _manage_team_wizard,
        TextInput(
            id=_MINIMAL_MEMBERS,
            type_factory=zero_positive,
            on_success=Next(on_click=write_dialog_value(_MINIMAL_MEMBERS)),
            on_error=_minimal_members_error,
            filter=dialog_filter_cancel,
        ),
        state=CreateTeam.minimalMembers,
        getter=dialog_data_getter,
    ),

    # Query for team maximalMembers.
    # maximalMembers can be great or equal than minimalMembers
    Window(
        NFormat(text=N_("create_team_query_maximal_members{minimalMembers}")),
        _preview(key=_MAXIMAL_MEMBERS),
        Row(
            Next(
                text=NFormat(text=N_("create_team_fix_maximal_members{minimalMembers}")),
                id=_FIXED_MAXIMAL_MEMBERS,
                on_click=_fixed_maximal_members,
                when=F[_MINIMAL_MEMBERS]
            ),
            Next(
                text=NConst(text=N_("create_team_skip_maximal_members")),
                id=_RESET_MAXIMAL_MEMBERS,
                on_click=write_dialog_data(_MAXIMAL_MEMBERS, 0),
                )
            ),
        _manage_team_wizard,
        TextInput(
            id=_MAXIMAL_MEMBERS,
            type_factory=zero_positive,
            on_success=_maximal_members_success,
            on_error=_maximal_members_error,
            filter=dialog_filter_cancel,
        ),
        state=CreateTeam.maximalMembers,
        getter=dialog_data_getter,
    ),

    # Buttons and message to setup crews
    Window(
        NConst(text=N_("create_team_crews_welcome")),
        Checkbox(
            checked_text=NConst(text=N_("create_team_enable_crews")),
            unchecked_text=NConst(text=N_("create_team_disable_crews")),
            id=_ENABLE_CREWS,
            on_state_changed=write_checkbox_state,
        ),
        Next(
            text=NConst(text=N_("create_team_setup_crews_limits")),
            id=_SETUP_CREWS_LIMIT,
            when=F[_ENABLE_CREWS],
        ),
        SwitchTo(
            text=NConst(text=N_("create_team_reset_crews_limits")),
            id=_RESET_CREWS_LIMIT,
            state=CreateTeam.deadline,
            on_click=reset_crews_limit
        ),
        _manage_team_wizard,
        state=CreateTeam.enableCrews,
        getter=dialog_data_getter,
    ),

    # Query for minimal crews
    Window(
        NConst(text=N_("create_team_query_minimal_crews")),
        _preview(key=_MINIMAL_CREWS),
        TextInput(
            id=_MINIMAL_CREWS,
            type_factory=zero_positive,
            on_success=Next(on_click=write_dialog_value(_MINIMAL_CREWS)),
            on_error=minimal_crews_error,
            filter=dialog_filter_cancel,
        ),
        Next(
            text=NConst(N_("create_team_reset_minimal_crews")),
            id=_RESET_MINIMAL_CREWS,
            on_click=write_dialog_data(_MINIMAL_CREWS, 0),
        ),
        _manage_team_wizard,
        state=CreateTeam.maximalCrews,
        getter=dialog_data_getter,
    ),

    # Query for maximal crews
    Window(
        NConst(N_("create_team_query_maximal_crews{minimalCrews}")),
        _preview(key=_MAXIMAL_CREWS),
        TextInput(
            id=_MAXIMAL_CREWS,
            type_factory=zero_positive,
            on_success=maximal_crews_success,
            on_error=maximal_crews_error,
            filter=dialog_filter_cancel
        ),
        Row(
            Next(
                text=NFormat(N_("create_team_fixed_maximal_crews{minimalCrews}")),
                id=_FIXED_MAXIMAL_CREWS,
                on_click=fixed_maximal_crews,
                when=F[_MINIMAL_CREWS],
            ),
            Next(
                text=NConst(N_("create_team_reset_maximal_crews")),
                id=_RESET_MAXIMAL_CREWS,
                on_click=write_dialog_value(_MAXIMAL_CREWS, lambda x: x or 0),
            )
        ),
        _manage_team_wizard,
        state=CreateTeam.minimalCrews,
        getter=dialog_data_getter,
    ),

    # Deadline
    Window(
        NConst(text=N_("create_team_deadline_welcome")),
        _preview(key=_DEADLINE),
        Calendar(
            id=_DEADLINE,
            on_click=write_calendar_date(True),
            when=F[_ENABLE_DEADLINE],
        ),
        Checkbox(
            checked_text=NConst(N_("create_team_enable_deadline_checked")),
            unchecked_text=NConst(N_("create_team_enable_deadline_unchecked")),
            id=_ENABLE_DEADLINE,
            on_state_changed=write_checkbox_state,
        ),
        Next(
            text=NConst(N_("create_team_deadline_next")),
            id=_DEADLINE_NEXT,
            when=~F[_ENABLE_DEADLINE],
            ),
        _manage_team_wizard,
        state=CreateTeam.deadline,
        getter=dialog_data_getter,
    ),

    # Advanced options
    Window(
        NJinja(text=N_("create_team_options_welcome{deadline}")),
        Checkbox(
            checked_text=NConst(N_("create_team_suspend_companions_checked")),
            unchecked_text=NConst(N_("create_team_suspend_companions_unchecked")),
            id=_SUSPEND_COMPANIONS,
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            checked_text=NConst(N_("create_team_suspend_recruitment_checked")),
            unchecked_text=NConst(N_("create_team_suspend_recruitment_unchecked")),
            id=_SUSPEND_RECRUITMENT,
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            checked_text=NConst(N_("create_team_suspend_pending_queue_checked")),
            unchecked_text=NConst(N_("create_team_suspend_pending_queue_unchecked")),
            id=_SUSPEND_PENDING_QUEUE,
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            checked_text=NConst(N_("create_team_suspend_deadline_queue_checked")),
            unchecked_text=NConst(N_("create_team_suspend_deadline_queue_unchecked")),
            id=_SUSPEND_DEADLINE_QUEUE,
            on_state_changed=write_checkbox_state,
            when=F[_ENABLE_DEADLINE],
        ),
        Next(text = NConst(N_("create_team_options_next")), id=_OPTIONS_NEXT),
        _manage_team_wizard,
        state=CreateTeam.options,
        getter=dialog_data_getter,
        parse_mode="html",
    ),

    # TODO: Add administrators and banned people.

    # Summary
    Window(
        NJinja(text = N_("create_team_summary")),
        Row(
            _manage_team_wizard,
            Button(
                text = NConst(N_("create_team_manage")),
                id=_MANAGE_TEAM,
                on_click=_manage_team,
                when=~F[_MANAGE_TEAM],
            ),
            DStart(
                text = NConst(N_("create_team_delete")),
                id=_DELETE_TEAM,
                state=ConfirmDeleteTeam.confirm,
                data=dynamic_dialog_data_items(_ID,_TEAM_ID_STR,_TITLE,_DESCRIPTION),
                when=F[_ID],
            ),
            Button(
                text = NConst(N_("create_team_insert")),
                id=_INSERT_TEAM,
                on_click=_insert_team,
                when=~F[_ID],
            ),
            Button(
                text = NConst(N_("create_team_update")),
                id=_UPDATE_TEAM,
                on_click=_update_team,
                when=F[_ID],
            ),
            Cancel(
                text = NConst(N_("create_team_cancel")),
                id=_CANCEL_TEAM,
                on_click=_cancel_team,
            ),
        ),
        state=CreateTeam.summary,
        getter=dialog_data_getter,
        on_process_result=_team_summary_result,
        parse_mode="html",
    ),
    on_start=_start_create_team,
)

create_team_router = Router()
create_team_router.include_router(_create_team_dialog)
create_team_router.include_router(_delete_team_confirmation)


@create_team_router.message(Command("cancel"))
async def handle_cancel(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    """
    Close current dialog
    """
    await dialog_manager.done()


@create_team_router.message(Command("create"))
async def handle_create_team(message: Message, state: FSMContext, dialog_manager: DialogManager) -> None:
    """
    Start to create a new team
    """
    await dialog_manager.start(CreateTeam.title, mode=StartMode.RESET_STACK)


@create_team_router.message(Command("manage"))
async def handle_manage_list(message: Message, state: FSMContext, dialog_manager: DialogManager) -> None:
    """
    Show list of managed teams
    """
    teams = await Repository().queryAdminTeams(make_person(message.from_user))

    # Build text
    msg = _("msg_manage_list_head")
    for team in teams:
        teamIdStr = even_hex(team.id)
        msg += _("msg_manage_list_item{teamIdStr}{title}{description}").format(
            teamIdStr = teamIdStr,
            title = team.title,
            description=team.description)

    await message.answer(msg)



# /m04, /m2F4H etc
manage_pattern = even_hex_pattern("m")

@create_team_router.message(Command(manage_pattern))
async def handle_manage_team(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    """
    Start to manage team from command
    """
    teamId = even_hex_parse(manage_pattern, message.text.lstrip('/'))
    if teamId is not None:
        teamIdStr = even_hex(teamId)
        teamModel = await Repository().queryAdminTeam(teamId, make_person(message.from_user))
        if teamModel:
            # Add the text representation of team ID
            team_values = dict(
                teamModel.model_dump(),
                **{_TEAM_ID_STR : teamIdStr }
            )

            await dialog_manager.start(CreateTeam.summary, data = team_values, mode = StartMode.RESET_STACK)
        else:
            # Team is not exists
            await message.answer(_("msg_team_not_found{teamIdStr}").format(
                teamIdStr = teamIdStr
            ))    



async def handle_member_team(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    pass


def register_dispatcher(dp: Dispatcher) -> None:
    """
    Register components of the module.
    """
    localize_router(create_team_router)
    dp.include_router(create_team_router)
    

