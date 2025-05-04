import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from db import SessionLocal
from models.user import User
from models.balance import Balance
from models.log import Log
from sqlalchemy import select
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

async def log_action(user_id: int, action: str, details: str = None):
    async with SessionLocal() as session:
        log = Log(
            user_id=user_id,
            action=action,
            details=details,
            created_at=datetime.utcnow()
        )
        session.add(log)
        await session.commit()

async def register_user(user_id: int, username: str):
    async with SessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(telegram_id=user_id, username=username)
            session.add(user)
            await session.flush()
            balance = Balance(user_id=user_id, balance=10)
            session.add(balance)
            await session.commit()
            await log_action(user_id, "register", f"username={username}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await register_user(message.from_user.id, message.from_user.username)
    await log_action(message.from_user.id, "start", "User sent /start")
    await message.answer("OK")

@dp.message()
async def echo(message: types.Message):
    await register_user(message.from_user.id, message.from_user.username)
    await log_action(message.from_user.id, "message", f"text={message.text}")
    await message.answer("OK")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 