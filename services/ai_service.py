from typing import Union, Tuple
from ai_studio.speech_service import YandexSpeechService
from utils.file_utils import FileManager
from utils.storage import LocalStorage


class AIService:
    def __init__(self):
        self.speech_service = YandexSpeechService()
        self.file_manager = FileManager(LocalStorage())

    async def text_to_speech(self, text: str, user_id: int, task_id: str) -> str:
        """Преобразование текста в речь"""
        # Получаем правильный путь через get_file_path
        audio_path = self.file_manager.storage.get_file_path(
            user_id=user_id,
            task_id=task_id,
            ext="ogg",
            subdir="audio",
            direction="out"  # Исходящий файл - отдаем пользователю
        )
        
        # Используем существующий сервис для создания аудио
        result_path = await self.speech_service.text_to_speech(text, output_file=audio_path)
        
        # Преобразуем Path в строку
        return str(result_path)

    async def speech_to_text(self, audio_content: bytes) -> str:
        """Преобразование речи в текст"""
        # Используем существующий сервис для распознавания
        text = await self.speech_service.speech_to_text(audio_content)
        return text

    def calculate_cost(self, content: Union[str, bytes], operation: str) -> int:
        """Расчет стоимости операции"""
        if operation == "tts":
            # Стоимость за символ текста
            # return len(content) * 0.1  # 0.1 кредита за символ
            return 5 # 1 токен
        else:  # stt
            # Стоимость за секунду аудио (примерно)
            # Предполагаем, что аудио в формате 16kHz, 16-bit mono
            # Размер в байтах / (16000 * 2) = количество секунд
            # audio_length = len(content) / (16000 * 2)
            # return int(audio_length * 0.5)  # 0.5 кредита за секунду 
            
            return 4  # токенов 
        