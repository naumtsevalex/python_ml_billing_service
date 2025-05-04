from sqlalchemy import String, Integer, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .base import Base

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    type: Mapped[str] = mapped_column(String)
    payload: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    result: Mapped[str] = mapped_column(String, nullable=True)
    cost: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
