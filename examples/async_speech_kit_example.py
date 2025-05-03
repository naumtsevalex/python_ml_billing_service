import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from pathlib import Path
import aiohttp

AUDIO_DIR = Path(__file__).parent / "audio"

class BaseSpeechService(ABC):
    @abstractmethod
    async def text_to_speech(self, text: str, output_file: str) -> Path:
        pass

    @abstractmethod
    async def speech_to_text(self, audio_file: str) -> str:
        pass

class YandexSpeechService(BaseSpeechService):
    TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    STT_URL = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"

    def __init__(self):
        self.folder_id = os.environ['FOLDER_ID']
        self.iam_token = os.environ['IAM_TOKEN']
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    async def text_to_speech(
        self, 
        text: str, 
        output_file: str = "output.ogg",
        voice: str = "alena",
        lang: str = "ru-RU"
    ) -> Path:
        if not self._session:
            raise RuntimeError("Service must be used as async context manager")

        headers = {"Authorization": f"Bearer {self.iam_token}"}
        data = {
            "text": text,
            "lang": lang,
            "voice": voice,
            "format": "oggopus",
            "folderId": self.folder_id
        }

        async with self._session.post(self.TTS_URL, headers=headers, data=data) as response:
            if response.status != 200:
                raise RuntimeError(f"TTS request failed: {await response.text()}")

            output_path = AUDIO_DIR / output_file
            content = await response.read()
            output_path.write_bytes(content)
            return output_path

    async def speech_to_text(
        self,
        audio_file: str,
        lang: str = "ru-RU"
    ) -> str:
        if not self._session:
            raise RuntimeError("Service must be used as async context manager")

        headers = {"Authorization": f"Bearer {self.iam_token}"}
        params = {
            "lang": lang,
            "folderId": self.folder_id
        }

        audio_path = AUDIO_DIR / audio_file
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        async with self._session.post(
            self.STT_URL,
            headers=headers,
            params=params,
            data=audio_path.read_bytes()
        ) as response:
            if response.status != 200:
                raise RuntimeError(f"STT request failed: {await response.text()}")

            result = await response.json()
            return result.get("result", "")

async def main():
    async with YandexSpeechService() as speech_service:
        try:
            output_path = await speech_service.text_to_speech(
                "Привет! Это тестовое сообщение для проверки работы Yandex SpeechKit.",
                "test_tts.ogg"
            )
            print(f"TTS completed, file saved to: {output_path}")

            text = await speech_service.speech_to_text("test_tts.ogg")
            print(f"STT completed, recognized text: {text}")

        except Exception as e:
            print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 