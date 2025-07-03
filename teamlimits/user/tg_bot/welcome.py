"""
Handle start command and define start dialogs

@Author: Denis Maydykovsky
"""

from aiogram import Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, Message
from aiogram_dialog import Dialog, DialogManager, Window

from teamlimits.user.tg_bot.details import dialog_start_getter
from teamlimits.user.tg_bot.international import _, N_, localize_router, NConst, NJinja

# Shows the first welcome message.
class Welcome(StatesGroup):
    welcome = State()

welcome_dialog = Dialog(
    Window(
        NJinja(N_("msg_start_welcome{bot_name}")),
        state=Welcome.welcome,
        parse_mode="html",
    ),
    getter=dialog_start_getter
)

# Shows the second welcome message with initial commands
class StartActions(StatesGroup):
    select_actions = State()

# Shows initial command menu and closes itself.
start_actions_dialog = Dialog(
    Window(
        NConst(N_("msg_start_select_action")),
        state=StartActions.select_actions
    ),
)

async def handle_start(message: Message, dialog_manager: DialogManager) -> None:
    bot = dialog_manager.event.bot

    # Setup commands
    await bot.set_my_commands(
        commands=[
            BotCommand(command="cancel", description=_("menu_cancel_anywhere")),
            BotCommand(command="create", description=_("menu_create_team")),
            BotCommand(command="manage", description=_("menu_manage_team")),
            BotCommand(command="member", description=_("menu_member_team")),
        ],
    )

    # Prepare dialog data
    name = (await bot.get_my_name()).name
    data = {"bot_name": name}

    # Show 2 screen and finish dialogs
    await dialog_manager.start(
        state = Welcome.welcome,
        data = data,
        )
    await dialog_manager.done("Waiting for actions...")

    await dialog_manager.start(StartActions.select_actions)
    await dialog_manager.done("Finita!")
    

def register_dispatcher(dp: Dispatcher) -> None:
    """
    Register components of the module.
    """
    localize_router(welcome_dialog)
    localize_router(start_actions_dialog)

    dp.include_router(welcome_dialog)
    dp.include_router(start_actions_dialog)

    dp.message.register(handle_start, CommandStart())



