"""
Many useful functions

@Author: Denis Maydykovsky
"""


from typing import Any
from aiogram.types import CallbackQuery 
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button


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


def write_dialog_value(id: str):
    """
    Write value of widget with id to DialogManager's dialog_data
    """
    async def on_click(    
        callback: CallbackQuery,
        button: Button,
        manager: DialogManager) -> None:
        widget = manager.find(id)
        value = widget.get_value()
        manager.dialog_data[id] = value
    return on_click


def or_empty(s: str|None) -> str:
    """
    Return empty string if input is None
    """
    if s is None:
        return ""
    else:
        return s


