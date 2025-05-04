import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from db.database import Database
from services.message_service import MessageService

# Инициализация бота и сервисов
bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher()
message_service = MessageService(bot)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    is_new = await message_service.register_user(message.from_user.id, message.from_user.username or str(message.from_user.id))
    if is_new:
        await message.answer("Добро пожаловать! Вы успешно зарегистрированы.")
    await message.answer(
        "Привет! Я бот для обработки текста и аудио. "
        "Отправьте мне текст или голосовое сообщение."
    )

@dp.message()
async def handle_message(message: types.Message):
    """Обработка входящих сообщений"""
    try:
        # Регистрируем пользователя, если нужно
        await message_service.register_user(message.from_user.id, message.from_user.username or str(message.from_user.id))
        
        # Обрабатываем сообщение
        task_type, task_data, file_path = await message_service.process_message(
            message.from_user.id,
            message.message_id,
            text=message.text if not message.voice else None,
            voice_file_id=message.voice.file_id if message.voice else None
        )
        
        # Отправляем задачу воркеру и получаем результат
        result = await message_service.send_task_to_worker(
            message.from_user.id,
            task_type,
            task_data,
            file_path
        )
        
        # Отправляем результат пользователю
        await message_service.send_result_to_user(message.from_user.id, result)
        
    except ValueError as e:
        if str(e) == "Insufficient balance":
            await message.answer("У вас недостаточно средств. Пополните баланс.")
        else:
            raise
    except Exception as e:
        db = Database()
        await db.log(message.from_user.id, "BOT_ERROR", f"Error processing message: {str(e)}", print_log=True)
        await message.answer("Произошла ошибка при обработке сообщения.")

async def main():
    """Запуск бота"""
    db = Database()
    await db.log(None, "BOT_STARTED", "Bot started and ready to process messages", print_log=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 