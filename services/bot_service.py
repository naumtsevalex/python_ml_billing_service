import os
import json
import uuid
import sys
import aio_pika
from aiogram import Bot
from aiogram.types import BufferedInputFile
from db.database import Database
from models.task import Task, TaskStatusEnum
from models.task_types import TaskTypeEnum, RabbitMQQueueEnum
from utils.file_utils import FileManager
from services.client_rabbitmq_service import ClientRabbitMQService, log_debug
import asyncio

# Настраиваем буферизацию вывода
sys.stdout.reconfigure(line_buffering=True)

class BotService:
    """Сервис для обработки сообщений бота и работы с пользователями"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        self.file_manager = FileManager()
        self.rabbitmq_service = ClientRabbitMQService()

    async def send_result_to_user(self, user_id: int, result: dict) -> None:
        """Отправка результата пользователю"""
        log_debug(f"Обработка результата для пользователя {user_id}: {result}")
        
        # Если статус ошибка, отправляем сообщение об ошибке
        if result["status"] != "success":
            await self.bot.send_message(user_id, result["message"])
            return
        
        # Получаем детальную информацию о задаче из базы данных
        task_id = result["task_id"]
        task = await self.db.get_task(task_id)
        
        if not task:
            log_debug(f"Задача {task_id} не найдена в базе данных")
            await self.bot.send_message(user_id, "Ошибка: задача не найдена в базе данных")
            return
            
        if task.status != TaskStatusEnum.COMPLETED:
            log_debug(f"Задача {task_id} не завершена: {task.status}")
            await self.bot.send_message(user_id, f"Задача в процессе обработки. Статус: {task.status}")
            return
        
        # Получаем информацию о стоимости из базы данных
        cost = task.cost
        log_debug(f"Стоимость задачи {task_id}: {cost}")
            
        # В зависимости от типа задачи обрабатываем результат
        task_type = task.type
        
        if task_type == TaskTypeEnum.TEXT:
            # Это был TTS запрос (преобразование текста в аудио)
            result_file = task.result
            log_debug(f"Получение аудиофайла из {result_file}")
            audio_content = await self.file_manager.get_audio(result_file)
            
            # Создаем InputFile из байтов
            filename = os.path.basename(result_file)
            voice_file = BufferedInputFile(audio_content, filename=filename)
            
            # Отправляем аудио и сообщение
            log_debug(f"Отправка голосового сообщения пользователю {user_id}")
            await self.bot.send_voice(user_id, voice_file)
            await self.bot.send_message(user_id, "Текст успешно преобразован в речь")
            
        elif task_type == TaskTypeEnum.VOICE:
            # Это был STT запрос (преобразование голоса в текст)
            text_result = task.result
            log_debug(f"Отправка распознанного текста пользователю {user_id}")
            await self.bot.send_message(user_id, text_result)
        
        # Отправляем информацию о стоимости
        await self.bot.send_message(user_id, f"💰 Стоимость: {cost} кредитов")