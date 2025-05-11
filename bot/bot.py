import os
import logging
import asyncio
import sys
from typing import Any, Optional
from datetime import datetime
import uuid

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import BotCommand, BotCommandScopeDefault

from db.database import Database
from services.bot_service import BotService
from services.client_rabbitmq_service import ClientRabbitMQService
from services.billing_service import BillingService

from models.user import SYSTEM_USER_ID, UserRole, User
from models.balance import Balance
from models.task import Task

from middleware import UserRegistrationMiddleware, BalanceMiddleware
from routers.joke_router import joke_router, setup_joke_router
from routers.balance_router import balance_router, setup_balance_router

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
client_rabbitmq_service = ClientRabbitMQService()
bot_service = BotService(bot)
billing_service = BillingService()

# Создаем роутеры для организации обработчиков
main_router = Router()
message_router = Router()

# Регистрируем middleware
main_router.message.middleware(UserRegistrationMiddleware(db))
message_router.message.middleware(UserRegistrationMiddleware(db))
joke_router.message.middleware(UserRegistrationMiddleware(db))
balance_router.message.middleware(UserRegistrationMiddleware(db))

# Регистрируем middleware для callback-запросов
# balance_router.callback_query.middleware(BalanceMiddleware(db))
balance_router.callback_query.middleware(UserRegistrationMiddleware(db))

# Инициализируем роутеры со всеми зависимостями
setup_joke_router(
    db_instance=db,
    client_rabbitmq_service_instance=client_rabbitmq_service,
    bot_service_instance=bot_service,
    billing_service_instance=billing_service
)

setup_balance_router(billing_service_instance=billing_service)

@main_router.message(CommandStart())
async def command_start_handler(message: types.Message) -> Any:
    """Обработчик команды /start"""
    logger.info(f"User {message.from_user.id} started bot")
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n\n"
        f"Я бот для работы с текстом и голосом. Вот что я умею:\n\n"
        f"🎭 /joke - расскажу случайный анекдот\n"
        f"🎙️ /joke_voice - расскажу анекдот голосом\n\n"
        f"💰 /balance - покажу твой текущий баланс\n"
        f"❓ /help - подробная справка по командам\n\n"
        f"Начни с команды /joke, чтобы получить свой первый анекдот! 😊"
    )

@main_router.message(Command("help"))
async def help_command(message: types.Message) -> None:
    """Обработчик команды /help
    
    Отображает список доступных команд и их описание
    """
    logger.info(f"Help command from user {message.from_user.id}")
    
    help_text = (
        "🤖 <b>Добро пожаловать в справку!</b>\n\n"
        "Вот что я умею:\n\n"
        "🚀 /start - Начать общение со мной\n"
        "❓ /help - Показать эту справку\n\n"
        "🎭 <b>Анекдоты:</b>\n"
        "   /joke - Расскажу случайный анекдот\n"
        "   /joke_voice - Расскажу анекдот голосом\n\n"
        "💰 <b>Баланс:</b>\n"
        "   /balance - Покажу твой текущий баланс\n\n"
        "💡 <b>Совет:</b> Начни с команды /joke, чтобы получить свой первый анекдот!\n\n"
        "Если у тебя есть вопросы или предложения - пиши мне! 😊"
    )
    
    await message.answer(help_text, parse_mode="HTML")

async def set_bot_commands() -> None:
    """Установка команд бота для отображения в интерфейсе Telegram"""
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Показать справку"),
        BotCommand(command="balance", description="Показать баланс"),
        BotCommand(command="joke", description="Получить случайный анекдот"),
        BotCommand(command="joke_voice", description="Получить озвученный анекдот"),
    ]
    await bot.set_my_commands(commands)

async def main() -> None:
    """Точка входа в приложение"""
    logger.info("Starting bot...")
    
    # Убеждаемся, что системный пользователь существует
    await db.ensure_system_user_exists()
    
    # Регистрируем старт в базе
    await db.log(SYSTEM_USER_ID, "BOT_STARTED", "Bot started")
    
    # Регистрируем роутеры
    dp.include_router(main_router)
    dp.include_router(message_router)
    dp.include_router(joke_router)
    dp.include_router(balance_router)
    
    # Установка команд бота (будут видны в интерфейсе Telegram)
    await set_bot_commands()
    
    # Получаем всех админов из базы
    admins = await db.get_users_by_role(UserRole.ADMIN)
    logger.info(f"[main] {admins=}")

    async def notify_admin(admin):
        await bot.send_message(
            admin.telegram_id,
            "🤖 Бот успешно запущен!\n"
            f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    await asyncio.gather(*(notify_admin(admin) for admin in admins))
    
    # Запускаем поллинг
    logger.info("Starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем бота
    asyncio.run(main())
    