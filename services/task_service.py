from db.database import Database
from utils.file_utils import FileManager
from services.ai_service import AIService

class TaskService:
    def __init__(self):
        self.db = Database()
        self.file_manager = FileManager()
        self.ai_service = AIService()

    async def process_task(self, task: dict) -> dict:
        """Обработка задачи"""
        user_id = task["user_id"]
        task_type = task["type"]
        file_path = task["file_path"]
        task_id = task["task_id"]
        
        # Создаем запись о задаче в БД
        await self.db.log(user_id, "TASK_DEBUG", f"Creating task record in DB for task_id: {task_id}", print_log=True)
        await self.db.create_task(
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
            payload=file_path
        )
        await self.db.log(user_id, "TASK_STARTED", f"Processing {task_type} task with task_id: {task_id}", print_log=True)
        
        # Получаем содержимое файла
        if task_type == "voice":
            # Получаем аудио файл
            await self.db.log(user_id, "TASK_DEBUG", f"Getting audio file for task_id: {task_id}", print_log=True)
            audio_content = await self.file_manager.get_audio(file_path)
            await self.db.log(user_id, "TASK_DEBUG", f"Got audio file for task_id: {task_id}", print_log=True)
            
            # Рассчитываем стоимость
            await self.db.log(user_id, "TASK_DEBUG", f"Calculating cost for STT task_id: {task_id}", print_log=True)
            cost = self.ai_service.calculate_cost(audio_content, "stt")
            await self.db.log(user_id, "TASK_DEBUG", f"Calculated cost for STT task_id: {task_id}, cost: {cost}", print_log=True)
            
            # Проверяем баланс
            await self.db.log(user_id, "TASK_DEBUG", f"Checking balance for task_id: {task_id}", print_log=True)
            balance = await self.db.get_balance(user_id)
            await self.db.log(user_id, "TASK_DEBUG", f"Current balance for task_id: {task_id} is {balance}", print_log=True)
            
            if balance < cost:
                error_msg = f"Insufficient balance. Required: {cost}, available: {balance}"
                print(f"[ERROR] {error_msg}")
                await self.db.update_task(task_id, "error", error_msg)
                raise ValueError(error_msg)
            
            # Преобразуем речь в текст
            await self.db.log(user_id, "TASK_DEBUG", f"Starting STT for task_id: {task_id}", print_log=True)
            text = await self.ai_service.speech_to_text(audio_content)
            await self.db.log(user_id, "TASK_DEBUG", f"Completed STT for task_id: {task_id}", print_log=True)
            
            # Сохраняем результат
            await self.db.log(user_id, "TASK_DEBUG", f"Saving text result for task_id: {task_id}", print_log=True)
            result_file = await self.file_manager.save_text(text, user_id, f"result_{task_id}")
            await self.db.log(user_id, "TASK_DEBUG", f"Saved text result for task_id: {task_id}", print_log=True)
            
            # Списываем кредиты
            await self.db.log(user_id, "TASK_DEBUG", f"Updating balance for task_id: {task_id}, deducting {cost}", print_log=True)
            await self.db.update_balance(user_id, -cost)
            await self.db.log(user_id, "BALANCE_UPDATED", f"Spent {cost} credits for STT", print_log=True)
            
            # Обновляем статус задачи
            await self.db.log(user_id, "TASK_DEBUG", f"Updating task status to completed for task_id: {task_id}", print_log=True)
            await self.db.update_task(
                task_id=task_id,
                status="completed",
                result=text,
                cost=cost
            )
            
            result = {
                "status": "success",
                "message": text,
                "type": "voice",
                "result_file": result_file,
                "cost": cost
            }
        else:
            # Получаем текстовый файл
            await self.db.log(user_id, "TASK_DEBUG", f"Getting text file for task_id: {task_id}", print_log=True)
            text_content = await self.file_manager.get_text(file_path)
            await self.db.log(user_id, "TASK_DEBUG", f"Got text file for task_id: {task_id}", print_log=True)
            
            # Рассчитываем стоимость
            await self.db.log(user_id, "TASK_DEBUG", f"Calculating cost for TTS task_id: {task_id}", print_log=True)
            cost = self.ai_service.calculate_cost(text_content, "tts")
            await self.db.log(user_id, "TASK_DEBUG", f"Calculated cost for TTS task_id: {task_id}, cost: {cost}", print_log=True)
            
            # Проверяем баланс
            await self.db.log(user_id, "TASK_DEBUG", f"Checking balance for task_id: {task_id}", print_log=True)
            balance = await self.db.get_balance(user_id)
            await self.db.log(user_id, "TASK_DEBUG", f"Current balance for task_id: {task_id} is {balance}", print_log=True)
            
            if balance < cost:
                error_msg = f"Insufficient balance. Required: {cost}, available: {balance}"
                print(f"[ERROR] {error_msg}")
                await self.db.update_task(task_id, "error", error_msg)
                raise ValueError(error_msg)
            
            # Преобразуем текст в речь
            await self.db.log(user_id, "TASK_DEBUG", f"Starting TTS for task_id: {task_id}", print_log=True)
            result_file = await self.ai_service.text_to_speech(
                text_content,
                user_id,
                task_id
            )
            await self.db.log(user_id, "TASK_DEBUG", f"Completed TTS for task_id: {task_id}", print_log=True)
            
            # Списываем кредиты
            await self.db.log(user_id, "TASK_DEBUG", f"Updating balance for task_id: {task_id}, deducting {cost}", print_log=True)
            await self.db.update_balance(user_id, -cost)
            await self.db.log(user_id, "BALANCE_UPDATED", f"Spent {cost} credits for TTS", print_log=True)
            
            # Обновляем статус задачи
            await self.db.log(user_id, "TASK_DEBUG", f"Updating task status to completed for task_id: {task_id}", print_log=True)
            await self.db.update_task(
                task_id=task_id,
                status="completed",
                result=result_file,
                cost=cost
            )
            
            result = {
                "status": "success",
                "message": "Текст успешно преобразован в речь",
                "type": "text",
                "result_file": result_file,
                "cost": cost
            }
        
        await self.db.log(user_id, "TASK_COMPLETED", f"Task {task_type} completed successfully with task_id: {task_id}", print_log=True)
        return result 