"""
Many useful functions

@Author: Denis Maydykovsky
"""

from typing import Any
from aiogram_dialog import DialogManager

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

