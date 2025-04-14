""""
Module wizard
creates the wizard line
"""

from aiogram import F
from aiogram.fsm.state import State
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Back, Next, Row, SwitchTo
from aiogram_dialog.widgets.common import Whenable, WhenCondition
from international import NConst, NFormat
from typing import Final, List, Tuple

_HOME_ID: Final[str] = "__home__"

def _get_states_and_index(manager: DialogManager) -> Tuple[List[State], int]:
    context = manager.current_context()
    states = manager.dialog().states()
    current_index = states.index(context.state)

    return (states, current_index)

def _when_back(
        data: dict,
        widget: Whenable,
        manager: DialogManager
        ) -> bool:
    states, current_index = _get_states_and_index(manager)    
    return current_index > 0

def _when_home(
        data: dict,
        widget: Whenable,
        manager: DialogManager
        ) -> bool:
    states, current_index = _get_states_and_index(manager)    
    return current_index != len(states) - 1

def _when_next(
        data: dict,
        widget: Whenable,
        manager: DialogManager
        ) -> bool:
    states, current_index = _get_states_and_index(manager)    
    return current_index < len(states) - 1


def wizard_control(homeState: State, showWizard: str, back: str, home: str, next: str) -> Row:
    return Row(
        Back(NConst(back), when=_when_back),
        SwitchTo(
            NConst(home),
            id=_HOME_ID,
            state=homeState,
            when=_when_home,
        ),
        Next(NConst(next), when=_when_next),
        when=F[showWizard]
    )


class Preview(NFormat):
    """
    Update text from data
    """    
    def __init__(self, text: str, key_source: str, key_target: str, when:WhenCondition = None):
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


def wizard_preview(text: str, showPreview: str, key_source: str, key_target="preview") -> Preview:
    return Preview(
        text = text,
        key_source=key_source,
        key_target=key_target,
        when=F[showPreview]
    )