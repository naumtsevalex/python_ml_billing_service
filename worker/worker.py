import os
import json
import asyncio
import aio_pika
from db.database import Database

async def process_task(message: aio_pika.IncomingMessage):
    """Обработка задачи от пользователя"""
    db = Database()
    
    try:
        # Получаем данные из сообщения
        body = json.loads(message.body.decode())
        user_id = body.get('user_id')
        task_type = body.get('type')
        task_data = body.get('data', {})

        # Логируем получение задачи
        await db.log(user_id, "TASK_RECEIVED", f"Received task of type: {task_type}", print_log=True)

        # Здесь будет обработка задачи
        result = {"status": "success", "message": "Task processed successfully"}

        # Логируем успешное выполнение
        await db.log(user_id, "TASK_COMPLETED", f"Task {task_type} completed successfully", print_log=True)

        return result

    except Exception as e:
        # Логируем ошибку
        await db.log(user_id, "TASK_ERROR", f"Error processing task: {str(e)}", print_log=True)
        raise

async def main():
    """Основная функция воркера"""
    db = Database()
    
    # Логируем запуск воркера
    await db.log(None, "WORKER_STARTED", "Worker started and ready to process tasks", print_log=True)
    
    try:
        # Подключаемся к RabbitMQ
        connection = await aio_pika.connect_robust(
            os.environ["RABBITMQ_URL"]
        )
        await db.log(None, "RABBITMQ_CONNECTED", f"Successfully connected to RabbitMQ at {os.environ['RABBITMQ_URL']}", print_log=True)

        # Создаем канал
        channel = await connection.channel()
        await db.log(None, "RABBITMQ_CHANNEL", "Created RabbitMQ channel", print_log=True)

        # Объявляем очередь
        queue = await channel.declare_queue("tasks")
        await db.log(None, "RABBITMQ_QUEUE", f"Declared queue: tasks", print_log=True)

        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    result = await process_task(message)
                    # Отправляем результат в очередь ответов
                    await channel.default_exchange.publish(
                        aio_pika.Message(
                            body=json.dumps(result).encode(),
                            correlation_id=message.correlation_id
                        ),
                        routing_key=message.reply_to
                    )
                except Exception as e:
                    # Логируем ошибку обработки сообщения
                    await db.log(None, "MESSAGE_PROCESSING_ERROR", f"Error processing message: {str(e)}", print_log=True)
                    raise

        # Начинаем слушать очередь
        await queue.consume(process_message)
        await db.log(None, "RABBITMQ_CONSUMING", "Started consuming messages from queue: tasks", print_log=True)

        try:
            # Держим воркер запущенным
            await asyncio.Future()
        finally:
            await connection.close()
            await db.log(None, "RABBITMQ_DISCONNECTED", "Disconnected from RabbitMQ", print_log=True)
            
    except Exception as e:
        await db.log(None, "WORKER_ERROR", f"Worker error: {str(e)}", print_log=True)
        raise

if __name__ == "__main__":
    asyncio.run(main()) 