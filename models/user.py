from sqlalchemy import BigInteger, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from enum import Enum
from .base import Base

# ID системного пользователя для системных логов
SYSTEM_USER_ID = -1

class UserRole(str, Enum):
    """Роли пользователей"""
    ADMIN = "ADMIN"  # Администратор системы
    CHILL_BOY = "CHILL_BOY"  # Обычный пользователь
    BANNED = "BANNED"  # Заблокированный пользователь

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.CHILL_BOY, nullable=False)
