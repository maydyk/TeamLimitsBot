"""
module create_team_wizard

Contains a dialog wizard to create a new team.

@Author: Denis Maydykovsky
"""

from operator import itemgetter
from aiogram import F, Dispatcher, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    CallbackQuery,
)

from aiogram_dialog import Dialog, DialogManager, StartMode, ShowMode, Window
from aiogram_dialog.api.entities import Data
from aiogram_dialog.widgets.common import Whenable, WhenCondition
from aiogram_dialog.widgets.input import TextInput, ManagedTextInput
from aiogram_dialog.widgets.kbd import (
    Back,
    Button,
    Calendar,
    Cancel,
    Checkbox,
    Next,
    Row,
    Start,
    SwitchTo,
)

from details import (
    even_hex,
    dialog_data_getter,
    dialog_delete_message,
    dialog_dynamic_data,
    dialog_copy_start_data,
    initialize_checkboxes,
    filter_cancel,
    dialog_start_getter,
    when_dialog_data,
    write_dialog_data,
    write_calendar_date,
    write_checkbox_state,
    write_dialog_value,
    zero_positive,
    DStart,
    Preview,
)

# Setup localization
from international import _, localize_router, N_, NConst, NFormat, NJinja
import re
from typing import Any, Dict, Final, List, Tuple

from entities import Team
from database import Repository

_CONFIRM_DELETE_TEAM_YES: Final[str] = "confirmDeleteTeamYes"

class ConfirmDeleteTeam(StatesGroup):
    confirm = State()

delete_team_confirmation = Dialog(
    Window(
        NFormat(N_("delete_team_confirmation{teamId}{title}")),
        Row(
            Cancel(
                NConst(N_("delete_team_confirmation_no"))),
            Cancel(
                NConst(N_("delete_team_confirmation_yes")),
                id=_CONFIRM_DELETE_TEAM_YES,
                result=_CONFIRM_DELETE_TEAM_YES,
                ),
        ),
        state=ConfirmDeleteTeam.confirm,
        getter=dialog_start_getter,
    ),
)


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
_ID: Final[str] = Team.ID
_TEAM_ID: Final[str] = "teamId"
_TITLE: Final[str] = Team.TITLE
_ASK_DESCRIPTION: Final[str] = "askDescription"
_DESCRIPTION: Final[str] = Team.DESCRIPTION
_RESET_DESCRIPTION: Final[str] = "resetDescription"
_MINIMAL_MEMBERS: Final[str] = Team.MINIMAL_MEMBERS
_RESET_MINIMAL_MEMBERS: Final[str] = "resetMinimalMembers"
_MAXIMAL_MEMBERS: Final[str] = Team.MAXIMAL_MEMBERS
_FIXED_MAXIMAL_MEMBERS: Final[str] = "fixedMaximalMembers"
_RESET_MAXIMAL_MEMBERS: Final[str] = "resetMaximalMembers"
_ENABLE_CREWS: Final[str] = Team.ENABLE_CREWS
_RESTRICT_CREWS: Final[str] = Team.RESTRICT_CREWS
_SETUP_CREWS_LIMIT: Final[str] = "setupCrewsLimit"
_RESET_CREWS_LIMIT: Final[str] = "resetCrewsLimit"
_MINIMAL_CREWS: Final[str] = Team.MINIMAL_CREWS
_RESET_MINIMAL_CREWS: Final[str] = "resetMinimalCrews"
_MAXIMAL_CREWS: Final[str] = Team.MAXIMAL_CREWS
_FIXED_MAXIMAL_CREWS: Final[str] = "fixMaximalCrews"
_RESET_MAXIMAL_CREWS: Final[str] = "skipMaximalCrews"
_ENABLE_DEADLINE: Final[str] = Team.ENABLE_DEADLINE
_DEADLINE: Final[str] = Team.DEADLINE
_DEADLINE_NEXT: Final[str] = "deadline_next"
_SUSPEND_RECRUITMENT: Final[str] = Team.SUSPEND_RECRUITMENT
_SUSPEND_PENDING_QUEUE: Final[str] = Team.SUSPEND_PENDING_QUEUE
_SUSPEND_DEADLINE_QUEUE: Final[str] = Team.SUSPEND_DEADLINE_QUEUE
_OPTIONS_NEXT: Final[str] = "optionsNext"
_MANAGE_TEAM: Final[str] = "manageTeam"
_CANCEL_TEAM: Final[str] = "cancelTeam"
_DELETE_TEAM: Final[str] = "deleteTeam"
_INSERT_TEAM: Final[str] = "insertTeam"
_UPDATE_TEAM: Final[str] = "updateTeam"
_TEAM_HOME: Final[str] = "__home__"


def _get_states_and_index(manager: DialogManager) -> Tuple[List[State], int]:
    context = manager.current_context()
    states = manager.dialog().states()
    current_index = states.index(context.state)

    return (states, current_index)

def when_back(
        data: dict,
        widget: Whenable,
        manager: DialogManager
        ) -> bool:
    states, current_index = _get_states_and_index(manager)    
    return current_index > 0

def when_home(
        data: dict,
        widget: Whenable,
        manager: DialogManager
        ) -> bool:
    states, current_index = _get_states_and_index(manager)    
    return current_index != len(states) - 1

def when_next(
        data: dict,
        widget: Whenable,
        manager: DialogManager
        ) -> bool:
    states, current_index = _get_states_and_index(manager)    
    return current_index < len(states) - 1

async def on_query_title(
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

async def start_create_team(start_data: Dict|None, dialog_manager: DialogManager) -> None:
    # Get data from start
    await dialog_copy_start_data(start_data, dialog_manager)

    # Initialize checkboxes state
    await initialize_checkboxes(
        dialog_manager,
        _ENABLE_CREWS,
        _RESTRICT_CREWS,
        _ENABLE_DEADLINE,
        _SUSPEND_RECRUITMENT,
        _SUSPEND_PENDING_QUEUE,
        _SUSPEND_DEADLINE_QUEUE,
        )

    
async def minimal_members_error(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        error: ValueError
    ) -> None:
    await message.answer(_("create_team_minimal_members_error{value}").format(
        value = message.text
    ))


async def maximal_members_success(
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

async def maximal_members_error(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        error_: ValueError
    ) -> None:
    await message.answer(_("create_team_maximal_members_error{value}").format(
        value = message.text
    ))


async def fixed_maximal_members(
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


async def manage_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    manager.dialog_data[_MANAGE_TEAM] = True


async def cancel_team(
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
    
    await callback.message.answer(text.format(
        title=data[_TITLE]
    ))
    await callback.message.delete()

async def delete_team_data(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> Any:
    """
    Extract from DialogManager.dialog_data values to
    use in delete confirmation dialog
    """
    keys = (_ID, _TEAM_ID, _TITLE,)
    return dict(zip(keys, itemgetter(*keys)(manager.dialog_data)))


async def insert_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    
    team_values = manager.dialog_data
    assert(not _ID in team_values)

    try:
        userId = callback.from_user.id
        teamId = await Repository().insertTeam(userId=userId, **team_values)

        await manager.done()
        await callback.message.answer(_("create_team_inserted{teamId}{title}").format(
            teamId=even_hex(teamId),
            title=team_values.get(Team.TITLE, ""),
            )
        )
        
    except:
        breakpoint()
        await callback.message.answer(_("create_team_insert_failed{title}").format(
            title=team_values.get(Team.TITLE, ""),
            )
        )
        pass


async def update_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:

    team_values = manager.dialog_data.copy()
    assert(_ID in team_values)

    try:
        teamId = await Repository().updateTeam(**team_values)

        await manager.done()
        await callback.message.answer(_("create_team_updated{teamId}{title}").format(
            teamId=even_hex(teamId),
            title=team_values[Team.TITLE],
            )
        )
    except Exception as e:
        print(e)
        breakpoint()
        await callback.message.answer(_("create_team_update_failed{title}").format(
            title=team_values.get(Team.TITLE, ""),
            )
        )
        pass


async def team_summary_result(data: Data, result: Any, dialog_manager: DialogManager) -> None:
    print("team_summary_result", data, result)
    if result == _CONFIRM_DELETE_TEAM_YES:
        teamId = data[_ID]
        print(f"Delete the team {even_hex(teamId)}")
        try:
            await Repository().deleteTeam(teamId)

            # Remove ID from dictionary
            # Now we are being in state as a new team was created
            dialog_manager.dialog_data.pop(_ID, "")
            dialog_manager.dialog_data.pop(_TEAM_ID, "")
        except:
            breakpoint()
            # TODO: How to show a message here?
            pass
    pass


manage_team_control = Row(
    Back(NConst(N_("create_team_back")), when=when_back),
    SwitchTo(
        NConst(N_("create_team_home")),
        id = _TEAM_HOME,
        state=CreateTeam.summary,
        when=when_home,
        ),
    Next(NConst(N_("create_team_next")), when=when_next),
    when=F[_MANAGE_TEAM],
    )

def _preview(key: str) -> Preview:
    return Preview(
        text=N_("create_team_preview{preview}"),
        key_source=key,
        when=F[_MANAGE_TEAM]
    )

create_team_dialog = Dialog(
    # Query for team name and provide [v] checkbox to include description.
    Window(
        NConst(N_("create_team_query_title")),
        _preview(key=_TITLE),
        TextInput(
            id=_TITLE,
            on_success=on_query_title,
            filter=filter_cancel,
        ),
        Checkbox(
            NConst(N_("create_team_ask_description_checked")),
            NConst(N_("create_team_ask_description_unchecked")),
            id=_ASK_DESCRIPTION,
            on_state_changed=write_checkbox_state,
        ),
        manage_team_control,
        state=CreateTeam.title,
        getter=dialog_data_getter,
    ),
    
    # Query team description with [reset] button.
    Window(
        NConst(N_("create_team_query_description")),
        _preview(key=_DESCRIPTION),
        TextInput(
            id=_DESCRIPTION,
            on_success=Next(on_click=write_dialog_value(_DESCRIPTION)),
            filter=filter_cancel,
        ),
        Next(
            NConst(N_("create_team_reset_description")),
            id=_RESET_DESCRIPTION,
            on_click=write_dialog_data(_DESCRIPTION, ""),
        ),
        manage_team_control,
        state=CreateTeam.description,
        getter=dialog_data_getter,
    ),
    
    # Query for team minimal members with [reset] button.
    # Zero or skip for minimalMembers
    Window(
        NConst(N_("create_team_query_minimal_members")),
        _preview(key=_MINIMAL_MEMBERS),
        TextInput(
            id=_MINIMAL_MEMBERS,
            type_factory=zero_positive,
            on_success=Next(on_click=write_dialog_value(_MINIMAL_MEMBERS)),
            on_error=minimal_members_error,
            filter=filter_cancel,
        ),
        Next(
            NConst(N_("create_team_reset_minimal_members")),
            id=_RESET_MINIMAL_MEMBERS,
            on_click=write_dialog_data(_MINIMAL_MEMBERS, 0),
        ),
        manage_team_control,
        state=CreateTeam.minimalMembers,
        getter=dialog_data_getter,
    ),

    # Query for team maximalMembers.
    # maximalMembers can be great or equal than minimalMembers
    Window(
        NFormat(N_("create_team_query_maximal_members{minimalMembers}")),
        _preview(key=_MAXIMAL_MEMBERS),
        TextInput(
            id=_MAXIMAL_MEMBERS,
            type_factory=zero_positive,
            on_success=maximal_members_success,
            on_error=maximal_members_error,
            filter=filter_cancel,
        ),
        Row(
            Next(
                NFormat(N_("create_team_fix_maximal_members{minimalMembers}")),
                id=_FIXED_MAXIMAL_MEMBERS,
                on_click=fixed_maximal_members,
                when=when_dialog_data(_MINIMAL_MEMBERS)
            ),
            Next(
                NConst(N_("create_team_skip_maximal_members")),
                id=_RESET_MAXIMAL_MEMBERS,
                on_click=write_dialog_data(_MAXIMAL_MEMBERS, 0),
                )
            ),
        manage_team_control,
        state=CreateTeam.maximalMembers,
        getter=dialog_data_getter,
    ),

    # Buttons and message to setup crews
    Window(
        NConst(N_("create_team_crews_welcome")),
        Checkbox(
            NConst(N_("create_team_enable_crews")),
            NConst(N_("create_team_disable_crews")),
            id=_ENABLE_CREWS,
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            NConst(N_("create_team_restrict_crews")),
            NConst(N_("create_team_broaden_crews")),
            id=_RESTRICT_CREWS,
            on_state_changed=write_checkbox_state,
            when=when_dialog_data(_ENABLE_CREWS),
        ),
        Next(
            NConst(N_("create_team_setup_crews_limits")),
            id=_SETUP_CREWS_LIMIT,
            when=when_dialog_data(_RESTRICT_CREWS, False),
        ),
        SwitchTo(
            NConst(N_("create_team_reset_crews_limits")),
            id=_RESET_CREWS_LIMIT,
            state=CreateTeam.deadline,
            on_click=reset_crews_limit
        ),
        manage_team_control,
        state=CreateTeam.enableCrews,
        getter=dialog_data_getter,
    ),

    # Query for minimal crews
    Window(
        NConst(N_("create_team_query_minimal_crews")),
        _preview(key=_MINIMAL_CREWS),
        TextInput(
            id=_MINIMAL_CREWS,
            type_factory=zero_positive,
            on_success=Next(on_click=write_dialog_value(_MINIMAL_CREWS)),
            on_error=minimal_crews_error,
            filter=filter_cancel,
        ),
        Next(
            NConst(N_("create_team_reset_minimal_crews")),
            id=_RESET_MINIMAL_CREWS,
            on_click=write_dialog_data(_MINIMAL_CREWS, 0),
        ),
        manage_team_control,
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
            filter=filter_cancel
        ),
        Row(
            Next(
                NFormat(N_("create_team_fixed_maximal_crews{minimalCrews}")),
                id=_FIXED_MAXIMAL_CREWS,
                on_click=fixed_maximal_crews,
                when=when_dialog_data(_MINIMAL_CREWS),
            ),
            Next(
                NConst(N_("create_team_reset_maximal_crews")),
                id=_RESET_MAXIMAL_CREWS,
                on_click=write_dialog_value(_MAXIMAL_CREWS, lambda x: x or 0),
            )
        ),
        manage_team_control,
        state=CreateTeam.minimalCrews,
        getter=dialog_data_getter,
    ),

    # Deadline
    Window(
        NConst(N_("create_team_deadline_welcome")),
        _preview(key=_DEADLINE),
        Calendar(
            id=_DEADLINE,
            on_click=write_calendar_date(True),
            when=when_dialog_data(_ENABLE_DEADLINE),
        ),
        Checkbox(
            NConst(N_("create_team_enable_deadline_checked")),
            NConst(N_("create_team_enable_deadline_unchecked")),
            id=_ENABLE_DEADLINE,
            on_state_changed=write_checkbox_state,
        ),
        Next(
            NConst(N_("create_team_deadline_next")),
            id=_DEADLINE_NEXT,
            when=when_dialog_data(_ENABLE_DEADLINE, False),
            ),
        manage_team_control,
        state=CreateTeam.deadline,
        getter=dialog_data_getter,
    ),

    # Advanced options
    Window(
        NJinja(N_("create_team_options_welcome{deadline}")),
        Checkbox(
            NConst(N_("create_team_suspend_recruitment_checked")),
            NConst(N_("create_team_suspend_recruitment_unchecked")),
            id=_SUSPEND_RECRUITMENT,
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            NConst(N_("create_team_suspend_pending_queue_checked")),
            NConst(N_("create_team_suspend_pending_queue_unchecked")),
            id=_SUSPEND_PENDING_QUEUE,
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            NConst(N_("create_team_suspend_deadline_queue_checked")),
            NConst(N_("create_team_suspend_deadline_queue_unchecked")),
            id=_SUSPEND_DEADLINE_QUEUE,
            on_state_changed=write_checkbox_state,
            when=when_dialog_data("enableDeadline"),
        ),
        Next(NConst(N_("create_team_options_next")), id=_OPTIONS_NEXT),
        manage_team_control,
        state=CreateTeam.options,
        getter=dialog_data_getter,
        parse_mode="html",
    ),

    # TODO: Add administrators and banned people.

    # Summary
    Window(
        NJinja(N_("create_team_summary")),
        Row(
            manage_team_control,
            Button(
                NConst(N_("create_team_manage")),
                id=_MANAGE_TEAM,
                on_click=manage_team,
                when=~F[_MANAGE_TEAM],
            ),
            Cancel(
                NConst(N_("create_team_cancel")),
                id=_CANCEL_TEAM,
                on_click=cancel_team,
            ),
            DStart(
                NConst(N_("create_team_delete")),
                id=_DELETE_TEAM,
                state=ConfirmDeleteTeam.confirm,
                data=delete_team_data,
                when=F[_ID].is_not(None),
            ),
            Button(
                NConst(N_("create_team_insert")),
                id=_INSERT_TEAM,
                on_click=insert_team,
                when=~F[_ID]
            ),
            Button(
                NConst(N_("create_team_update")),
                id=_UPDATE_TEAM,
                on_click=update_team,
                when=F[_ID]
            ),
        ),
        state=CreateTeam.summary,
        getter=dialog_data_getter,
        on_process_result=team_summary_result,
        parse_mode="html",
    ),
    on_start=start_create_team,
)

create_team_router = Router()
create_team_router.include_router(create_team_dialog)
create_team_router.include_router(delete_team_confirmation)


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
    teams = await Repository().queryAdminTeams(message.from_user.id)

    # Build text
    msg = _("msg_manage_list_head")
    for id, (title, description) in teams.items():
        teamId = even_hex(id)
        msg += _("msg_manage_list_item{teamId}{title}{description}").format(
            teamId = teamId,
            title = title,
            description=description)

    await message.answer(msg)



# /m04, /m2F4H etc
manage_pattern = re.compile(r"^m((?:[0-9A-Fa-f]{2})+)$")

@create_team_router.message(Command(manage_pattern))
async def handle_manage_team(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    """
    Start to manage team from command
    """
    command_match = manage_pattern.search(message.text.lstrip('/'))
    if command_match:
        team_text = command_match.group(1)
        if team_text:
            teamId = int(team_text, 16)
            teamStr = even_hex(teamId)
            team_values = await Repository().queryTeam(teamId, message.from_user.id)
            if team_values:
                # Add the text representation of team ID
                team_values[_TEAM_ID] = teamStr

                await dialog_manager.start(CreateTeam.summary, data = team_values, mode = StartMode.RESET_STACK)
            else:
                # Team is not exists
                await message.answer(_("msg_team_not_found{teamId}").format(
                    teamId = teamStr
                ))    



async def handle_member_team(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    pass


def register_dispatcher(dp:Dispatcher) -> None:
    """
    Register components of the module.
    """
    localize_router(create_team_router)
    dp.include_router(create_team_router)
    

