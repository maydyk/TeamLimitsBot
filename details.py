"""
Many useful functions

@Author: Denis Maydykovsky
"""


from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.state import State
from aiogram_dialog import DialogManager, ChatEvent, StartMode
from aiogram_dialog.api.entities import ShowMode, Data
from aiogram_dialog.widgets.common import Whenable, WhenCondition
from aiogram_dialog.widgets.kbd import Button, Calendar, Checkbox, ManagedCheckbox, Start
from aiogram_dialog.widgets.kbd.button import OnClick
from aiogram_dialog.widgets.kbd.calendar_kbd import OnDateSelected
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.text import Text

from datetime import date
from international import NFormat
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol, Union, Unpack

import re

async def print_dialog_event(data: Any, manager: DialogManager):
    """
    Simple print dialog event data.
    """
    if __debug__:
        print(data)


async def dialog_copy_start_data(start_data: Dict|None, dialog_manager: DialogManager) ->  None:
    """
    Copy dialog start start data to dialog data
    """
    if isinstance(start_data, Dict):
        dialog_manager.dialog_data.update(start_data)
    

async def dialog_start_getter(dialog_manager: DialogManager, **kwargs) -> dict:
    """
    Return DialogManager start data to use it with Jinja.
    """
    return dialog_manager.start_data


async def dialog_data_getter(dialog_manager: DialogManager, **kwargs):
    return dialog_manager.dialog_data


def write_dialog_value(id: str, conversion = None) -> OnClick:
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


def write_dialog_data(id: str, data: Any|None) -> OnClick:
    async def on_click(
            callback: CallbackQuery,
            button: Button,
            manager: DialogManager,
    ) -> None:
        manager.dialog_data[id] = data

    return on_click


def when_dialog_data(key: str, condition: bool = True) -> WhenCondition:
    """
    Show widget if value in dialog data with specified `key` is True.
    """
    def callback(
            data: dict,
            widget: Whenable,
            manager: DialogManager,
        ) -> bool:
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

async def dialog_delete_message(
        callback: CallbackQuery,
        button: Button,
        dialog_manager: DialogManager,
        ) -> None:
    await callback.message.delete()
    

def write_calendar_date(next: bool) -> OnDateSelected: 
    """
    Write calendar date to `dialog_data`
    """
    async def callback(
            callback: CallbackQuery,
            source: Calendar,
            manager: DialogManager,
            selected_date: date,
        ) -> None:
        manager.dialog_data[source.widget_id] = selected_date
        if next:
            await manager.next()

    return callback

    
def zero_positive(text: str) -> int:
    """
    """
    value = int(text)
    if value < 0:
        raise ValueError(f"Negative number {text}")
    return value

class Preview(NFormat):
    """
    Update...
    """    
    def __init__(self, text: str, key_source: str, key_target: str = "preview", when:WhenCondition = None):
        super().__init__(text, when)
        self.key_source = key_source
        self.key_target = key_target

    async def _render_text(self, data:dict, manager: DialogManager) -> str:
        # Assign 
        if self.key_source in data:
            data[self.key_target] = data[self.key_source]
            return await super()._render_text(data, manager)
        else:
            return ""


async def filter_cancel(message: Message, dialog_manager: DialogManager, **kwargs) -> bool:
    cmd = Command("cancel")
    ch = await cmd(message=message, bot=message.bot)
    if ch:
        manager = dialog_manager
        await manager.done()
        return False
    else:
        return True
    

# See Method 3 from https://stackoverflow.com/q/6760685/3023211
class Singleton(type):
    """
    A metaclass for singletons
    """
    __instances = {}

    def __call__(cls, *args, **kwds):
        if cls not in cls.__instances:
            cls.__instances[cls] = super(Singleton, cls).__call__(*args, **kwds)
        return cls.__instances[cls]


def even_hex(number: int) -> str:
    """
    Format number as even hex without prefix
    """

    # Remove prefix 0x
    text = hex(number)[2:].upper()
    # Pad by zero
    l = len(text)
    return text.rjust(l + (l % 2), '0')


def even_hex_pattern(prefix: str) -> re.Pattern:
    """
    Build a regular expression to parse even hex string with prefix
    """
    return re.compile(f"^{prefix}((?:[0-9A-Fa-f]{{2}})+)$")


def even_hex_parse(pattern: re.Pattern, text: str) -> str|None:
    match = pattern.search(text)
    if match:
        value = match.group(1)
        if value:
            return int(value, 16)
    
    return None


DynamicDataProvider = Callable[[CallbackQuery, Button, DialogManager], Awaitable[dict],]


# TODO: Combine DynamicDataMaker with Data
# DynamicData = Union[dict, list, int, str, float, None, DynamicDataProvider]
DynamicData = Union[Data, DynamicDataProvider]

class DStart(Start):
    def __init__(
            self,
            text: Text,
            id: str,
            state: State,
            data: DynamicData = None,
            on_click: Optional[OnClick] = None,
            show_mode: Optional[ShowMode] = None,
            mode: StartMode = StartMode.NORMAL,
            when: WhenCondition = None):
        super().__init__(text, id, state, data, on_click, show_mode, mode, when)
        self.dynamic_data = data

    async def _on_click(self, callback: CallbackQuery, button: Button,
                        manager: DialogManager):
        # Replace start data before super call
        if isinstance(self.dynamic_data, Callable):
            self.start_data = await self.dynamic_data(callback, button, manager)

        return await super()._on_click(callback, button, manager)
    

async def dialog_dynamic_data(callback: CallbackQuery, button: Button, dialog_manager: DialogManager):
    return dialog_manager.dialog_data


async def initialize_checkboxes(manager: DialogManager, *ids: List[str]) -> None:
    """
    Lookup manager.dialog_data for specified ids and set corresponding
    checkbox to an appropriate state. 
    """
    data = manager.dialog_data
    for id in ids:
        widget = manager.find(id)
        assert(isinstance(widget, ManagedCheckbox))
        if id in data:
            await widget.set_checked(data[id])


# Self testing
if __name__ == "__main":

    # Testing even_hex
    assert(even_hex(0x5f7) == "05F7")
    assert(even_hex(0xA679) == "A679")

