import os
import json
import asyncio
import aio_pika
import uuid
from db.database import Database
from services.task_service import TaskService
from models.user import SYSTEM_USER_ID
from models.task_types import RabbitMQQueueEnum
from utils.utils import log_debug

# Инициализация сервисов
task_service = TaskService()

async def main():
    """Основная функция воркера"""
    db = Database()
    
    # Подключаемся к RabbitMQ
    await db.log(SYSTEM_USER_ID, "WORKER_STARTING", "Starting worker", print_log=True)
    connection = await aio_pika.connect_robust(os.environ["RABBITMQ_URL"])
    await db.log(SYSTEM_USER_ID, "WORKER_CONNECTED", "Connected to RabbitMQ", print_log=True)
    
    # Создаем канал
    channel = await connection.channel()
    await db.log(SYSTEM_USER_ID, "WORKER_CHANNEL", "Created channel", print_log=True)
    
    # Объявляем очередь задач
    tasks_queue = await channel.declare_queue(RabbitMQQueueEnum.TASK_PROCESSING)
    await db.log(SYSTEM_USER_ID, "WORKER_QUEUES", f"Declared queue: {RabbitMQQueueEnum.TASK_PROCESSING}", print_log=True)
    
    # Обработка сообщений
    async with tasks_queue.iterator() as queue_iter:
        await db.log(SYSTEM_USER_ID, "WORKER_READY", "Ready to process tasks", print_log=True)
        async for message in queue_iter:
            async with message.process():
                # Получаем задачу
                task = json.loads(message.body.decode())
                await db.log(SYSTEM_USER_ID, "TASK_RECEIVED", f"Received task: {task}", print_log=True)
                
                # Обрабатываем задачу
                result = await task_service.process_task(task)
                
                # Проверяем наличие адреса для ответа
                reply_to = message.reply_to
                if not reply_to:
                    await db.log(SYSTEM_USER_ID, "ERROR", "No reply_to in message, cannot send result", print_log=True)
                    continue
                
                # Отправляем результат в указанную очередь ответа
                await channel.default_exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(result).encode(),
                        correlation_id=message.correlation_id
                    ),
                    routing_key=reply_to
                )
                await db.log(SYSTEM_USER_ID, "RESULT_SENT", f"Result sent to {reply_to} queue", print_log=True)

if __name__ == "__main__":
    asyncio.run(main()) 