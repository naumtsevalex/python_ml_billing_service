import os
import logging
import asyncio
import sys
from typing import Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart

from db.database import Database
from services.message_service import MessageService
from models.user import SYSTEM_USER_ID

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Инициализация компонентов
bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()
db = Database()
message_service = MessageService(bot)

@dp.message(CommandStart())
async def command_start_handler(message: types.Message) -> Any:
    """Обработчик команды /start"""
    logger.info(f"User {message.from_user.id} started bot")
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n"
        f"Я бот для обработки сообщений.\n"
        f"Твой ID: <code>{message.from_user.id}</code>"
    )
    

# @dp.message()
# async def echo_handler(message: types.Message):
#     logger.info(f"Получено сообщение: {message.text}")
#     await message.answer(f"Эхо: {message.text}")


@dp.message(F.voice)
async def voice_handler(message: types.Message):
    """Обработчик голосовых сообщений"""
    logger.info(f"Processing voice message from user {message.from_user.id}")
    await db.log(message.from_user.id, "handle_voice", f"{message=}")
    
    result = await message_service.process_message(
        user_id=message.from_user.id,
        message_id=message.message_id,
        voice_file_id=message.voice.file_id
    )
    await message_service.send_result_to_user(message.from_user.id, result)

@dp.message(F.text)
async def text_handler(message: types.Message):
    """Обработчик текстовых сообщений"""
    logger.info(f"Processing text message from user {message.from_user.id}: {message.text}")
    await db.log(message.from_user.id, "handle_text", "[text_handler]")
    
    result = await message_service.process_message(
        user_id=message.from_user.id,
        message_id=message.message_id,
        text=message.text
    )
    await message_service.send_result_to_user(message.from_user.id, result)
    

async def main() -> None:
    """Точка входа в приложение"""
    logger.info("Starting bot...")
    
    # Регистрируем старт в базе
    # await db.log(SYSTEM_USER_ID, "BOT_STARTED", "Bot started")
    
    # Запускаем поллинг (как в рабочем эхо-боте)
    logger.info("Starting polling...")
    await dp.start_polling(bot)
    

if __name__ == "__main__":
    asyncio.run(main())
    