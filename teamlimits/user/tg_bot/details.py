"""
Many useful functions

@Author: Denis Maydykovsky
"""


from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.filters.command import CommandObject, CommandPatternType
from aiogram.fsm.state import State
from aiogram_dialog import DialogManager, ChatEvent, StartMode
from aiogram_dialog.api.entities import ShowMode, Data
from aiogram_dialog.api.exceptions import InvalidWidgetType
from aiogram_dialog.widgets.common import Whenable, WhenCondition
from aiogram_dialog.widgets.kbd import Button, Calendar, ManagedCheckbox, Start
from aiogram_dialog.widgets.kbd.button import OnClick
from aiogram_dialog.widgets.kbd.calendar_kbd import OnDateSelected
from aiogram_dialog.widgets.text import Text
from aiogram_dialog.widgets.utils import GetterVariant, ensure_data_getter
from datetime import date
from operator import itemgetter
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union


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


def write_dialog_value(id: str, conversion: Optional[Callable[[Any], Any]] = None) -> OnClick:
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


def write_dialog_data(id: str, data: Optional[Any]) -> OnClick:
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


async def dialog_filter_cancel(message: Message, dialog_manager: DialogManager, **kwargs) -> bool:
    if await filter_command(message, "cancel"):
        manager = dialog_manager
        await manager.done()
        return False
    else:
        return True
    

async def parse_command(message: Message, *values: CommandPatternType) -> str:
    res = await Command(*values)(message=message, bot=message.bot)
    if isinstance(res, dict):
        cmd = res.get("command")
        if isinstance(cmd, CommandObject):
            return cmd.command
    # Command wasn't parsed
    return ""


async def filter_command(message: Message, *values: CommandPatternType) -> bool:
    """
    Returns True if one of value match as command.
    """
    return bool(await Command(*values)(message=message, bot=message.bot))


# TODO: Combine DynamicDataMaker with Data
# DynamicData = Union[dict, list, int, str, float, None, DynamicDataProvider]
DynamicData = Union[Data, GetterVariant]


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
        
        # Check data is getter
        try:
            self.dynamic_data = ensure_data_getter(data)
            data = None
        except InvalidWidgetType:
            self.dynamic_data = None

        super().__init__(text, id, state, data, on_click, show_mode, mode, when)


    async def _on_click(self, callback: CallbackQuery, button: Button,
                        manager: DialogManager) ->None :
        # Replace start data before super call
        if self.dynamic_data:
            self.start_data = await self.dynamic_data(**manager.middleware_data)

        await super()._on_click(callback, button, manager)


def dynamic_dialog_data_items(*keys: str) -> Callable[..., Awaitable[Dict[str, Any]]]:
    """
    Build a data getter for DStart, that extract specified keys from dialog data.
    """
    
    async def dialog_items(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
        return dict(zip(keys, itemgetter(*keys)(dialog_manager.dialog_data)))
    
    return dialog_items

    
async def dynamic_dialog_start_data(dialog_manager: DialogManager, **kwargs) -> Dict:
    return dialog_manager.start_data


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

