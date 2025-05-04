import os
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models.user import User
from models.balance import Balance
from models.log import Log

class Database:
    _instance = None
    _engine = None
    _session_factory = None
    _lock = asyncio.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self):
        """Асинхронная инициализация подключения к БД"""
        async with self._lock:
            if not self._initialized:
                DATABASE_URL = os.environ["DATABASE_URL"]
                self._engine = create_async_engine(DATABASE_URL, echo=True)
                self._session_factory = sessionmaker(
                    self._engine, 
                    class_=AsyncSession, 
                    expire_on_commit=False
                )
                self.session = self._session_factory()
                self._initialized = True

    async def get_user(self, telegram_id: int) -> User | None:
        """Получить пользователя по telegram_id"""
        await self.initialize()  # Убеждаемся, что БД инициализирована
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_user(self, telegram_id: int, username: str) -> User:
        """Создать нового пользователя"""
        await self.initialize()
        user = User(telegram_id=telegram_id, username=username)
        self.session.add(user)
        await self.session.flush()
        
        # Создаем начальный баланс
        balance = Balance(user_id=telegram_id, balance=10)
        self.session.add(balance)
        
        await self.session.commit()
        return user

    async def get_balance(self, user_id: int) -> int:
        """Получить баланс пользователя"""
        await self.initialize()
        result = await self.session.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
        balance = result.scalar_one_or_none()
        return balance.balance if balance else 0

    async def update_balance(self, user_id: int, amount: int) -> None:
        """Обновить баланс пользователя"""
        await self.initialize()
        result = await self.session.execute(
            select(Balance).where(Balance.user_id == user_id)
        )
        balance = result.scalar_one_or_none()
        if balance:
            balance.balance += amount
            await self.session.commit()

    async def log(self, user_id: int | None, action: str, details: str | None = None, print_log: bool = False):
        """Логирование действий в БД и консоль (если print_log=True)"""
        await self.initialize()
        
        # Логируем в консоль если включен флаг
        if print_log:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            user_info = f"User {user_id}" if user_id else "System"
            print(f"[{timestamp}] {user_info} - {action}: {details or ''}")
        
        # Логируем в БД
        async with self.session as session:
            log_entry = Log(
                user_id=user_id,
                action=action,
                details=details
            )
            session.add(log_entry)
            await session.commit()

    async def get_user_logs(self, user_id: int, limit: int = 10) -> list[Log]:
        """Получить последние логи пользователя"""
        await self.initialize()
        result = await self.session.execute(
            select(Log)
            .where(Log.user_id == user_id)
            .order_by(Log.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all() 