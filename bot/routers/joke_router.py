import logging
import uuid
from aiogram import Router, types
from aiogram.filters import Command
from models.user import User
from models.task import Task
from services.joke_service import JokeService
from services.ai_service import AIService
from services.task_service import TaskService
from services.client_rabbitmq_service import ClientRabbitMQService
from services.bot_service import BotService
from services.billing_service import BillingService
from db.database import Database

logger = logging.getLogger(__name__)

# Создаем роутер для анекдотов
joke_router = Router()

# Переменные для хранения сервисов
db: Database = None
client_rabbitmq_service: ClientRabbitMQService = None
joke_service: JokeService = None
bot_service: BotService = None
billing_service: BillingService = None

def generate_task_id(user_id: int, message_id: int) -> str:
    """Генерирует уникальный идентификатор задачи в формате user_id_message_id_uuid"""
    return f"{user_id}_{message_id}_{uuid.uuid4()}"

def setup_joke_router(
    db_instance: Database,
    client_rabbitmq_service_instance: ClientRabbitMQService,
    bot_service_instance: BotService,
    billing_service_instance: BillingService
):
    """Инициализация роутера со всеми необходимыми зависимостями"""
    global db, client_rabbitmq_service, joke_service, bot_service, billing_service
    db = db_instance
    client_rabbitmq_service = client_rabbitmq_service_instance
    bot_service = bot_service_instance
    billing_service = billing_service_instance
    joke_service = JokeService(db)  # Создаем joke_service после инициализации db

# ================================

@joke_router.message(Command("joke"))
async def joke_handler(message: types.Message, user: User):
    """Обработчик команды /joke"""
    logger.info(f"Joke command from user {user.telegram_id}")
    
    joke = await joke_service.get_random_joke()
    if not joke:
        await message.answer("Извините, у меня закончились анекдоты 😢")
        return
    
    # Генерируем task_id
    task_id = generate_task_id(user.telegram_id, message.message_id)
    
    # достать текст любого анекдота будет стоит 1 токен
    task = await db.create_task(task_id=task_id, user_id=user.telegram_id, task_type="just_text_form_db", payload=joke.text, 
                                cost=1) # hardcoded bad(
    task, (ok, str_report) = await billing_service.charge_for_task(task_id=task_id)

    res = f"💰 Стоимость анекдота: {task.cost} токен\n{joke.text}"
    await message.answer(res)

@joke_router.message(Command("joke_voice"))
async def joke_voice_handler(
    message: types.Message, 
    user: User
):
    """Обработчик команды /joke_voice"""
    logger.info(f"Joke voice command from user {user.telegram_id}")
    
    joke = await joke_service.get_random_joke()
    if not joke:
        await message.answer("Извините, у меня закончились анекдоты 😢")
        return
    
    # Генерируем task_id
    task_id = generate_task_id(user.telegram_id, message.message_id)
    
    # Отправляем в очередь
    result = await client_rabbitmq_service.process_message(
        task_id=task_id,
        user_id=user.telegram_id,
        message_id=message.message_id,
        text=joke.text
    )

    logger.info(f"[text_handler] Final result from user {user.telegram_id}: {result=}")
    await bot_service.send_result_to_user(user.telegram_id, result)
    
    task, (ok, str_report) = await billing_service.charge_for_task(task_id=task_id)

    res = f"💰 Стоимость анекдота: {task.cost} токенов\n<tg-spoiler>{joke.text}</tg-spoiler>"
    await message.answer(res, parse_mode="HTML") 