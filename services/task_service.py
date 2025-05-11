from db.database import Database
from utils.file_utils import FileManager
from services.ai_service import AIService
from models.task_types import TaskTypeEnum
from models.task import TaskStatusEnum
import os
import aiohttp
from utils.utils import log_debug

class TaskService:
    
    def __init__(self):
        self.db = Database()
        self.file_manager = FileManager()
        self.ai_service = AIService()
        self.telegram_token = os.environ.get("TELEGRAM_TOKEN")

    async def _download_telegram_file(self, file_id: str) -> bytes:
        """Скачивает файл из Telegram по file_id"""
        # Получаем информацию о файле
        async with aiohttp.ClientSession() as session:
            # Получаем file_path
            file_info_url = f"https://api.telegram.org/bot{self.telegram_token}/getFile"
            async with session.get(file_info_url, params={"file_id": file_id}) as response:
                file_info = await response.json()
                if not file_info.get("ok"):
                    raise ValueError(f"Failed to get file info: {file_info}")
                file_path = file_info["result"]["file_path"]
            
            # Скачиваем файл
            file_url = f"https://api.telegram.org/file/bot{self.telegram_token}/{file_path}"
            async with session.get(file_url) as response:
                if response.status != 200:
                    raise ValueError(f"Failed to download file: {response.status}")
                return await response.read()

    async def process_task(self, task: dict) -> dict:
        """Обработка задачи"""
        user_id = task["user_id"]
        task_type = task["type"]
        data = task["data"]
        task_id = task["task_id"]
        
        # Проверяем существование пользователя
        await self.db.log(user_id, "TASK_DEBUG", f"Checking if user exists for task_id: {task_id}", print_log=True)
        user = await self.db.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Проверяем существование задачи
        await self.db.log(user_id, "TASK_DEBUG", f"Getting task from DB for task_id: {task_id}", print_log=True)
        db_task = await self.db.get_task(task_id)
        if not db_task:
            raise ValueError(f"Task {task_id} not found")
            
        # Обновляем статус задачи на processing
        await self.db.update_task(task_id, TaskStatusEnum.PROCESSING)
        await self.db.log(user_id, "TASK_STARTED", f"Processing {task_type} task with task_id: {task_id}", print_log=True)
        
        # Конвертируем тип задачи в enum
        task_type_enum = TaskTypeEnum(task_type)

        if task_type_enum == TaskTypeEnum.VOICE:
            # Скачиваем файл из Telegram
            await self.db.log(user_id, "TASK_DEBUG", f"Downloading file from Telegram for task_id: {task_id}", print_log=True)
            try:
                # Получаем file_id из данных задачи
                file_id = data
                await self.db.log(user_id, "TASK_DEBUG", f"Got file_id: {file_id} for task_id: {task_id}", print_log=True)
                
                # Скачиваем файл
                audio_content = await self._download_telegram_file(file_id)
                await self.db.log(user_id, "TASK_DEBUG", f"File downloaded successfully for task_id: {task_id}", print_log=True)
            except Exception as e:
                await self.db.log(user_id, "TASK_ERROR", f"Failed to download file: {str(e)}", print_log=True)
                raise ValueError(f"Failed to download voice file: {str(e)}")
            
            # Сохраняем файл локально
            await self.db.log(user_id, "TASK_DEBUG", f"Saving audio file for task_id: {task_id}", print_log=True)
            audio_path = await self.file_manager.save_audio(audio_content, user_id, task_id, direction="in")
            await self.db.log(user_id, "TASK_DEBUG", f"Audio file saved at {audio_path} for task_id: {task_id}", print_log=True)
            
            # Рассчитываем стоимость
            await self.db.log(user_id, "TASK_DEBUG", f"Calculating cost for STT task_id: {task_id}", print_log=True)
            cost = self.ai_service.calculate_cost(audio_content, "stt")
            await self.db.log(user_id, "TASK_DEBUG", f"Calculated cost for STT task_id: {task_id}, cost: {cost}", print_log=True)
            
            # Преобразуем речь в текст
            await self.db.log(user_id, "TASK_DEBUG", f"Starting STT for task_id: {task_id}", print_log=True)
            text = await self.ai_service.speech_to_text(audio_content)
            await self.db.log(user_id, "TASK_DEBUG", f"Completed STT for task_id: {task_id}", print_log=True)
            
            await self.db.log(user_id, "TASK_DEBUG", f"Saving text result for task_id: {task_id}", print_log=True)
            result_file = await self.file_manager.save_text(text, user_id, f"result_{task_id}")
            await self.db.log(user_id, "TASK_DEBUG", f"Saved text result for task_id: {task_id}", print_log=True)
            
            await self.db.log(user_id, "TASK_DEBUG", f"Updating task status to completed for task_id: {task_id}", print_log=True)
            await self.db.update_task(
                task_id=task_id,
                status=TaskStatusEnum.COMPLETED,
                result=text,
                cost=cost
            )
            
            await self.db.log(user_id, "TASK_COMPLETED", f"Task {task_type} completed successfully with task_id: {task_id}", print_log=True)
            return {
                "status": "success",
                "message": text,
                "type": task_type_enum,
                "result_file": result_file,
                "cost": cost
            }

        elif task_type_enum == TaskTypeEnum.TEXT:
            # Для текстовых сообщений data содержит сам текст
            text_content = data
            await self.db.log(user_id, "TASK_DEBUG", f"Processing text: {text_content}", print_log=True)
            
            # Рассчитываем стоимость и проверяем баланс
            await self.db.log(user_id, "TASK_DEBUG", f"Calculating cost for TTS task_id: {task_id}", print_log=True)
            cost = self.ai_service.calculate_cost(text_content, "tts")
            await self.db.log(user_id, "TASK_DEBUG", f"Calculated cost for TTS task_id: {task_id}, cost: {cost}", print_log=True)
            
            # await self.db.log(user_id, "TASK_DEBUG", f"Checking balance for task_id: {task_id}", print_log=True)
            # balance = await self.db.get_balance(user_id)
            # await self.db.log(user_id, "TASK_DEBUG", f"Current balance for task_id: {task_id} is {balance}", print_log=True)
            # if balance < cost:
            #     raise ValueError(f"Insufficient balance. Required: {cost}, available: {balance}")
            
            # Преобразуем текст в речь
            await self.db.log(user_id, "TASK_DEBUG", f"Starting TTS for task_id: {task_id}", print_log=True)
            result_file = await self.ai_service.text_to_speech(text_content, user_id, task_id)
            await self.db.log(user_id, "TASK_DEBUG", f"Completed TTS for task_id: {task_id}", print_log=True)
            
            # Списываем кредиты и обновляем задачу
            # await self.db.log(user_id, "TASK_DEBUG", f"Updating balance for task_id: {task_id}, deducting {cost}", print_log=True)
            # await self.db.update_balance(user_id, -cost)
            # await self.db.log(user_id, "BALANCE_UPDATED", f"Spent {cost} credits for TTS", print_log=True)
            
            await self.db.log(user_id, "TASK_DEBUG", f"Updating task status to completed for task_id: {task_id}", print_log=True)
            await self.db.update_task(
                task_id=task_id,
                status=TaskStatusEnum.COMPLETED,
                result=result_file,
                cost=cost
            )
            
            await self.db.log(user_id, "TASK_COMPLETED", f"Task {task_type} completed successfully with task_id: {task_id}", print_log=True)
            return {
                "status": "success",
                "message": "Текст успешно преобразован в речь",
                "type": task_type_enum,
                "result_file": result_file,
                "cost": cost
            }
        else:
            raise ValueError(f"Unknown task type: {task_type}") 