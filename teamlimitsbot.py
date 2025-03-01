
'''
TeamLimitsBot
A Telegram bot to manage number of participans of some event.
Author: Denis Maydykovsky 

Usage: python3 TeamLimitsBot.py <YOUR BOT TOKEN>
'''
import os
import sys
import asyncio
import logging

from aiogram import F, Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.handlers import CallbackQueryHandler
from aiogram.types import (
    Message, 
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.utils.i18n import I18n, gettext as _
from aiogram.utils.i18n.middleware import SimpleI18nMiddleware
from pathlib import Path
from typing import Any, Dict, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)

# Setup localization directory and domain
I18N_DOMAIN = 'TeamLimitsBot'
BASE_DIR = Path(__file__).parent
LOCALES_DIR = BASE_DIR / "locales"

# Setup i18n middleware
i18n = I18n(path=LOCALES_DIR, default_locale="en", domain=I18N_DOMAIN)    
localization = SimpleI18nMiddleware(i18n)
# Alias for gettext method
_ = i18n.gettext

# Treat to the first command line argumant as TOKEN.
if len(sys.argv) > 1:
    # Don't save the TOKEN in the code!
    TOKEN = sys.argv[1]
else:
    # Treat to an enviromenent variable 
    # Don't save the TOKEN in launch.json
    TOKEN = os.getenv("TEAMLIMITSBOT_TOKEN", None)

if not TOKEN:
    print(_("error-no-token-arg"), file=sys.stderr)
    logging.log(level=logging.ERROR, msg = _("error-no-token-arg"))
    sys.exit(1)

# Main objects
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
localization.setup(router)

DRIVERS_FILE = object
PASSENGERS_FILE = object

stats_message_id = None  # ID сообщения со статистикой
stats_chat_id = None  # ID чата для статистики

def get_count(file):
    return 5

# Кнопки
# keyboard = aiogram.types.InlineKeyboardMarkup(inline_keyboard=[
#     [aiogram.types.InlineKeyboardButton(text="🚗 Записаться водителем", callback_data="driver")],
#     [aiogram.types.InlineKeyboardButton(text="🧑‍🤝‍🧑 Записаться пассажиром", callback_data="passenger")]
# ])

@router.message(CommandStart())
async def start(message: Message) -> None:
    global stats_chat_id
    stats_chat_id = message.chat.id  # Запоминаем чат для статистики

    await message.answer(
        _("select_action")
        )#, reply_markup=keyboard)


class CreateEventForm(StatesGroup):
    name = State()
    description = State()


@router.message(Command("create"))
async def create(message: Message, state: FSMContext) -> None:
    await state.set_state(CreateEventForm.name)
    await message.answer(
        _("query_event_name"),
        reply_markup=ReplyKeyboardRemove(),
    )

skipId = object
@router.message(CreateEventForm.name)
async def process_name(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text)
    await state.set_state(CreateEventForm.description)
    await message.answer(
        _("query_event_description"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard = [
                [
                    InlineKeyboardButton(text="Skip", callback_data="skip_description")
                ]
            ],
            resize_keyboard=True
        ),
    )

@router.callback_query(lambda callback_query: callback_query.data == "skip_description")
async def handle_skip_description(callback_query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    await show_summary(callback_query.message, data)


@router.message(CreateEventForm.description)
async def process_description(message: Message, state: FSMContext) -> None:
    data = await state.update_data(description=message.text)
    await state.clear()
    await show_summary(message, data)

async def show_summary(message: Message, data: Dict[str, Any]) -> None:
    name = data["name"]
    description = data.get("description", "")

    text = _("new_event_created{name}{desc}").format(
        name = name,
        desc = description
    )
    await message.answer(text=text, reply_markup=ReplyKeyboardRemove())




@router.message(Command("manage"))
async def create(message: Message):
    await message.answer("manage is not implemented yet.")


async def update_stats():
    global stats_message_id, stats_chat_id
    while stats_chat_id is None:
        await asyncio.sleep(1)  # Ждем, пока кто-то введет start

    if stats_message_id is None:
        msg = await bot.send_message(stats_chat_id, "Обновление статистики...")
        stats_message_id = int(msg.message_id)
        print(1, stats_message_id)

    while True:
        drivers = get_count(DRIVERS_FILE)
        passengers = get_count(PASSENGERS_FILE)
        text = f"Водителей {drivers}\nПассажиров {passengers}"

        try:
            await bot.edit_message_text(text, chat_id=stats_chat_id, message_id=stats_message_id)
        except Exception:  # Если сообщение удалено, создаем новое
            #msg = await bot.send_message(stats_chat_id, text)
            #stats_message_id = msg.message_id
            print(3, stats_message_id)

        await asyncio.sleep(5)

async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)

    # asyncio.create_task(update_stats())  # Запускаем обновление статистики ОДИН раз
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


    