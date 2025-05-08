import os
import logging
import asyncio
import sys
from typing import Any, Optional
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import BotCommand, BotCommandScopeDefault

from db.database import Database
from services.message_service import BotService
from models.user import SYSTEM_USER_ID, UserRole, User
from models.balance import Balance
from middleware import UserRegistrationMiddleware

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
message_service = BotService(bot)

# Создаем роутеры для организации обработчиков
main_router = Router()
finance_router = Router()
message_router = Router()

# Регистрируем middleware
# dp.update.middleware(UserRegistrationMiddleware())
main_router.message.middleware(UserRegistrationMiddleware())
finance_router.message.middleware(UserRegistrationMiddleware())
message_router.message.middleware(UserRegistrationMiddleware())


@main_router.message(CommandStart())
async def command_start_handler(message: types.Message) -> Any:
    """Обработчик команды /start"""
    logger.info(f"User {message.from_user.id} started bot")
    await message.answer(
        f"👋 Привет, {message.from_user.full_name}!\n"
        f"Я бот для обработки сообщений.\n"
        f"Твой ID: <code>{message.from_user.id}</code>\n\n"
        f"Используй /help для получения списка доступных команд."
    )

@main_router.message(Command("help"))
async def help_command(message: types.Message) -> None:
    """Обработчик команды /help
    
    Отображает список доступных команд и их описание
    """
    logger.info(f"Help command from user {message.from_user.id}")
    
    help_text = (
        "📋 <b>Доступные команды:</b>\n\n"
        "/start - Начать взаимодействие с ботом\n"
        "/help - Показать этот список команд\n"
        "/balance - Проверить ваш текущий баланс\n\n"
        "<b>Возможности бота:</b>\n"
        "• Отправьте текстовое сообщение для преобразования его в аудио (TTS)\n"
        "• Отправьте голосовое сообщение для преобразования его в текст (STT)\n"
        "• Напишите 'баланс' для проверки вашего счета"
    )
    
    await message.answer(help_text, parse_mode="HTML")

@finance_router.message(Command("balance"))
async def balance_command(message: types.Message, user: User, balance: Balance) -> None:
    """Обработчик команды /balance
    
    Отображает текущий баланс пользователя и время последнего обновления
    """
    logger.info(f"Balance command from user {message.from_user.id}")
    
    # Проверка роли пользователя
    if user.role == UserRole.BANNED:
        await message.answer("Извините, ваш аккаунт заблокирован.")
        return
    
    # Форматируем и отправляем информацию о балансе
    last_updated = balance.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    await message.answer(
        f"💰 Ваш текущий баланс: {balance.balance} кредитов\n"
        f"📊 Последнее обновление: {last_updated}"
    )

@message_router.message(F.voice)
async def voice_handler(message: types.Message, user: User, balance: Balance) -> None:
    """Обработчик голосовых сообщений"""
    logger.info(f"Processing voice message from user {message.from_user.id}")
    
    # Проверка роли пользователя
    if user.role == UserRole.BANNED:
        await message.answer("Извините, ваш аккаунт заблокирован.")
        return
    
    # Проверка баланса для голосовых сообщений
    if balance.balance <= 0:  # Предполагаем минимальный баланс для Voice->Text
        await message.answer(f"⚠️ Недостаточно средств. Ваш баланс: {balance.balance} кредитов.")
        return

    result = await message_service.process_message(
        user_id=message.from_user.id,
        message_id=message.message_id,
        voice_file_id=message.voice.file_id
    )
    await message_service.send_result_to_user(message.from_user.id, result)

@message_router.message(F.text)
async def text_handler(message: types.Message, user: User, balance: Balance) -> None:
    """Обработчик текстовых сообщений"""
    logger.info(f"Processing text message from user {message.from_user.id}: {message.text}")
    
    # Проверка роли пользователя
    if user.role == UserRole.BANNED:
        await message.answer("Извините, ваш аккаунт заблокирован.")
        return
    
    if balance.balance <= 0:  # Предполагаем минимальный баланс для Text->Voice
        await message.answer(f"⚠️ Недостаточно средств. Ваш баланс: {balance.balance} кредитов.")
        return
    
    result = await message_service.process_message(
        user_id=message.from_user.id,
        message_id=message.message_id,
        text=message.text
    )
    logger.info(f"[text_handler] Final result from user {message.from_user.id}: {result=}")

    await message_service.send_result_to_user(message.from_user.id, result)

async def set_bot_commands() -> None:
    """Установка команд бота для отображения в интерфейсе Telegram"""
    commands = [
        BotCommand(command="start", description="Начать взаимодействие с ботом"),
        BotCommand(command="help", description="Показать список доступных команд"),
        BotCommand(command="balance", description="Проверить ваш текущий баланс")
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    logger.info("Bot commands have been set successfully")

async def main() -> None:
    """Точка входа в приложение"""
    logger.info("Starting bot...")
    
    # Убеждаемся, что системный пользователь существует
    await db.ensure_system_user_exists()
    
    # Регистрируем старт в базе
    await db.log(SYSTEM_USER_ID, "BOT_STARTED", "Bot started")
    
    # Регистрируем роутеры
    dp.include_router(main_router)
    dp.include_router(finance_router)
    dp.include_router(message_router)
    
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
    
    # Запускаем поллинг (как в рабочем эхо-боте)
    logger.info("Starting polling...")
    await dp.start_polling(bot)
    

if __name__ == "__main__":
    # Запускаем бота
    asyncio.run(main())
    