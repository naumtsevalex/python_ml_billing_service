from db.database import Database
from utils.file_utils import FileManager
from services.ai_service import AIService
from models.task_types import TaskType
import os

class TaskService:
    
    def __init__(self):
        self.db = Database()
        self.file_manager = FileManager()
        self.ai_service = AIService()

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
        await self.db.update_task(task_id, "processing")
        await self.db.log(user_id, "TASK_STARTED", f"Processing {task_type} task with task_id: {task_id}", print_log=True)
        
        # Конвертируем тип задачи в enum
        task_type_enum = TaskType(task_type)

        if task_type_enum == TaskType.VOICE:
            # Получаем аудио файл
            await self.db.log(user_id, "TASK_DEBUG", f"Getting audio file for task_id: {task_id}", print_log=True)
            audio_content = await self.file_manager.get_audio(data)
            await self.db.log(user_id, "TASK_DEBUG", f"Got audio file for task_id: {task_id}", print_log=True)
            
            # Рассчитываем стоимость и проверяем баланс
            await self.db.log(user_id, "TASK_DEBUG", f"Calculating cost for STT task_id: {task_id}", print_log=True)
            cost = self.ai_service.calculate_cost(audio_content, "stt")
            await self.db.log(user_id, "TASK_DEBUG", f"Calculated cost for STT task_id: {task_id}, cost: {cost}", print_log=True)
            
            await self.db.log(user_id, "TASK_DEBUG", f"Checking balance for task_id: {task_id}", print_log=True)
            balance = await self.db.get_balance(user_id)
            await self.db.log(user_id, "TASK_DEBUG", f"Current balance for task_id: {task_id} is {balance}", print_log=True)
            
            if balance < cost:
                raise ValueError(f"Insufficient balance. Required: {cost}, available: {balance}")
            
            # Преобразуем речь в текст
            await self.db.log(user_id, "TASK_DEBUG", f"Starting STT for task_id: {task_id}", print_log=True)
            text = await self.ai_service.speech_to_text(audio_content)
            await self.db.log(user_id, "TASK_DEBUG", f"Completed STT for task_id: {task_id}", print_log=True)
            
            await self.db.log(user_id, "TASK_DEBUG", f"Saving text result for task_id: {task_id}", print_log=True)
            result_file = await self.file_manager.save_text(text, user_id, f"result_{task_id}")
            await self.db.log(user_id, "TASK_DEBUG", f"Saved text result for task_id: {task_id}", print_log=True)
            
            # Списываем кредиты и обновляем задачу
            await self.db.log(user_id, "TASK_DEBUG", f"Updating balance for task_id: {task_id}, deducting {cost}", print_log=True)
            await self.db.update_balance(user_id, -cost)
            await self.db.log(user_id, "BALANCE_UPDATED", f"Spent {cost} credits for STT", print_log=True)
            
            await self.db.log(user_id, "TASK_DEBUG", f"Updating task status to completed for task_id: {task_id}", print_log=True)
            await self.db.update_task(
                task_id=task_id,
                status="completed",
                result=text,
                cost=cost
            )
            
            await self.db.log(user_id, "TASK_COMPLETED", f"Task {task_type} completed successfully with task_id: {task_id}", print_log=True)
            return {
                "status": "success",
                "message": text,
                "type": task_type_enum.value,
                "result_file": result_file,
                "cost": cost
            }

        elif task_type_enum == TaskType.TEXT:
            # Для текстовых сообщений data содержит сам текст
            text_content = data
            await self.db.log(user_id, "TASK_DEBUG", f"Processing text: {text_content}", print_log=True)
            
            # Рассчитываем стоимость и проверяем баланс
            await self.db.log(user_id, "TASK_DEBUG", f"Calculating cost for TTS task_id: {task_id}", print_log=True)
            cost = self.ai_service.calculate_cost(text_content, "tts")
            await self.db.log(user_id, "TASK_DEBUG", f"Calculated cost for TTS task_id: {task_id}, cost: {cost}", print_log=True)
            
            await self.db.log(user_id, "TASK_DEBUG", f"Checking balance for task_id: {task_id}", print_log=True)
            balance = await self.db.get_balance(user_id)
            await self.db.log(user_id, "TASK_DEBUG", f"Current balance for task_id: {task_id} is {balance}", print_log=True)
            
            if balance < cost:
                raise ValueError(f"Insufficient balance. Required: {cost}, available: {balance}")
            
            # Преобразуем текст в речь
            await self.db.log(user_id, "TASK_DEBUG", f"Starting TTS for task_id: {task_id}", print_log=True)
            result_file = await self.ai_service.text_to_speech(text_content, user_id, task_id)
            await self.db.log(user_id, "TASK_DEBUG", f"Completed TTS for task_id: {task_id}", print_log=True)
            
            # Списываем кредиты и обновляем задачу
            await self.db.log(user_id, "TASK_DEBUG", f"Updating balance for task_id: {task_id}, deducting {cost}", print_log=True)
            await self.db.update_balance(user_id, -cost)
            await self.db.log(user_id, "BALANCE_UPDATED", f"Spent {cost} credits for TTS", print_log=True)
            
            await self.db.log(user_id, "TASK_DEBUG", f"Updating task status to completed for task_id: {task_id}", print_log=True)
            await self.db.update_task(
                task_id=task_id,
                status="completed",
                result=result_file,
                cost=cost
            )
            
            await self.db.log(user_id, "TASK_COMPLETED", f"Task {task_type} completed successfully with task_id: {task_id}", print_log=True)
            return {
                "status": "success",
                "message": "Текст успешно преобразован в речь",
                "type": task_type_enum.value,
                "result_file": result_file,
                "cost": cost
            }
        else:
            raise ValueError(f"Unknown task type: {task_type}") 