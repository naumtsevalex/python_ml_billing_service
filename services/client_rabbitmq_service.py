import os
import json
import uuid
import sys
import aio_pika
from aiogram import Bot
from aiogram.types import BufferedInputFile
from db.database import Database
from models.task import TaskStatusEnum
from models.task_types import TaskTypeEnum, RabbitMQQueueEnum
from utils.file_utils import FileManager
from utils.utils import log_debug
import asyncio

# Настраиваем буферизацию вывода
sys.stdout.reconfigure(line_buffering=True)


class ClientRabbitMQService:
    """Сервис для работы с RabbitMQ и выполнения RPC запросов"""
    
    def __init__(self):
        self._connection = None
        self.db = Database()
        self.file_manager = FileManager()

    async def _get_connection(self):
        """Получение или создание подключения к RabbitMQ"""
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(
                os.environ["RABBITMQ_URL"],
                timeout=30  # 30 секунд таймаут на подключение
            )
        return self._connection
    
    async def send_rpc_request(self, routing_key: str, data: dict) -> dict:
        """Отправка RPC запроса и ожидание ответа"""
        # Получаем соединение
        connection = await self._get_connection()
        channel = await connection.channel()
        
        # Создаем временную эксклюзивную очередь для ответа
        # Она удалится автоматически после закрытия соединения
        callback_queue = await channel.declare_queue("", exclusive=True)
        
        # Генерируем correlation_id для отслеживания запроса
        correlation_id = str(uuid.uuid4())
        
        # Добавляем correlation_id в данные запроса
        data["correlation_id"] = correlation_id
        
        log_debug(f"Отправка RPC запроса в очередь {routing_key}")
        
        # Отправляем запрос, указав reply_to на временную очередь
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(data).encode(),
                correlation_id=correlation_id,
                reply_to=callback_queue.name
            ),
            routing_key=routing_key
        )
        
        log_debug(f"Ожидание ответа в очереди {callback_queue.name}")
        
        # Ожидаем ответ из временной очереди
        async with callback_queue.iterator() as queue_iter:
            async for message in queue_iter:
                # Проверяем correlation_id чтобы получить только наш ответ
                if message.correlation_id == correlation_id:
                    await message.ack()
                    result = json.loads(message.body.decode())
                    log_debug(f"Получен ответ на запрос")
                    return result
                    
                # Игнорируем чужие сообщения
                await message.ack()

    async def process_message(self, user_id: int, message_id: int, text: str | None = None, voice_file_id: str | None = None) -> dict:
        """Обработка входящего сообщения"""
        # Пользователь уже создан через middleware, нет необходимости проверять
        
        # Генерируем ID задачи
        task_id = f"{user_id}_{message_id}"
        
        # Определяем тип задачи и создаем её
        if text:
            task_type = TaskTypeEnum.TEXT
            payload = text
        elif voice_file_id:
            task_type = TaskTypeEnum.VOICE
            payload = voice_file_id
        else:
            raise ValueError("Neither text nor voice_file_id provided")
        
        # Создаем задачу
        task = await self.db.create_task(task_id, user_id, task_type, payload)
        
        # Отправляем задачу в очередь
        task_data = {
            "user_id": task.user_id,
            "type": task.type,
            "task_id": task.id,
            "data": task.payload
        }
        
        log_debug(f"Отправка задачи {task_id} на обработку")
        
        # Отправляем RPC запрос воркеру и получаем результат
        result = await self.send_rpc_request(
            routing_key=RabbitMQQueueEnum.TASK_PROCESSING,
            data=task_data
        )
        
        log_debug(f"Получен результат обработки задачи {task_id}: {result}")
        
        # Проверяем, что результат содержит нужные поля
        if not result or "status" not in result:
            # Если результат некорректный, возвращаем ошибку
            return {
                "status": "error",
                "message": "Получен некорректный результат от воркера",
                "task_id": task_id,
                "type": task_type
            }
        
        # Добавляем ID задачи и тип, если их нет в результате
        if "task_id" not in result:
            result["task_id"] = task_id
            
        return result 