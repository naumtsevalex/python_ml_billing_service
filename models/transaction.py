from sqlalchemy import Integer, String, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    type: Mapped[str] = mapped_column(String)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    task_id: Mapped[str] = mapped_column(String, nullable=True)