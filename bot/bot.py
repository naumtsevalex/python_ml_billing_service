import os
import json
import asyncio
import aio_pika
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from db.database import Database

# Инициализация бота
bot = Bot(token=os.environ["TELEGRAM_TOKEN"])
dp = Dispatcher()

async def register_user(message: types.Message):
    """Регистрация нового пользователя"""
    db = Database()
    user_id = message.from_user.id
    username = message.from_user.username or str(user_id)
    
    # Проверяем, существует ли пользователь
    user = await db.get_user(user_id)
    if not user:
        # Создаем нового пользователя
        user = await db.create_user(user_id, username)
        await db.log(user_id, "USER_REGISTERED", f"New user registered: {username}", print_log=True)
        await message.answer("Добро пожаловать! Вы успешно зарегистрированы.")
    else:
        await db.log(user_id, "USER_LOGIN", f"User logged in: {username}", print_log=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    await register_user(message)
    await message.answer(
        "Привет! Я бот для обработки текста и аудио. "
        "Отправьте мне текст или голосовое сообщение."
    )

@dp.message()
async def handle_message(message: types.Message):
    """Обработка входящих сообщений"""
    db = Database()
    user_id = message.from_user.id
    
    # Проверяем регистрацию
    user = await db.get_user(user_id)
    if not user:
        await register_user(message)
    
    # Получаем баланс
    balance = await db.get_balance(user_id)
    if balance <= 0:
        await message.answer("У вас недостаточно средств. Пополните баланс.")
        return

    try:
        # Подключаемся к RabbitMQ
        await db.log(user_id, "RABBITMQ_CONNECTING", f"Connecting to RabbitMQ at {os.environ['RABBITMQ_URL']}", print_log=True)
        connection = await aio_pika.connect_robust(os.environ["RABBITMQ_URL"])
        await db.log(user_id, "RABBITMQ_CONNECTED", "Successfully connected to RabbitMQ", print_log=True)
        
        # Создаем канал
        channel = await connection.channel()
        await db.log(user_id, "RABBITMQ_CHANNEL", "Created RabbitMQ channel", print_log=True)
        
        # Формируем задачу
        task = {
            "user_id": user_id,
            "type": "text",  # или "voice" для голосовых сообщений
            "data": message.text
        }
        
        # Создаем очередь для ответа
        reply_queue = await channel.declare_queue(exclusive=True)
        await db.log(user_id, "RABBITMQ_REPLY_QUEUE", f"Created reply queue: {reply_queue.name}", print_log=True)
        
        # Отправляем задачу
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(task).encode(),
                reply_to=reply_queue.name
            ),
            routing_key="tasks"
        )
        
        await db.log(user_id, "TASK_SENT", f"Task sent to worker: {task['type']}", print_log=True)
        
        # Ждем ответ
        async with reply_queue.iterator() as queue_iter:
            await db.log(user_id, "WAITING_REPLY", "Waiting for worker reply", print_log=True)
            async for message in queue_iter:
                async with message.process():
                    result = json.loads(message.body.decode())
                    if result["status"] == "success":
                        await db.log(user_id, "TASK_RESULT", f"Task completed: {result['message']}", print_log=True)
                        await bot.send_message(user_id, result["message"])
                    else:
                        await db.log(user_id, "TASK_ERROR", f"Task failed: {result.get('error', 'Unknown error')}", print_log=True)
                        await bot.send_message(user_id, "Произошла ошибка при обработке задачи.")
                    break
    
    except Exception as e:
        await db.log(user_id, "BOT_ERROR", f"Error processing message: {str(e)}", print_log=True)
        await message.answer("Произошла ошибка при обработке сообщения.")
    
    finally:
        if 'connection' in locals():
            await connection.close()
            await db.log(user_id, "RABBITMQ_DISCONNECTED", "Disconnected from RabbitMQ", print_log=True)

async def main():
    """Запуск бота"""
    db = Database()
    await db.log(None, "BOT_STARTED", "Bot started and ready to process messages", print_log=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 