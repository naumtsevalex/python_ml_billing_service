import os
import json
import uuid
import sys
import aio_pika
from aiogram import Bot
from db.database import Database
from models.task import Task
from utils.file_utils import FileManager
import asyncio

# Настраиваем буферизацию вывода
sys.stdout.reconfigure(line_buffering=True)

def log_debug(message: str):
    """Функция для отладочного логирования"""
    print(f"[DEBUG] {message}", flush=True)
    sys.stdout.flush()

class MessageService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        self.file_manager = FileManager()
        self._connection = None

    async def _get_connection(self):
        """Получение или создание подключения к RabbitMQ"""
        try:
            if self._connection is None or self._connection.is_closed:
                self._connection = await aio_pika.connect_robust(
                    os.environ["RABBITMQ_URL"],
                    timeout=30  # 30 секунд таймаут на подключение
                )
            return self._connection
        except Exception as e:
            print(f"[ERROR] Failed to connect to RabbitMQ: {str(e)}")
            raise

    async def process_message(self, user_id: int, message_id: int, text: str | None = None, voice_file_id: str | None = None) -> dict:
        """Обработка входящего сообщения"""
        try:
            # Получаем или создаем пользователя
            user = await self.db.get_user(user_id)
            if not user:
                user = await self.db.create_user(user_id, "user")
            
            # Генерируем ID задачи
            task_id = f"{user_id}_{message_id}"
            
            # Определяем тип задачи и создаем её
            if text:
                task_type = "TTS"
                payload = text
            elif voice_file_id:
                task_type = "STT"
                payload = voice_file_id
            else:
                raise ValueError("Neither text nor voice_file_id provided")
            
            # Создаем задачу
            task = await self.db.create_task(task_id, user_id, task_type, payload)
            
            # Отправляем задачу в очередь
            await self.send_task_to_worker(task)
            
            return {
                "status": "success",
                "task_id": task_id,
                "type": task_type
            }
            
        except Exception as e:
            await self.db.log(user_id, "MESSAGE_PROCESSING_ERROR", f"e={str(e)}", print_log=True)
            raise

    async def send_task_to_worker(self, task: Task) -> dict:
        """Отправка задачи воркеру"""
        channel = None
        try:
            connection = await self._get_connection()
            channel = await connection.channel()
            
            # Генерируем correlation_id
            correlation_id = str(uuid.uuid4())
            
            # Формируем задачу
            task_data = {
                "user_id": task.user_id,
                "type": task.type,
                "task_id": task.id,
                "data": task.payload,
                "correlation_id": correlation_id,
                "file_path": None
            }
            
            # Объявляем обе очереди
            tasks_queue = await channel.declare_queue("tasks")
            results_queue = await channel.declare_queue("results")
            
            # Отправляем задачу
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(task_data).encode(),
                    correlation_id=correlation_id
                ),
                routing_key="tasks"
            )
            
            # Ждем ответ в очереди results с таймаутом
            try:
                async with asyncio.timeout(30):  # 30 секунд таймаут на ответ
                    async with results_queue.iterator() as queue_iter:
                        async for message in queue_iter:
                            if message.correlation_id == correlation_id:
                                async with message.process():
                                    result = json.loads(message.body.decode())
                                    return result
            except asyncio.TimeoutError:
                raise TimeoutError("Worker response timeout")

        except Exception as e:
            await self.db.log(task.user_id, "RABBITMQ_ERROR", f"e={str(e)}", print_log=True)
            raise
        finally:
            # Закрываем канал если он был создан
            if channel and not channel.is_closed:
                try:
                    await channel.close()
                except Exception as e:
                    print(f"[ERROR] Failed to close channel: {str(e)}")

    async def send_result_to_user(self, user_id: int, result: dict) -> None:
        """Отправка результата пользователю"""
        try:
            if result["status"] == "success":
                # Если есть файл с результатом и это был текст -> аудио (TTS)
                if "result_file" in result and result["type"] == "text":
                    # Получаем содержимое аудио файла
                    audio_content = await self.file_manager.get_audio(result["result_file"])
                    # Отправляем аудио
                    await self.bot.send_voice(user_id, audio_content)
                    await self.bot.send_message(user_id, result["message"])
                # Если это был голос -> текст (STT)
                elif result["type"] == "voice":
                    await self.bot.send_message(user_id, result["message"])
                else:
                    await self.bot.send_message(user_id, result["message"])
            else:
                await self.bot.send_message(user_id, "Произошла ошибка при обработке задачи.")
        except Exception as e:
            await self.db.log(user_id, "SEND_RESULT_ERROR", f"e={str(e)}", print_log=True)
            raise 