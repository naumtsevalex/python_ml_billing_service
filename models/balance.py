from sqlalchemy import Integer, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .base import Base

START_BALANCE = 20

class Balance(Base):
    __tablename__ = "balances"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), primary_key=True)
    balance: Mapped[int] = mapped_column(Integer, default=START_BALANCE)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)