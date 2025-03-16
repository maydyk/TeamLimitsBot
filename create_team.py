"""
module create_team_wizard

Contains a dialog wizard to create a new team.

@Author: Denis Maydykovsky
"""

from aiogram import F, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    CallbackQuery,
)

from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.common import Whenable
from aiogram_dialog.widgets.input import TextInput, ManagedTextInput
from aiogram_dialog.widgets.kbd import Back, Button, Calendar, Cancel, Checkbox, Next, Row, SwitchTo

from details import (
    dialog_data_getter,
    when_dialog_data,
    write_dialog_data,
    write_calendar_date,
    write_checkbox_state,
    write_dialog_value,
    zero_positive,
)

# Setup localization
from international import _, localize_router, N_, NConst, NFormat, NJinja

from typing import Any, Final, List, Tuple


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
_ID_TITLE: Final[str] = "title"
_ID_ASC_DESCRIPTION: Final[str] = "askDescription"
_ID_DESCRIPTION: Final[str] = "description"
_ID_RESET_DESCRIPTION: Final[str] = "resetDescription"
_ID_MINIMAL_MEMBERS: Final[str] = "minimalMembers"
_ID_RESET_MINIMAL_MEMBERS: Final[str] = "resetMinimalMembers"
_ID_MAXIMAL_MEMBERS: Final[str] = "maximalMembers"
_ID_FIXED_MAXIMAL_MEMBERS: Final[str] = "fixedMaximalMembers"
_ID_RESET_MAXIMAL_MEMBERS: Final[str] = "resetMaximalMembers"
_ID_ENABLE_CREWS: Final[str] = "enableCrews"
_ID_SETUP_CREWS_LIMIT: Final[str] = "setupCrewsLimit"
_ID_RESET_CREWS_LIMIT: Final[str] = "resetCrewsLimit"
_ID_MINIMAL_CREWS: Final[str] = "minimalCrews"
_ID_RESET_MINIMAL_CREWS: Final[str] = "resetMinimalCrews"
_ID_MAXIMAL_CREWS: Final[str] = "maximalCrews"
_ID_FIXED_MAXIMAL_CREWS: Final[str] = "fixMaximalCrews"
_ID_RESET_MAXIMAL_CREWS: Final[str] = "skipMaximalCrews"
_ID_ENABLE_DEADLINE: Final[str] = "enableDeadline"
_ID_DEADLINE: Final[str] = "deadline"
_ID_DEADLINE_NEXT: Final[str] = "deadline_next"
_ID_SUSPEND_RECRUITMENT: Final[str] = "suspendRecruitment"
_ID_SUSPEND_WAITING_QUEUE: Final[str] = "suspendWaitingQueue"
_ID_SUSPEND_DEADLINE_QUEUE: Final[str] = "suspendDeadlineQueue"
_ID_OPTIONS_NEXT: Final[str] = "optionsNext"
_ID_MANAGE_TEAM: Final[str] = "manageTeam"
_ID_ACCEPT_TEAM: Final[str] = "acceptTeam"
_ID_TEAM_HOME: Final[str] = "__home__"

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
    
    manager.dialog_data[_ID_TITLE] = data

    if manager.dialog_data.get(_ID_ASC_DESCRIPTION):
        await manager.next()
    else:
        await manager.switch_to(CreateTeam.minimalMembers)

    
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
    minimalMembers = manager.dialog_data.get(_ID_MINIMAL_MEMBERS) or 0
    maximalMembers = data
    
    if minimalMembers <= maximalMembers:
        manager.dialog_data[_ID_MAXIMAL_MEMBERS] = maximalMembers
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
    minimalMembers = manager.dialog_data.get(_ID_MINIMAL_MEMBERS)
    manager.dialog_data[_ID_MAXIMAL_MEMBERS] = minimalMembers
       
async def reset_crews_limit(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    manager.dialog_data[_ID_MINIMAL_CREWS] = 0
    manager.dialog_data[_ID_MAXIMAL_CREWS] = 0
    

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
    minimalCrews = manager.dialog_data.get(_ID_MINIMAL_CREWS) or 0
    maximalCrews = data

    if minimalCrews <= maximalCrews:
        manager.dialog_data[_ID_MAXIMAL_CREWS] = maximalCrews
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
    minimalCrews = manager.dialog_data.get(_ID_MINIMAL_CREWS)
    manager.dialog_data[_ID_MAXIMAL_CREWS] = minimalCrews


async def manage_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    manager.dialog_data[_ID_MANAGE_TEAM] = True


async def accept_team(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    pass

manage_team_control = Row(
    Back(NConst(N_("create_team_back")), when=when_back),
    SwitchTo(
        NConst(N_("create_team_home")),
        id = _ID_TEAM_HOME,
        state=CreateTeam.summary,
        when=when_home,
        ),
    Next(NConst(N_("create_team_next")), when=when_next),
    when=F["dialog_data"][_ID_MANAGE_TEAM],
    )

create_team_wizard = Dialog(
    # Query for team name and provide [v] checkbox to include description.
    Window(
        NConst(N_("create_team_query_title")),
        TextInput(id=_ID_TITLE, on_success=on_query_title),
        Checkbox(
            NConst(N_("create_team_ask_description_checked")),
            NConst(N_("create_team_ask_description_unchecked")),
            id=_ID_ASC_DESCRIPTION,
            on_state_changed=write_checkbox_state,
        ),
        manage_team_control,
        state=CreateTeam.title,
        getter=dialog_data_getter,
    ),
    
    # Query team description with [reset] button.
    Window(
        NConst(N_("create_team_query_description")),
        TextInput(
            id=_ID_DESCRIPTION,
            on_success=Next(on_click=write_dialog_value(_ID_DESCRIPTION))),
        Next(
            NConst(N_("create_team_reset_description")),
            id=_ID_RESET_DESCRIPTION,
            on_click=write_dialog_data(_ID_DESCRIPTION, ""),
            ),
        manage_team_control,
        state=CreateTeam.description,
    ),
    
    # Query for team minimal members with [reset] button.
    # Zero or skip for minimalMembers
    Window(
        NConst(N_("create_team_query_minimal_members")),
        TextInput(
            id=_ID_MINIMAL_MEMBERS,
            type_factory=zero_positive,
            on_success=Next(on_click=write_dialog_value(_ID_MINIMAL_MEMBERS)),
            on_error=minimal_members_error,
        ),
        Next(
            NConst(N_("create_team_reset_minimal_members")),
            id=_ID_RESET_MINIMAL_MEMBERS,
            on_click=write_dialog_data(_ID_MINIMAL_MEMBERS, 0),
        ),
        manage_team_control,
        state=CreateTeam.minimalMembers,
    ),

    # Query for team maximalMembers.
    # maximalMembers can be great or equal than minimalMembers
    Window(
        NFormat(N_("create_team_query_maximal_members{minimalMembers}")),
        TextInput(
            id=_ID_MAXIMAL_MEMBERS,
            type_factory=zero_positive,
            on_success=maximal_members_success,
            on_error=maximal_members_error,
        ),
        Row(
            Next(
                NFormat(N_("create_team_fix_maximal_members{minimalMembers}")),
                id=_ID_FIXED_MAXIMAL_MEMBERS,
                on_click=fixed_maximal_members,
                when=when_dialog_data(_ID_MINIMAL_MEMBERS)
            ),
            Next(
                NConst(N_("create_team_skip_maximal_members")),
                id=_ID_RESET_MAXIMAL_MEMBERS,
                on_click=write_dialog_data(_ID_MAXIMAL_MEMBERS, 0),
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
            id=_ID_ENABLE_CREWS,
            on_state_changed=write_checkbox_state,
        ),
        # TODO: Add checkbox to strict crews (only administrators can create crews)
        Next(
            NConst(N_("create_team_setup_crews_limits")),
            id=_ID_SETUP_CREWS_LIMIT,
            when=when_dialog_data(_ID_ENABLE_CREWS),
        ),
        SwitchTo(
            NConst(N_("create_team_reset_crews_limits")),
            id=_ID_RESET_CREWS_LIMIT,
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
        TextInput(
            id=_ID_MINIMAL_CREWS,
            type_factory=zero_positive,
            on_success=Next(on_click=write_dialog_value(_ID_MINIMAL_CREWS)),
            on_error=minimal_crews_error
        ),
        Next(
            NConst(N_("create_team_reset_minimal_crews")),
            id=_ID_RESET_MINIMAL_CREWS,
            on_click=write_dialog_data(_ID_MINIMAL_CREWS, 0),
        ),
        manage_team_control,
        state=CreateTeam.maximalCrews,
        getter=dialog_data_getter,
    ),

    # Query for maximal crews
    Window(
        NConst(N_("create_team_query_maximal_crews{minimalCrews}")),
        TextInput(
            id=_ID_MAXIMAL_CREWS,
            type_factory=zero_positive,
            on_success=maximal_crews_success,
            on_error=maximal_crews_error,
        ),
        Row(
            Next(
                NFormat(N_("create_team_fixed_maximal_crews{minimalCrews}")),
                id=_ID_FIXED_MAXIMAL_CREWS,
                on_click=fixed_maximal_crews,
                when=when_dialog_data(_ID_MINIMAL_CREWS),
            ),
            Next(
                NConst(N_("create_team_reset_maximal_crews")),
                id=_ID_RESET_MAXIMAL_CREWS,
                on_click=write_dialog_value(_ID_MAXIMAL_CREWS, lambda x: x or 0),
            )
        ),
        manage_team_control,
        state=CreateTeam.minimalCrews,
        getter=dialog_data_getter,
    ),

    # Deadline
    Window(
        NConst(N_("create_team_deadline_welcome")),
        Calendar(
            id=_ID_DEADLINE,
            on_click=write_calendar_date(True),
            when=when_dialog_data(_ID_ENABLE_DEADLINE),
        ),
        Checkbox(
            NConst(N_("create_team_enable_deadline_checked")),
            NConst(N_("create_team_enable_deadline_unchecked")),
            id=_ID_ENABLE_DEADLINE,
            on_state_changed=write_checkbox_state,
        ),
        Next(
            NConst(N_("create_team_deadline_next")),
            id=_ID_DEADLINE_NEXT,
            when=when_dialog_data(_ID_ENABLE_DEADLINE, False),
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
            id=_ID_SUSPEND_RECRUITMENT,
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            NConst(N_("create_team_suspend_waiting_queue_checked")),
            NConst(N_("create_team_suspend_waiting_queue_unchecked")),
            id=_ID_SUSPEND_WAITING_QUEUE,
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            NConst(N_("create_team_suspend_deadline_queue_checked")),
            NConst(N_("create_team_suspend_deadline_queue_unchecked")),
            id=_ID_SUSPEND_DEADLINE_QUEUE,
            on_state_changed=write_checkbox_state,
            when=when_dialog_data("enableDeadline"),
        ),
        Next(NConst(N_("create_team_options_next")), id=_ID_OPTIONS_NEXT),
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
            Button(NConst(N_("create_team_manage")), id=_ID_MANAGE_TEAM, on_click=manage_team),
            Cancel(NConst(N_("create_team_accept")), id=_ID_ACCEPT_TEAM, on_click=accept_team),
        ),
        manage_team_control,
        state=CreateTeam.summary,
        getter=dialog_data_getter,
        parse_mode="html",
    ),
)

async def handle_create_team(message: Message, state: FSMContext, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(CreateTeam.title, mode=StartMode.RESET_STACK)

def register_dispatcher(dp:Dispatcher) -> None:
    """
    Register components of the module.
    """
    localize_router(create_team_wizard)
    dp.include_router(create_team_wizard)
    dp.message.register(handle_create_team, Command("create"))
    

