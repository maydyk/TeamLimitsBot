"""
module create_team_wizard

Contains a dialog wizard to create a new team.

@Author: Denis Maydykovsky
"""

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    CallbackQuery,
)

from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.widgets.input import TextInput, ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, Calendar, Checkbox, Next, Row, SwitchTo

from details import (
    dialog_data_getter,
    or_zero,
    when_dialog_data,
    write_calendar_date,
    write_checkbox_state,
    write_dialog_value,
    zero_positive,
)

# Setup localization
from international import _, localize_router, N_, NConst, NFormat, NJinja

from typing import Any, Final


class CreateTeamWizard(StatesGroup):
    title = State()
    description = State()
    minimalMembers = State()
    maximalMembers = State()
    askForCrews = State()
    minimalCrews = State()
    maximalCrews = State()
    deadline = State()
    options = State()

    summary = State()

# Constants widget IDs
_ID_TITLE: Final[str] = "title"
_ID_ASC_DESCRIPTION: Final[str] = "askDescription"
_ID_DESCRIPTION: Final[str] = "description"
_ID_MINIMAL_MEMBERS: Final[str] = "minimalMembers"
_ID_SKIP_MINIMAL_MEMBERS: Final[str] = "skipMinimalMembers"
_ID_MAXIMAL_MEMBERS: Final[str] = "maximalMembers"
_ID_FIX_MAXIMAL_MEMBERS: Final[str] = "fixMaximalMembers"
_ID_SKIP_MAXIMAL_MEMBERS: Final[str] = "skipMaximalMembers"
_ID_ENABLE_CREWS: Final[str] = "enableCrews"
_ID_SETUP_CREWS_LIMIT: Final[str] = "setupCrewsLimit"
_ID_SKIP_CREWS_LIMIT: Final[str] = "skipCrewsLimit"
_ID_MINIMAL_CREWS: Final[str] = "minimalCrews"
_ID_SKIP_MINIMAL_CREWS: Final[str] = "skipMinimalCrews"
_ID_MAXIMAL_CREWS: Final[str] = "minimalCrews"
_ID_FIX_MAXIMAL_CREWS: Final[str] = "fixMaximalCrews"
_ID_SKIP_MAXIMAL_CREWS: Final[str] = "skipMaximalCrews"
_ID_ENABLE_DEADLINE: Final[str] = "enableDeadline"
_ID_DEADLINE: Final[str] = "deadline"



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
        await manager.switch_to(CreateTeamWizard.minimalMembers)

    
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
    minimalMembers = or_zero(manager.dialog_data.get(_ID_MINIMAL_MEMBERS))
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


async def fix_maximal_members(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager
    ) -> None:
    minimalMembers = manager.dialog_data.get(_ID_MINIMAL_MEMBERS)
    manager.dialog_data[_ID_MAXIMAL_MEMBERS] = minimalMembers
       

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
    minimalCrews = or_zero(manager.dialog_data.get(_ID_MINIMAL_CREWS))
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


async def fix_maximal_crews(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager
    ) -> None:
    minimalCrews = manager.dialog_data.get(_ID_MINIMAL_CREWS)
    manager.dialog_data[_ID_MAXIMAL_CREWS] = minimalCrews


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
        state=CreateTeamWizard.title,
        getter=dialog_data_getter,
    ),
    
    # Query team description with [skip] button.
    Window(
        NConst(N_("create_team_query_description")),
        TextInput(id=_ID_DESCRIPTION, on_success=Next(on_click=write_dialog_value(_ID_DESCRIPTION))),
        Next(NConst(N_("create_team_skip_description"))),
        state=CreateTeamWizard.description,
    ),
    
    # Query for team minimal members with [skip] button.
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
            NConst(N_("create_team_skip_minimal_members")),
            id=_ID_SKIP_MINIMAL_MEMBERS,
            on_click=write_dialog_value(_ID_MINIMAL_MEMBERS, lambda x: x or 0),
        ),
        state=CreateTeamWizard.minimalMembers,
    ),

    # Query for team maximalMembers.
    # maximalMembers can be great or equal than minimalMembers
    Window(
        NFormat(N_("create_team_query_maximal_members{minimalMembers}")),
        TextInput(
            id=_ID_MAXIMAL_MEMBERS,
            type_factory=zero_positive,
            on_success=maximal_members_success,
            on_error=minimal_members_error,
        ),
        Row(
            Next(
                NFormat(N_("create_team_fix_maximal_members{minimalMembers}")),
                id=_ID_FIX_MAXIMAL_MEMBERS,
                on_click=fix_maximal_members,
                when=when_dialog_data(_ID_MINIMAL_MEMBERS)
            ),
            Next(
                NConst(N_("create_team_skip_maximal_members")),
                id=_ID_SKIP_MAXIMAL_MEMBERS,
                on_click=write_dialog_value(_ID_MAXIMAL_MEMBERS, lambda x: x or 0),
                )
            ),
        state=CreateTeamWizard.maximalMembers,
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
            NConst(N_("create_team_skip_crews_limits")),
            id=_ID_SKIP_CREWS_LIMIT,
            state=CreateTeamWizard.deadline,
        ),
        state=CreateTeamWizard.askForCrews,
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
            NConst(N_("create_team_skip_minimal_crews")),
            id=_ID_SKIP_MINIMAL_CREWS,
            on_click=write_dialog_value(_ID_MINIMAL_CREWS, lambda x: x or 0),
        ),
        state=CreateTeamWizard.maximalCrews,
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
                NFormat(N_("create_team_set_crews_fixed{minimalCrews}")),
                id=_ID_FIX_MAXIMAL_CREWS,
                on_click=fix_maximal_crews,
                when=when_dialog_data(_ID_MINIMAL_CREWS),
            ),
            Next(
                NConst(N_("create_team_skip_maximal_crews")),
                id=_ID_SKIP_MAXIMAL_CREWS,
                on_click=write_dialog_value(_ID_MAXIMAL_CREWS, lambda x: x or 0),
            )
        ),
        state=CreateTeamWizard.minimalCrews,
        getter=dialog_data_getter,
    ),

    # Deadline
    Window(
        NConst(N_("create_team_deadline_welcome")),
        NFormat(N_("create_team_deadline_show{deadline}"),
                when=when_dialog_data(_ID_DEADLINE)
                ),
        Calendar(
            id=_ID_DEADLINE,
            on_click=write_calendar_date,
            when=when_dialog_data("enableDeadline"),
        ),
        Checkbox(
            NConst(N_("create_team_enable_deadline_checked")),
            NConst(N_("create_team_enable_deadline_unchecked")),
            id=_ID_ENABLE_DEADLINE,
            on_state_changed=write_checkbox_state,
        ),
        Next(NConst(N_("create_team_deadline_next"))),
        state=CreateTeamWizard.deadline,
        getter=dialog_data_getter,
    ),

    # Advanced options
    Window(
        NJinja(N_("create_team_options_welcome{deadline}")),
        Checkbox(
            NConst(N_("create_team_suspend_recruitment_checked")),
            NConst(N_("create_team_suspend_recruitment_unchecked")),
            id="suspendRecruitment",
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            NConst(N_("create_team_suspend_waiting_queue_checked")),
            NConst(N_("create_team_suspend_waiting_queue_unchecked")),
            id="suspendWaitingQueue",
            on_state_changed=write_checkbox_state,
        ),
        Checkbox(
            NConst(N_("create_team_suspend_deadline_queue_checked")),
            NConst(N_("create_team_suspend_deadline_queue_unchecked")),
            id="suspendDeadlineQueue",
            on_state_changed=write_checkbox_state,
            when=when_dialog_data("enableDeadline"),
        ),
        Next(NConst(N_("create_team_options_next"))),
        state=CreateTeamWizard.options,
        getter=dialog_data_getter,
        parse_mode="html",
    ),

    # TODO: Add administrators and banned people.

    # Summary
    Window(
        NJinja(
            "<u>Summary</u>:\n\n"
            "<b>Name</b>: {{title}}\n"
            "<b>Description</b>    : {{description}}\n"
            "<b>Maximal members</b>: {{maximalMembers}}\n"
            "<b>Minimal members</b>: {{minimalMembers}}\n"
            "<b>Enable crews</b>   : {{enableCrews}}\n"
            "<b>Maximal crews</b>  : {{maximalCrews}}\n"
            "<b>Minimal crews</b>  : {{minimalCrews}}\n"
            "<b>Enable deadline</b> : {{enableDeadline}}\n"
            "<b>Deadline</b>       : {{deadline}}\n"
            "<b>Disable recruitment</b>: {{disableRecruitment}}\n"
            "<b>Disable waiting queue</b>: {{disableWaitingQueue}}\n"
            "<b>Disable deadline queue</b>: {{disableDeadlineQueue}}"
        ),
        state=CreateTeamWizard.summary,
        getter=dialog_data_getter,
        parse_mode="html",
    ),
)

async def handle_create_team(message: Message, state: FSMContext, dialog_manager: DialogManager) -> None:
    await dialog_manager.start(CreateTeamWizard.title, mode=StartMode.RESET_STACK)

def register_dispatcher(dp:Dispatcher) -> None:
    """
    Register components of the module.
    """
    localize_router(create_team_wizard)
    dp.include_router(create_team_wizard)
    dp.message.register(handle_create_team, Command("create"))
    

