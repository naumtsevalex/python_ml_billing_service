import os
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models.user import User
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

    async def create_task(self, task_id: str, user_id: int, task_type: str, payload: str) -> Task:
        """Создать новую задачу"""
        await self.initialize()
        try:
            async with self.session as session:
                task = Task(
                    id=task_id,
                    user_id=user_id,
                    type=task_type,
                    payload=payload,
                    status="created"
                )
                session.add(task)
                await self.log(user_id, "TASK_CREATED", f"Creating task {task_id} of type {task_type}", print_log=True)
                await session.commit()
                await self.log(user_id, "TASK_CREATED_SUCCESS", f"Task {task_id} created successfully", print_log=True)
                return task
        except Exception as e:
            import traceback
            error_msg = f"Error creating task: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERROR] Database.create_task error:\n{error_msg}")
            await self.log(user_id, "TASK_CREATED_ERROR", error_msg, print_log=True)
            raise

    async def update_task(self, task_id: str, status: str, result: str | None = None, cost: int | None = None) -> Task | None:
        """Обновить статус задачи"""
        await self.initialize()
        try:
            query_result = await self.session.execute(
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
                await self.log(task.user_id, "TASK_UPDATED", f"Updating task {task_id} to status {status}", print_log=True)
                await self.session.commit()
                await self.log(task.user_id, "TASK_UPDATED_SUCCESS", f"Task {task_id} updated successfully", print_log=True)
            else:
                error_msg = f"Task {task_id} not found"
                print(f"[ERROR] Database.update_task error: {error_msg}")
                await self.log(None, "TASK_UPDATE_ERROR", error_msg, print_log=True)
            return task
        except Exception as e:
            import traceback
            error_msg = f"Error updating task {task_id}: {str(e)}\n{traceback.format_exc()}"
            print(f"[ERROR] Database.update_task error:\n{error_msg}")
            await self.log(None, "TASK_UPDATE_ERROR", error_msg, print_log=True)
            raise

    async def get_task(self, task_id: str) -> Task | None:
        """Получить задачу по ID"""
        await self.initialize()
        result = await self.session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_user_tasks(self, user_id: int, limit: int = 10) -> list[Task]:
        """Получить последние задачи пользователя"""
        await self.initialize()
        result = await self.session.execute(
            select(Task)
            .where(Task.user_id == user_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all() 