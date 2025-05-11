import os
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from models.user import User, SYSTEM_USER_ID, UserRole
from models.balance import Balance, START_BALANCE
from models.log import Log
from models.task import Task, TaskStatusEnum

class Database:
    def __init__(self):
        # Создаем engine с пулом соединений
        self.engine = create_async_engine(
            os.environ["DATABASE_URL"],
            echo=True,
            pool_size=20,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True
        )
        
        # Создаем фабрику сессий
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )

    async def get_session(self) -> AsyncSession:
        """Получить новую сессию"""
        return self.async_session()
        

    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по telegram_id"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()

    async def create_user(self, telegram_id: int, username: str, role: UserRole = UserRole.CHILL_BOY) -> User:
        """Создать нового пользователя"""
        async with await self.get_session() as session:
            # Создаем пользователя
            user = User(telegram_id=telegram_id, username=username, role=role)
            session.add(user)
            await session.flush()
            
            # Создаем начальный баланс
            balance = Balance(user_id=telegram_id, balance=START_BALANCE)
            session.add(balance)
            
            await session.commit()
            return user

    async def get_balance(self, user_id: int) -> int:
        """Получить баланс пользователя"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Balance).where(Balance.user_id == user_id)
            )
            balance = result.scalar_one_or_none()
            if not balance:
                balance = Balance(user_id=user_id, balance=10)
                session.add(balance)
                await session.commit()
            return balance.balance

    async def get_balance_object(self, user_id: int) -> Balance:
        """Получить объект баланса пользователя"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Balance).where(Balance.user_id == user_id)
            )
            balance = result.scalar_one_or_none()
            if not balance:
                balance = Balance(user_id=user_id, balance=10)
                session.add(balance)
                await session.commit()
            return balance

    async def update_balance(self, user_id: int, amount: int) -> None:
        """Обновить баланс пользователя"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Balance).where(Balance.user_id == user_id)
            )
            if balance := result.scalar_one_or_none():
                balance.balance += amount
                await session.commit()

    async def log(self, user_id: Optional[int], action: str, details: Optional[str] = None, print_log: bool = False) -> None:
        """Логирование действий в БД"""
        async with await self.get_session() as session:
            log_entry = Log(
                user_id=user_id or SYSTEM_USER_ID,
                action=action,
                details=details
            )
            session.add(log_entry)
            await session.commit()
            
            if print_log:
                print(f"[LOG] {action}: {details}", flush=True)

    async def create_task(self, task_id: str, user_id: int, task_type: str, payload: str, cost: int = 0) -> Task:
        """Создать новую задачу"""
        async with await self.get_session() as session:
            task = Task(
                id=task_id,
                user_id=user_id,
                type=task_type,
                payload=payload,
                status=TaskStatusEnum.CREATED,
                cost=cost
            )
            session.add(task)
            await session.commit()
            return task

    async def update_task(
        self, 
        task_id: str, 
        status: TaskStatusEnum, 
        result: Optional[str] = None, 
        cost: Optional[int] = None
    ) -> Optional[Task]:
        """Обновить статус задачи"""
        async with await self.get_session() as session:
            query_result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            if task := query_result.scalar_one_or_none():
                task.status = status
                task.result = result
                task.cost = cost
                if status in [TaskStatusEnum.COMPLETED, TaskStatusEnum.ERROR]:
                    task.finished_at = datetime.utcnow()
                await session.commit()
                return task
            return None

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Получить задачу по ID"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == task_id)
            )
            return result.scalar_one_or_none()

    async def get_user_tasks(self, user_id: int, limit: int = 10) -> List[Task]:
        """Получить последние задачи пользователя"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(Task)
                .where(Task.user_id == user_id)
                .order_by(Task.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_users_by_role(self, role: UserRole) -> List[User]:
        """Получить список пользователей по роли"""
        async with await self.get_session() as session:
            result = await session.execute(
                select(User).where(User.role == role)
            )
            return list(result.scalars().all())
    

    async def ensure_system_user_exists(self) -> User:
        """Проверяет наличие системного пользователя и создает его при необходимости"""
        system_user = await self.get_user(SYSTEM_USER_ID)
        if not system_user:
            system_user = await self.create_user(
                telegram_id=SYSTEM_USER_ID, 
                username="system", 
                role=UserRole.SYSTEM
            )
            await self.log(SYSTEM_USER_ID, "SYSTEM_USER_CREATED", "Системный пользователь создан", print_log=True)
        return system_user 