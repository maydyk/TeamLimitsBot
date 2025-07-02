"""
Module manage_crew

Contains a telegram dialog to create and manage a crew

@Author: Denis Maydykovsky
"""

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.api.entities import Data
from aiogram_dialog.widgets.input import ManagedTextInput, TextInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Next, Row
from confirmation_dialog import make_confirmation_dialog
from details import (
    DStart,
    dialog_copy_start_data,
    dialog_data_getter,
    dynamic_dialog_data_items,
    dialog_filter_cancel,
    write_dialog_data,
    write_dialog_value,
    zero_positive,
)
from international import N_, NConst, NFormat, NJinja, _, localize_router
from models_base import CrewModel, PersonModel
from model_fields import fields
from repository import Repository, make_person_team
from typing import Any, Final, Tuple
from wizard import wizard_control, wizard_preview, Preview

import logging

_logger = logging.getLogger(__name__)

class CreateCrew(StatesGroup):
    title = State()
    minimalMates = State()
    maximalMates = State()
    summary = State()

# Constants widget IDs
_ID: Final[str] = fields(CrewModel).id
_CREW_ID_STR: Final[str] = "crewIdStr"
_TITLE: Final[str] = fields(CrewModel).title
_MINIMAL_MATES: Final[str] = fields(CrewModel).minimalMates
_RESET_MINIMAL_MATES: Final[str] = "resetMinimalMates"
_MAXIMAL_MATES: Final[str] = fields(CrewModel).maximalMates
_FIXED_MAXIMAL_MATES: Final[str] = "fixedMaximalMates"
_RESET_MAXIMAL_MATES: Final[str] = "resetMaximalMates"
_MANAGE_CREW: Final[str] = "manageCrew"
_DELETE_CREW: Final[str] = "deleteCrew"
_INSERT_CREW: Final[str] = "insertCrew"
_UPDATE_CREW: Final[str] = "updateCrew"
_FINISH_CREW: Final[str] = "finishCrew"


# Row with manage controls
_manage_crew_wizard = wizard_control(
    homeState=CreateCrew.summary,
    showWizard=_MANAGE_CREW,
    back=N_("create_crew_back"),
    home=N_("create_crew_home"),
    next=N_("create_crew_next"),
)

def _preview(key: str) -> Preview:
    return wizard_preview(
        text = N_("create_crew_preview{preview}"),
        showPreview=_MANAGE_CREW,
        key_source=key
    )

def _get_member(dialog_manager: DialogManager) -> Tuple[int, PersonModel]:
    return make_person_team(dialog_manager.start_data)


async def _on_query_title(
        callback: CallbackQuery,
        source: ManagedTextInput,
        manager: DialogManager,
        data: Any,
        ) -> None:
    """
    Handle crew title
    """
    teamId, *_ = _get_member(manager)
    if await Repository().checkCrewTitleIsUnique(teamId, data):
        manager.dialog_data[_TITLE] = data
        await manager.next()
    else:
        await callback.answer(_("create_crew_duplicated_title{title}").format(
            title = data
        ))


async def _minimal_mates_error(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        error: ValueError,
        ) -> None:
    await message.answer(_("create_crew_minimal_mates_error{value}").format(
        value = message.text
    ))    

async def _fixed_maximal_mates(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    minimalMates = manager.dialog_data[_MINIMAL_MATES]
    manager.dialog_data[_MAXIMAL_MATES] = minimalMates


async def _maximal_mates_success(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        data: Any,
        ) -> None:
    minimalMates = manager.dialog_data[_MINIMAL_MATES] or 0
    maximalMates = data or None

    if maximalMates is None or minimalMates <= maximalMates:
        manager.dialog_data[_MAXIMAL_MATES] = maximalMates
        await manager.next()
    else:
        await message.answer(
            _("create_crew_maximal_mates_invalid{minimalMates}{maximalMates}")
            .format(
                minimalMates = minimalMates,
                maximalMates = maximalMates
            ))


async def _maximal_mates_error(
        message: Message,
        source: ManagedTextInput,
        manager: DialogManager,
        error: ValueError,
        ) -> None:
    await message.answer(
        _("create_crew_maximal_mates_error{value}")
        .format(
            value = message.text
        )
    )


async def _manage_crew(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    manager.dialog_data[_MANAGE_CREW] = True


async def _insert_crew(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    
    crew_values = manager.dialog_data
    assert(not _ID in crew_values)

    teamId, member = _get_member(manager)

    try:
        crew = CrewModel(**crew_values)
        crewId = await Repository().insertCrew(person = member, crew=crew)
        manager.dialog_data[_ID] = crewId
    except Exception as e:
        
        breakpoint()
        await callback.answer(
            _("create_crew_insert_failed{title}")
            .format(
                title = crew_values.get(_TITLE, "")
            ))


async def _update_crew(
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager,
        ) -> None:
    
    crew_values = manager.dialog_data
    assert(_ID in crew_values)

    try:
        crew = CrewModel(**crew_values)
        crewId = await Repository().updateCrew(crew=crew)
    except Exception as e:
        _logger.exception(e)
        breakpoint()
        await callback.answer(
            _("create_crew_update_failed{title}")
            .format(
                title = crew_values.get(_TITLE, "")
            )
        )


async def _crew_summary_result(
        data: Data,
        result: Any,
        dialog_manager: DialogManager,
        ) -> None:
    if result == _DELETE_CREW:
        crewId = data[_ID]
        try:
            await Repository().deleteCrew(crewId=crewId)

            dialog_manager.dialog_data.pop(_ID, "")
            dialog_manager.dialog_data.pop(_CREW_ID_STR, "")
        except:
            breakpoint()
            pass


# Delete crew confirmation
class ConfirmDeleteCrew(StatesGroup):
    confirmation = State()


_delete_crew_confirmation = make_confirmation_dialog(
    text = N_("delete_crew_confirmation{title}"),
    no = N_("delete_crew_confirmation_no"),
    yes = N_("delete_crew_confirmation_yes"),
    result = _DELETE_CREW,
    state = ConfirmDeleteCrew.confirmation
)


# Main crew dialog
_create_crew_dialog = Dialog(
    # Query for crew name
    Window(
        NConst(text=N_("create_crew_query_title")),
        _preview(key = _TITLE),
        _manage_crew_wizard,
        TextInput(
            id = _TITLE,
            on_success=_on_query_title,
            filter=dialog_filter_cancel,
        ),
        state=CreateCrew.title,
        getter=dialog_data_getter,
    ),

    # Query for minimal mates
    Window(
        NConst(text=N_("create_crew_minimal_mates")),
        _preview(_MINIMAL_MATES),
        Next(
            text = NConst(text=N_("create_crew_reset_minimal_mates")),
            id = _RESET_MINIMAL_MATES,
            on_click=write_dialog_data(_MINIMAL_MATES, 0),
        ),
        _manage_crew_wizard,
        TextInput(
            id=_MINIMAL_MATES,
            type_factory=zero_positive,
            on_success=Next(on_click=write_dialog_value(_MINIMAL_MATES)),
            on_error=_minimal_mates_error,
            filter=dialog_filter_cancel,
        ),
        state=CreateCrew.minimalMates,
        getter=dialog_data_getter,
    ),

    # Query for maximal mates
    Window(
        NConst(N_("create_crew_maximal_mates")),
        _preview(_MAXIMAL_MATES),
        Row(
            Next(
                text = NFormat(text=N_("create_crew_fixed_maximal_mates{minimalMates}")),
                id = _FIXED_MAXIMAL_MATES,
                on_click=_fixed_maximal_mates,
                when=F[_MINIMAL_MATES],
            ),
            Next(
                text = NConst(text=N_("create_team_reset_reset_maximal_mates")),
                id = _RESET_MAXIMAL_MATES,
                on_click=write_dialog_data(_MAXIMAL_MATES, None),
            )
        ),
        _manage_crew_wizard,
        TextInput(
            id = _MAXIMAL_MATES,
            type_factory=zero_positive,
            on_success=_maximal_mates_success,
            on_error=_maximal_mates_error,
            filter=dialog_filter_cancel,
        ),
        state=CreateCrew.maximalMates,
        getter=dialog_data_getter,
    ),

    # Crew summary
    Window(
        NJinja(N_("create_crew_summary")),
        Row(
            _manage_crew_wizard,
            Button(
                text = NConst(text=N_("create_crew_manage")),
                id = _MANAGE_CREW,
                on_click=_manage_crew,
                when=~F[_MANAGE_CREW]
            ),
            DStart(
                text = NConst(text=N_("create_crew_delete")),
                id = _DELETE_CREW,
                state=ConfirmDeleteCrew.confirmation,
                data=dynamic_dialog_data_items(_ID, _TITLE,),
                when=F[_ID],
            ),
            Button(
                text = NConst(text=N_("create_crew_insert")),
                id = _INSERT_CREW,
                on_click=_insert_crew,
                when=~F[_ID]
            ),
            Button(
                text = NConst(text=N_("create_crew_update")),
                id = _UPDATE_CREW,
                on_click=_update_crew,
                when=F[_ID],
            ),
            Cancel(
                text = NConst(text=N_("create_crew_finish")),
                id = _FINISH_CREW,
            ),
        ),
        state=CreateCrew.summary,
        getter=dialog_data_getter,
        on_process_result=_crew_summary_result,
        parse_mode="html"
    ),
    on_start=dialog_copy_start_data
)


create_crew_router = Router()
create_crew_router.include_router(_create_crew_dialog)
create_crew_router.include_router(_delete_crew_confirmation)


@create_crew_router.message(Command("cancel"))
async def handle_cancel(message: Message, dialog_manager: DialogManager, **kwargs) -> None:
    await dialog_manager.done()


def register_dispatcher(dp: Dispatcher) -> None:
    localize_router(create_crew_router)
    dp.include_router(create_crew_router)


