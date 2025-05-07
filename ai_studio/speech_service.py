import os
import aiohttp
from pathlib import Path
import asyncio
from abc import ABC, abstractmethod
import json


class BaseSpeechService(ABC):
    @abstractmethod
    async def text_to_speech(self, text: str, output_file: str = "output.ogg", **kwargs) -> Path:
        """Преобразовать текст в речь и сохранить в файл"""
        pass

    @abstractmethod
    async def speech_to_text(self, audio_path: Path, **kwargs) -> str:
        """Преобразовать аудиофайл в текст"""
        pass

async def _refresh_iam_token() -> str:
    """
    Обновляет IAM токен, используя OAUTH токен из переменных окружения.
    Возвращает новый IAM токен и устанавливает его в переменную окружения.
    """
    oauth_token = os.environ.get('OAUTH_TOKEN')
    if not oauth_token:
        raise ValueError("OAUTH_TOKEN не найден в переменных окружения")

    url = "https://iam.api.cloud.yandex.net/iam/v1/tokens"
    payload = json.dumps({"yandexPassportOauthToken": oauth_token})

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Ошибка получения IAM токена: {error_text}")
            
            result = await response.json()

            # print(f"[IAM Token][_refresh_iam_token] Получен IAM токен: {result=}")
            iam_token = result.get("iamToken")
            
            if iam_token is None:
                raise ValueError("[_refresh_iam_token] IAM токен не получен в ответе")
            else:
                print(f"[IAM Token][_refresh_iam_token] Успешно получен IAM токен: не покажу :DDD!")

            # Устанавливаем новый токен в переменную окружения
            os.environ['IAM_TOKEN'] = iam_token
            return iam_token


class YandexSpeechService(BaseSpeechService):
    TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

    def __init__(self):
        self.folder_id = os.environ.get('FOLDER_ID')
        self.iam_token = os.environ.get('IAM_TOKEN')
        self.oauth_token = os.environ.get('OAUTH_TOKEN')

        print(f"YandexSpeechService:__init__: \n{self.folder_id=}\n{self.iam_token=}\n{self.oauth_token=}\n\n")
        
        if not self.folder_id:
            raise ValueError("FOLDER_ID должен быть задан в переменных окружения")
        if not self.iam_token and not self.oauth_token:
            raise ValueError("IAM_TOKEN или OAUTH_TOKEN должны быть заданы в переменных окружения")
    
    async def _make_request(self, url: str, headers: dict, **kwargs) -> aiohttp.ClientResponse:
        """Выполняет запрос с автоматическим обновлением токена при необходимости"""
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, **kwargs) as response:
                if response.status == 401:  # Unauthorized - токен истек
                    print(f"[IAM Token] Токен истек, начинаем обновление...")
                    self.iam_token = await _refresh_iam_token()
                    print(f"[IAM Token] Токен успешно обновлен")
                    headers["Authorization"] = f"Bearer {self.iam_token}"
                    print(f"[IAM Token] Повторяем запрос с новым токеном")
                    # Создаем новую сессию для повторного запроса
                    async with aiohttp.ClientSession() as retry_session:
                        async with retry_session.post(url, headers=headers, **kwargs) as retry_response:
                            print(f"[IAM Token] Повторный запрос выполнен со статусом: {retry_response.status}")
                            # Читаем тело ответа сразу
                            content = await retry_response.read()
                            return content
                # Читаем тело ответа сразу
                content = await response.read()
                return content

    async def text_to_speech(self, text: str, output_file: str = "output.ogg", voice: str = "alena", lang: str = "ru-RU") -> Path:
        headers = {"Authorization": f"Bearer {self.iam_token}"}
        data = {
            "text": text,
            "lang": lang,
            "voice": voice,
            "format": "oggopus",
            "folderId": self.folder_id
        }
        
        content = await self._make_request(self.TTS_URL, headers, data=data)
        if not content:  # Если контент пустой, значит была ошибка
            raise RuntimeError("TTS request failed: Empty response")
            
        output_path = Path(output_file)
        output_path.write_bytes(content)
        return output_path

    async def speech_to_text(self, audio_data: bytes) -> str:
        """Преобразование аудио в текст"""
        headers = {
            "Authorization": f"Bearer {self.iam_token}",
        }
        
        params = {
            "lang": "ru-RU",
            "folderId": self.folder_id
        }
        
        content = await self._make_request(self.STT_URL, headers, params=params, data=audio_data)
        if not content:  # Если контент пустой, значит была ошибка
            raise Exception("STT error: Empty response")
            
        try:
            result = json.loads(content)
            return result.get("result", "")
        except json.JSONDecodeError as e:
            raise Exception(f"STT error: Invalid JSON response - {str(e)}")

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