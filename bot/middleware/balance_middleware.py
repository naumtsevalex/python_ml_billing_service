from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery
from models.user import User
from models.balance import Balance
from db.database import Database

class BalanceMiddleware(BaseMiddleware):
    """Middleware для добавления баланса пользователя в callback-запросы"""
    
    def __init__(self, db: Database):
        self.db = db
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из контекста
        user: User = data.get("user")
        if not user:
            return await handler(event, data)
        
        # Получаем баланс пользователя
        balance = await self.db.get_balance(user.telegram_id)
        data["balance"] = balance
        
        return await handler(event, data) 