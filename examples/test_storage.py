import asyncio
from utils.storage import LocalStorage
from utils.file_utils import FileManager
from services.ai_service import AIService

async def test_storage():
    # Создаем экземпляры
    storage = LocalStorage(base_dir="data")
    file_manager = FileManager(storage=storage)
    ai_service = AIService()
    
    # Тест 1: Сохранение и чтение текстового файла
    print("\n1. Тест текстового файла:")
    text_path = await file_manager.save_text(
        text_content="Привет, это тестовый текст!",
        user_id=1,
        task_id="test1",
        direction="out"
    )
    print(f"Сохранен текст в: {text_path}")
    
    text_content = await file_manager.get_text(text_path)
    print(f"Прочитанный текст: {text_content}")
    
    # Тест 2: Сохранение и чтение аудио файла
    print("\n2. Тест аудио файла:")
    audio_content = b"Test audio content"
    audio_path = await file_manager.save_audio(
        audio_content=audio_content,
        user_id=1,
        task_id="test2",
        direction="in"
    )
    print(f"Сохранено аудио в: {audio_path}")
    
    loaded_audio = await file_manager.get_audio(audio_path)
    print(f"Размер загруженного аудио: {len(loaded_audio)} байт")
    
    # Тест 3: TTS (с моком)
    print("\n3. Тест TTS:")
    tts_path = await ai_service.text_to_speech(
        text="Это тестовый текст для TTS",
        user_id=1,
        task_id="test3"
    )
    print(f"Создан аудио файл: {tts_path}")
    
    # Тест 4: STT (с моком)
    print("\n4. Тест STT:")
    text = await ai_service.speech_to_text(
        audio_content=b"Test audio for STT",
        user_id=1,
        task_id="test4"
    )
    print(f"Распознанный текст: {text}")
    
    # Тест 5: Расчет стоимости
    print("\n5. Тест расчета стоимости:")
    tts_cost = ai_service.calculate_cost("Test text", "tts")
    print(f"Стоимость TTS: {tts_cost}")
    
    stt_cost = ai_service.calculate_cost(b"Test audio", "stt")
    print(f"Стоимость STT: {stt_cost}")

if __name__ == "__main__":
    asyncio.run(test_storage()) 