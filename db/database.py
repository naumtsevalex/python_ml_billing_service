import os
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models.user import User, SYSTEM_USER_ID
from models.balance import Balance
from models.log import Log
from models.task import Task

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
                
                # Проверяем существование системного пользователя
                system_user = await self.get_user(SYSTEM_USER_ID, skip_init=True)
                if not system_user:
                    # Создаем системного пользователя
                    await self.create_user(SYSTEM_USER_ID, "system", skip_init=True)
                    print("[INFO] System user created successfully")
                
                self._initialized = True

    async def _get_session(self) -> AsyncSession:
        """Получение новой сессии"""
        if not self._initialized:
            await self.initialize()
        return self._session_factory()

    async def get_user(self, telegram_id: int, skip_init: bool = False) -> User | None:
        """Получить пользователя по telegram_id"""
        async with await self._get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    async def create_user(self, telegram_id: int, username: str, skip_init: bool = False) -> User:
        """Создать нового пользователя"""
        async with await self._get_session() as session:
            user = User(telegram_id=telegram_id, username=username)
            session.add(user)
            await session.flush()
            
            # Создаем начальный баланс
            balance = Balance(user_id=telegram_id, balance=10)
            session.add(balance)
            
            await session.commit()
            return user

    async def get_balance(self, user_id: int, skip_init: bool = False) -> int:
        """Получить баланс пользователя"""
        async with await self._get_session() as session:
            result = await session.execute(
                select(Balance).where(Balance.user_id == user_id)
            )
            balance = result.scalar_one_or_none()
            if not balance:
                # Создаем начальный баланс для нового пользователя
                balance = Balance(user_id=user_id, balance=10)
                session.add(balance)
                await session.commit()
            return balance.balance

    async def update_balance(self, user_id: int, amount: int, skip_init: bool = False) -> None:
        """Обновить баланс пользователя"""
        async with await self._get_session() as session:
            result = await session.execute(
                select(Balance).where(Balance.user_id == user_id)
            )
            balance = result.scalar_one_or_none()
            if balance:
                balance.balance += amount
                await session.commit()

    async def log(self, user_id: int | None, action: str, details: str | None = None, print_log: bool = False, skip_init: bool = False):
        """Логирование действий в БД и консоль (если print_log=True)"""
        # Если user_id не указан, используем системного пользователя
        if user_id is None:
            user_id = SYSTEM_USER_ID
        
        # Логируем в консоль если включен флаг
        if print_log:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            user_info = f"User {user_id}" if user_id != SYSTEM_USER_ID else "System"
            print(f"[{timestamp}] {user_info} - {action}: {details or ''}")
        
        try:
            async with await self._get_session() as session:
                # Логируем в БД
                log_entry = Log(
                    user_id=user_id,
                    action=action,
                    details=details
                )
                session.add(log_entry)
                await session.commit()
        except Exception as e:
            print(f"[ERROR] Database.log error: e={str(e)}")

    async def get_user_logs(self, user_id: int, limit: int = 10) -> list[Log]:
        """Получить последние логи пользователя"""
        async with await self._get_session() as session:
            result = await session.execute(
                select(Log)
                .where(Log.user_id == user_id)
                .order_by(Log.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()

    async def create_task(self, task_id: str, user_id: int, task_type: str, payload: str) -> Task:
        """Создать новую задачу"""
        async with await self._get_session() as session:
            try:
                task = Task(
                    id=task_id,
                    user_id=user_id,
                    type=task_type,
                    payload=payload,
                    status="created"
                )
                session.add(task)
                await session.commit()
                return task
            except Exception as e:
                print(f"[ERROR] Database.create_task error: e={str(e)}")
                raise

    async def update_task(self, task_id: str, status: str, result: str | None = None, cost: int | None = None) -> Task | None:
        """Обновить статус задачи"""
        async with await self._get_session() as session:
            try:
                query_result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = query_result.scalar_one_or_none()
                if task:
                    task.status = status
                    if result is not None:
                        task.result = result
                    if cost is not None:
                        task.cost = cost
                    if status in ["completed", "error"]:
                        task.finished_at = datetime.utcnow()
                    await session.commit()
                return task
            except Exception as e:
                print(f"[ERROR] Database.update_task error: e={str(e)}")
                raise

    async def get_task(self, task_id: str) -> Task | None:
        """Получить задачу по ID"""
        async with await self._get_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()

    async def get_user_tasks(self, user_id: int, limit: int = 10) -> list[Task]:
        """Получить последние задачи пользователя"""
        async with await self._get_session() as session:
            result = await session.execute(
                select(Task)
                .where(Task.user_id == user_id)
                .order_by(Task.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all() 