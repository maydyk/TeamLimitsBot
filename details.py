"""
Many useful functions

@Author: Denis Maydykovsky
"""


from aiogram.types import CallbackQuery 
from aiogram_dialog import DialogManager, ChatEvent
from aiogram_dialog.widgets.kbd import Button, Calendar, ManagedCheckbox
from aiogram_dialog.widgets.common import Whenable, WhenCondition

from datetime import date

from typing import Any

async def print_dialog_event(data: Any, manager: DialogManager):
    """
    Simple print dialog event data.
    """
    if __debug__:
        print(data)


async def dialog_start_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    """
    Return DialogManager start data to use it with Jinja.
    """
    return dialog_manager.start_data

async def dialog_data_getter(dialog_manager: DialogManager, **kwargs):
    return dialog_manager.dialog_data


def write_dialog_value(id: str, conversion = None):
    """
    Create and return a Button `on_click` handler who
    Writes value of widget with `id` to DialogManager's dialog_data
    """
    async def on_click(    
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager) -> None:
    
        widget = manager.find(id)
        value = widget.get_value()

        # Perform optional conversion
        manager.dialog_data[id] = value if conversion is None else conversion(value)
    
    return on_click

def when_dialog_data(key: str, condition: bool = True) -> WhenCondition:
    """
    Show widget if value in dialog data with specified `key` is True.
    """
    def callback(
            data: dict,
            widget: Whenable,
            manager: DialogManager,
        ) -> WhenCondition:
        value = manager.dialog_data.get(key, False)
        return bool(value) == bool(condition)
    return callback

async def write_checkbox_state(
        event: ChatEvent,
        checkbox: ManagedCheckbox,
        manager: DialogManager
        ) -> None:
    """
    Write checkbox state to dialog data.
    Use it as handler for CheckBox.on_state_changed
    """
    manager.dialog_data[checkbox.widget.widget_id] = checkbox.is_checked()


async def write_calendar_date(
        callback: CallbackQuery,
        source: Calendar,
        manager: DialogManager,
        selected_date: date,
    ) -> None:
    """
    Write calendar date to `dialog_data`
    """
    manager.dialog_data[source.widget_id] = selected_date

    
def zero_positive(text: str) -> int:
    """
    """
    value = int(text)
    if value < 0:
        raise ValueError(f"Negative number {text}")
    return value


def or_empty(s: str|None) -> str:
    """
    Return empty string if input is None
    """
    return "" if s is None else s

def or_zero(v: int|None) -> int:
    """
    Return zero if value is None
    """
    return 0 if v is None else v
