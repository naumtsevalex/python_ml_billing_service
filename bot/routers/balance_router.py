import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User, UserRole
from models.balance import Balance
from services.billing_service import BillingService

logger = logging.getLogger(__name__)

# Создаем роутер для баланса
balance_router = Router()

# Переменная для хранения сервиса
billing_service: BillingService = None

def setup_balance_router(billing_service_instance: BillingService):
    """Инициализация роутера с необходимыми зависимостями"""
    global billing_service
    billing_service = billing_service_instance

def get_balance_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой пополнения"""
    keyboard = []
    keyboard.append([
        InlineKeyboardButton(
            text="➕ Пополнить на 5 токенов",
            callback_data="topup_balance"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@balance_router.message(Command("balance"))
async def balance_command(message: types.Message, user: User, balance: Balance) -> None:
    """Обработчик команды /balance
    
    Отображает текущий баланс пользователя и время последнего обновления
    """
    logger.info(f"Balance command from user {user.telegram_id}")
    
    # Проверка роли пользователя
    if user.role == UserRole.BANNED:
        await message.answer("Извините, ваш аккаунт заблокирован.")
        return
    
    # Форматируем и отправляем информацию о балансе
    last_updated = balance.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    keyboard = get_balance_keyboard()
    
    await message.answer(
        f"💰 Ваш текущий баланс: {balance.balance} кредитов\n"
        f"📊 Последнее обновление: {last_updated}",
        reply_markup=keyboard
    )

@balance_router.callback_query(F.data == "topup_balance")
async def topup_balance_callback(callback: types.CallbackQuery, user: User, balance: Balance) -> None:
    """Обработчик нажатия на кнопку пополнения баланса"""
    logger.info(f"Topup balance callback from user {user.telegram_id}")
    
    # Проверка роли пользователя
    if user.role == UserRole.BANNED:
        await callback.answer("Извините, ваш аккаунт заблокирован.", show_alert=True)
        return
    
    # Проверяем текущий баланс
    # if balance.balance >= 20:
    #     await callback.answer("Ваш баланс уже больше 10 токенов!", show_alert=True)
    #     return
    
    # Пополняем баланс на 5 токенов
    new_balance = await billing_service._update_balance(user_id=user.telegram_id, amount=5)
    
    # Обновляем сообщение
    last_updated = balance.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    keyboard = get_balance_keyboard()
    
    await callback.message.edit_text(
        f"💰 Ваш текущий баланс: {new_balance.balance} кредитов\n"
        f"📊 Последнее обновление: {last_updated}",
        reply_markup=keyboard
    )
    
    await callback.answer("Баланс успешно пополнен на 5 токенов!", show_alert=True) 