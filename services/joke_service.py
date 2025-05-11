from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from models.joke import Joke
import random
from sqlalchemy import func, select

class JokeService:
    def __init__(self, db):
        self.db = db
    
    async def get_random_joke(self) -> Joke:
        """Получить случайный анекдот"""
        session = self.db.async_session()
        async with session:
            result = await session.execute(
                select(Joke).order_by(func.random()).limit(1)
            )
            return result.scalar_one_or_none()
    
    async def get_joke_by_category(self, category: str) -> Joke:
        """Получить случайный анекдот по категории"""
        session = self.db.async_session()
        async with session:
            result = await session.execute(
                select(Joke).filter(Joke.category == category).order_by(func.random()).limit(1)
            )
            return result.scalar_one_or_none()
    
    async def add_joke(self, text: str, category: str = None) -> Joke:
        """Добавить новый анекдот"""
        session = self.db.async_session()
        async with session:
            joke = Joke(text=text, category=category)
            session.add(joke)
            await session.commit()
            await session.refresh(joke)
            return joke