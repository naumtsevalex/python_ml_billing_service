import os
import json
import uuid
import aio_pika
from aiogram import Bot
from db.database import Database
from utils.file_utils import FileManager

class MessageService:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        self.file_manager = FileManager()

    async def register_user(self, telegram_id: int, username: str) -> None:
        """Регистрация пользователя"""
        await self.db.register_user(telegram_id, username)

    async def process_message(self, user_id: int, message_id: int, text: str = None, voice_file_id: str = None) -> tuple[str, str, str]:
        """Обработка входящего сообщения"""
        # Проверяем баланс
        balance = await self.db.get_balance(user_id)
        if balance <= 0:
            raise ValueError("Insufficient balance")

        # Сохраняем сообщение в файл
        if voice_file_id:
            # Получаем файл голосового сообщения
            voice_file = await self.bot.get_file(voice_file_id)
            voice_bytes = await self.bot.download_file(voice_file.file_path)
            
            # Сохраняем аудио файл
            file_path = await self.file_manager.save_audio(
                voice_bytes,
                user_id,
                f"voice_{message_id}",
                direction="in"
            )
            await self.db.log(user_id, "FILE_SAVED", f"Saved voice message to {file_path}", print_log=True)
            
            return "voice", file_path, file_path
            
        else:
            # Сохраняем текстовое сообщение
            file_path = await self.file_manager.save_text(
                text,
                user_id,
                f"text_{message_id}",
                direction="in"
            )
            await self.db.log(user_id, "FILE_SAVED", f"Saved text message to {file_path}", print_log=True)
            
            return "text", text, file_path

    async def send_task_to_worker(self, user_id: int, task_type: str, task_data: str, file_path: str) -> dict:
        """Отправка задачи воркеру"""
        # Подключаемся к RabbitMQ
        await self.db.log(user_id, "RABBITMQ_CONNECTING", f"Connecting to RabbitMQ at {os.environ['RABBITMQ_URL']}", print_log=True)
        connection = await aio_pika.connect_robust(os.environ["RABBITMQ_URL"])
        await self.db.log(user_id, "RABBITMQ_CONNECTED", "Successfully connected to RabbitMQ", print_log=True)
        
        try:
            # Создаем канал
            channel = await connection.channel()
            await self.db.log(user_id, "RABBITMQ_CHANNEL", "Created RabbitMQ channel", print_log=True)
            
            # Генерируем уникальный task_id
            task_id = str(uuid.uuid4())
            
            # Формируем задачу
            task = {
                "user_id": user_id,
                "type": task_type,
                "task_id": task_id,  # Отдельное поле для task_id
                "data": task_data,   # Оригинальные данные
                "file_path": file_path
            }
            
            # Создаем очередь для ответа
            reply_queue = await channel.declare_queue(exclusive=True)
            await self.db.log(user_id, "RABBITMQ_REPLY_QUEUE", f"Created reply queue: {reply_queue.name}", print_log=True)
            
            # Отправляем задачу
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(task).encode(),
                    reply_to=reply_queue.name
                ),
                routing_key="tasks"
            )
            
            await self.db.log(user_id, "TASK_SENT", f"Task sent to worker: {task['type']}", print_log=True)
            
            # Ждем ответ
            async with reply_queue.iterator() as queue_iter:
                await self.db.log(user_id, "WAITING_REPLY", "Waiting for worker reply", print_log=True)
                async for message in queue_iter:
                    async with message.process():
                        result = json.loads(message.body.decode())
                        return result

        finally:
            await connection.close()
            await self.db.log(user_id, "RABBITMQ_DISCONNECTED", "Disconnected from RabbitMQ", print_log=True)

    async def send_result_to_user(self, user_id: int, result: dict) -> None:
        """Отправка результата пользователю"""
        if result["status"] == "success":
            await self.db.log(user_id, "TASK_RESULT", f"Task completed: {result['message']}", print_log=True)
            
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
            await self.db.log(user_id, "TASK_ERROR", f"Task failed: {result.get('error', 'Unknown error')}", print_log=True)
            await self.bot.send_message(user_id, "Произошла ошибка при обработке задачи.") 