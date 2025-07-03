"""
Module confirmation_dialog
defines a simple confirmation

@Author: Denis Maydykovsky
"""

from aiogram.fsm.state import State
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, StartMode, Window
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.widgets.common import WhenCondition
from aiogram_dialog.widgets.kbd import Button, Cancel, Row, Start
from aiogram_dialog.widgets.kbd.button import OnClick
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.utils import GetterVariant, ensure_data_getter

from typing import Any, Final

from .details import DStart, dialog_start_getter
from .international import NConst, NFormat

_CONFIRM_YES: Final[str] = "__confirm_yes__"

def make_confirmation_dialog(
        text: str,
        no: str,
        yes: str,
        result: Any,
        state: State,
        ) -> Dialog:
    """
    Create dialog
    """
    return Dialog(
        Window(
            NFormat(text),
            Row(
                Cancel(NConst(no)),
                Cancel(
                    NConst(yes),
                    id = _CONFIRM_YES,
                    result = result,
                ),
            ),
            state=state,
            getter=dialog_start_getter
        )
    )

