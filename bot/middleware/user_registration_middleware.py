import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import types, BaseMiddleware

from db.database import Database
from models.user import User
from models.balance import Balance

# Настройка логирования
logger = logging.getLogger(__name__)

class UserRegistrationMiddleware(BaseMiddleware):
    """Middleware для проверки и создания пользователя при обработке сообщений"""
    
    def __init__(self, db: Database):
        """Инициализация middleware"""
        self.db = db
    
    async def __call__(
        self,
        handler: Callable[[types.Message, Dict[str, Any]], Awaitable[Any]],
        event: types.Message,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка каждого сообщения перед его передачей в обработчик"""
        # Проверяем наличие атрибута from_user
        if not hasattr(event, 'from_user') or event.from_user is None:
            # Для событий без пользователя просто пропускаем middleware
            return await handler(event, data)
        
        user_id = event.from_user.id
        username = event.from_user.username or event.from_user.full_name or str(user_id)
        
        # Получаем или создаем пользователя
        user: User = await self.db.get_user(user_id)
        
        if not user:
            logger.info(f"Creating new user: {user_id}, username: {username}")
            user = await self.db.create_user(user_id, username)
            await self.db.log(user_id, "USER_CREATED", f"User created: {username}", print_log=True)
        
        # Добавляем пользователя в контекст для обработчиков
        data["user"] = user
        
        # Получаем объект баланса через метод БД
        # Этот метод создаст баланс, если его нет
        balance: Balance = await self.db.get_balance_object(user_id)
        data["balance"] = balance
        
        # Безопасно получаем тип контента
        content_type = "unknown"
        if hasattr(event, 'content_type'):
            content_type = event.content_type
        
        # Записываем в лог обращение к боту
        await self.db.log(user_id, "BOT_INTERACTION", f"Interaction: {content_type}", print_log=False)
        
        # Вызываем следующий обработчик
        return await handler(event, data) 