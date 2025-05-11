import requests
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from models.joke import Joke
from services.joke_service import JokeService
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import os
import time
import random
import asyncio
from requests.exceptions import RequestException

def parse_anekdot_ru():
    """Парсинг анекдотов с anekdot.ru"""
    try:
        url = "https://www.anekdot.ru/random/anekdot/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        jokes = []
        for joke in soup.find_all('div', class_='text'):
            jokes.append({
                'text': joke.text.strip(),
                'category': 'general'
            })
        
        return jokes
    except RequestException as e:
        print(f"Ошибка при запросе к anekdot.ru: {e}")
        return []

def parse_anekdot_me():
    """Парсинг анекдотов с anekdot.me"""
    try:
        url = "https://anekdot.me/random"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        jokes = []
        for joke in soup.find_all('div', class_='anekdot'):
            jokes.append({
                'text': joke.text.strip(),
                'category': 'general'
            })
        
        return jokes
    except RequestException as e:
        print(f"Ошибка при запросе к anekdot.me: {e}")
        return []

def parse_anekdotov_net():
    """Парсинг анекдотов с anekdotov.net"""
    try:
        url = "https://anekdotov.net/anekdot/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        jokes = []
        for joke in soup.find_all('div', class_='anekdot'):
            jokes.append({
                'text': joke.text.strip(),
                'category': 'general'
            })
        
        return jokes
    except RequestException as e:
        print(f"Ошибка при запросе к anekdotov.net: {e}")
        return []

async def save_jokes(jokes: list[dict], joke_service: JokeService):
    """Сохранение анекдотов в базу через JokeService"""
    for joke_data in jokes:
        try:
            await joke_service.add_joke(text=joke_data['text'], category=joke_data['category'])
        except Exception as e:
            print(f"Ошибка при сохранении анекдота: {e}")

async def main():
    # Инициализация движка и сессии
    database_url = "postgresql+asyncpg://postgres:postgres@localhost:5433/billing"
    engine = create_async_engine(
        database_url,
        echo=True,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True
    )
    
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    
    # Список функций парсинга
    parsers = [
        parse_anekdot_ru,
        parse_anekdot_me,
        parse_anekdotov_net
    ]
    
    total_jokes = 0
    async with async_session() as session:
        joke_service = JokeService(session)
        
        for parser in parsers:
            try:
                print(f"Парсинг с помощью {parser.__name__}...")
                jokes = parser()
                if jokes:
                    await save_jokes(jokes, joke_service)
                    total_jokes += len(jokes)
                    print(f"Сохранено {len(jokes)} анекдотов")
                else:
                    print("Не удалось получить анекдоты")
                
                # Делаем паузу между запросами
                await asyncio.sleep(random.uniform(1, 3))
            except Exception as e:
                print(f"Ошибка при парсинге {parser.__name__}: {e}")
                await session.rollback()
    
    print(f"\nВсего сохранено {total_jokes} анекдотов")
    await engine.dispose()

def test():
    jokes = parse_anekdot_me()
    print(jokes)

if __name__ == "__main__":
    asyncio.run(main())
    # test()
    
    # set -a && source .env
    # docker-compose down && docker-compose up -d --build
    # PYTHONPATH=. python3 scripts/parse_jokes.py