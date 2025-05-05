import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from db.database import Database
from services.message_service import MessageService
from models.user import SYSTEM_USER_ID
from utils.error_utils import format_error

# Инициализация бота и диспетчера
bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher()

# Инициализация сервисов
db = Database()
message_service = MessageService(bot)

@dp.message()
async def handle_message(message: Message):
    """Обработка всех сообщений"""
    try:
        # Обрабатываем сообщение
        if message.voice:
            result = await message_service.process_message(
                user_id=message.from_user.id,
                message_id=message.message_id,
                voice_file_id=message.voice.file_id
            )
        else:
            result = await message_service.process_message(
                user_id=message.from_user.id,
                message_id=message.message_id,
                text=message.text
            )
        
        # Отправляем результат пользователю
        await message_service.send_result_to_user(message.from_user.id, result)
        
    except Exception as e:
        error_msg = format_error(e, "Error processing message")
        await db.log(message.from_user.id, "BOT_ERROR", error_msg, print_log=True)
        await message.answer("Произошла ошибка при обработке сообщения.")

@dp.startup()
async def on_startup():
    """Действия при запуске бота"""
    print("[INFO] Bot is starting...")
    try:
        await db.log(SYSTEM_USER_ID, "BOT_STARTED", "Bot started", print_log=True)
        print("[INFO] Bot started successfully")
    except Exception as e:
        print(f"[ERROR] Failed to start bot: {str(e)=}")
        raise

if __name__ == "__main__":
    print("[INFO] Starting bot...")
    dp.run_polling(bot) 
    