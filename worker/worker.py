import os
import json
import asyncio
import aio_pika
import uuid
from db.database import Database
from services.task_service import TaskService

# Инициализация сервисов
task_service = TaskService()

async def main():
    """Основная функция воркера"""
    db = Database()
    
    try:
        # Подключаемся к RabbitMQ
        await db.log(0, "WORKER_STARTING", "Starting worker", print_log=True)
        connection = await aio_pika.connect_robust(os.environ["RABBITMQ_URL"])
        await db.log(0, "WORKER_CONNECTED", "Connected to RabbitMQ", print_log=True)
        
        # Создаем канал
        channel = await connection.channel()
        await db.log(0, "WORKER_CHANNEL", "Created channel", print_log=True)
        
        # Объявляем очередь
        queue = await channel.declare_queue("tasks", routing_key="tasks")
        await db.log(0, "WORKER_QUEUE", "Declared queue: tasks", print_log=True)
        
        # Обработка сообщений
        async with queue.iterator() as queue_iter:
            await db.log(0, "WORKER_READY", "Ready to process tasks", print_log=True)
            async for message in queue_iter:
                async with message.process():
                    try:
                        # Получаем задачу
                        task = json.loads(message.body.decode())
                        await db.log(0, "TASK_RECEIVED", f"Received task of type: {task['type']} with task_id: {task['task_id']}", print_log=True)
                        
                        # Обрабатываем задачу
                        result = await task_service.process_task(task)
                        
                        # Отправляем результат
                        if message.reply_to:
                            await channel.default_exchange.publish(
                                aio_pika.Message(
                                    body=json.dumps(result).encode(),
                                    correlation_id=message.correlation_id
                                ),
                                routing_key=message.reply_to
                            )
                            await db.log(0, "RESULT_SENT", f"Result sent back to bot for task_id: {task['task_id']}", print_log=True)
                    
                    except Exception as e:
                        await db.log(0, "WORKER_ERROR", f"Error processing message: {str(e)}", print_log=True)
    
    except Exception as e:
        await db.log(0, "WORKER_FATAL", f"Fatal error: {str(e)}", print_log=True)
    
    finally:
        if 'connection' in locals():
            await connection.close()
            await db.log(0, "WORKER_SHUTDOWN", "Worker shutdown", print_log=True)

if __name__ == "__main__":
    asyncio.run(main()) 