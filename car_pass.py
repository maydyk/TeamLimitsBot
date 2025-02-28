import asyncio
import logging
from aiogram import Bot, Router, types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

TOKEN = "..."

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

PASSENGERS_FILE = "passengers.txt"
DRIVERS_FILE = "drivers.txt"

stats_message_id = None  # ID сообщения со статистикой
stats_chat_id = None  # ID чата для статистики

# Функции для работы с файлами
def get_count(filename):
    try:
        with open(filename, 'r') as file:
            return len(file.readlines())
    except FileNotFoundError:
        return 0

def add_user(filename, user_id):
    with open(filename, "a") as file:
        file.write(f"{user_id}\n")

# Кнопки
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🚗 Записаться водителем", callback_data="driver")],
    [InlineKeyboardButton(text="🧑‍🤝‍🧑 Записаться пассажиром", callback_data="passenger")]
])

@router.message(Command("start"))
async def start(message: types.Message):
    global stats_chat_id
    stats_chat_id = message.chat.id  # Запоминаем чат для статистики
    await message.answer("Выберите действие", reply_markup=keyboard)

@router.callback_query()
async def process_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if callback_query.data == "driver":
        add_user(DRIVERS_FILE, user_id)
    else:
        add_user(PASSENGERS_FILE, user_id)
    await callback_query.answer("Вы записаны!")

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

    asyncio.create_task(update_stats())  # Запускаем обновление статистики ОДИН раз
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
