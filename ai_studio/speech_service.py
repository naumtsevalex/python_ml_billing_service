import os
import aiohttp
from pathlib import Path
import asyncio
from abc import ABC, abstractmethod

class BaseSpeechService(ABC):
    @abstractmethod
    async def text_to_speech(self, text: str, output_file: str = "output.ogg", **kwargs) -> Path:
        """Преобразовать текст в речь и сохранить в файл"""
        pass

    @abstractmethod
    async def speech_to_text(self, audio_path: Path, **kwargs) -> str:
        """Преобразовать аудиофайл в текст"""
        pass

class YandexSpeechService(BaseSpeechService):
    TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

    def __init__(self):
        self.folder_id = os.environ.get('FOLDER_ID')
        self.iam_token = os.environ.get('IAM_TOKEN')
        self.oauth_token = os.environ.get('OAUTH_TOKEN')
        
        if not self.folder_id:
            raise ValueError("FOLDER_ID должен быть задан в переменных окружения")
        if not self.iam_token and not self.oauth_token:
            raise ValueError("IAM_TOKEN или OAUTH_TOKEN должны быть заданы в переменных окружения")

    async def text_to_speech(self, text: str, output_file: str = "output.ogg", voice: str = "alena", lang: str = "ru-RU") -> Path:
        headers = {"Authorization": f"Bearer {self.iam_token}"}
        data = {
            "text": text,
            "lang": lang,
            "voice": voice,
            "format": "oggopus",
            "folderId": self.folder_id
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.TTS_URL, headers=headers, data=data) as response:
                if response.status != 200:
                    raise RuntimeError(f"TTS request failed: {await response.text()}")
                output_path = Path(output_file)
                output_path.write_bytes(await response.read())
                return output_path

    async def speech_to_text(self, audio_data: bytes) -> str:
        """Преобразование аудио в текст"""
        headers = {
            "Authorization": f"Api-Key {self.iam_token}",
            "Content-Type": "audio/ogg"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(self.STT_URL, headers=headers, data=audio_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["result"]
                else:
                    error_text = await response.text()
                    raise Exception(f"STT error: {error_text}")

# Пример использования
if __name__ == "__main__":
    async def main():
        service: BaseSpeechService = YandexSpeechService()
        # TTS пример
        text = "Привет, это тест синтеза речи!"
        audio_path = await service.text_to_speech(text, output_file="test.ogg")
        print(f"Аудио сохранено: {audio_path}")
        # STT пример (раскомментируй, если есть файл test.ogg)
        # recognized_text = await service.speech_to_text(Path("test.ogg"))
        # print(f"Распознанный текст: {recognized_text}")
    asyncio.run(main()) 