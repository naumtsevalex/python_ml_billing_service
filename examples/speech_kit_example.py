import os
import requests

# Получаем переменные окружения напрямую
FOLDER_ID = os.environ.get('FOLDER_ID')
IAM_TOKEN = os.environ.get('IAM_TOKEN')

# Путь к директории с аудио файлами
AUDIO_DIR = os.path.join(os.path.dirname(__file__), 'audio')

def text_to_speech(text, output_file="output.mp3"):
    """
    Преобразование текста в речь (TTS)
    
    Args:
        text (str): Текст для преобразования в речь
        output_file (str): Имя файла для сохранения аудио
    """
    url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
    
    headers = {
        "Authorization": f"Bearer {IAM_TOKEN}"
    }
    
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": "alena",  # Можно выбрать другие голоса
        "format": "mp3",
        "folderId": FOLDER_ID
    }
    
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        # Создаем полный путь к файлу
        full_path = os.path.join(AUDIO_DIR, output_file)
        with open(full_path, "wb") as f:
            f.write(response.content)
        print(f"Аудио сохранено в файл: {full_path}")
    else:
        print(f"Ошибка: {response.status_code}")
        print(response.text)

def speech_to_text(audio_file):
    """
    Преобразование речи в текст (STT)
    
    Args:
        audio_file (str): Имя аудио файла в директории audio (должен быть в формате OGG)
    """
    url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
    
    headers = {
        "Authorization": f"Bearer {IAM_TOKEN}"
    }
    
    params = {
        "lang": "ru-RU",
        "folderId": FOLDER_ID
    }
    
    # Создаем полный путь к файлу
    full_path = os.path.join(AUDIO_DIR, audio_file)
    
    with open(full_path, "rb") as f:
        data = f.read()
    
    response = requests.post(url, headers=headers, params=params, data=data)
    
    if response.status_code == 200:
        result = response.json()
        print("Распознанный текст:", result.get("result", ""))
    else:
        print(f"Ошибка: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Создаем директорию для аудио файлов, если она не существует
    os.makedirs(AUDIO_DIR, exist_ok=True)
    
    print("=== Тест Text-to-Speech (TTS) ===")
    text_to_speech("Привет! Это тестовое сообщение для проверки работы Yandex SpeechKit.", "test_tts.mp3")
    
    print("\n=== Тест Speech-to-Text (STT) с MP3 ===")
    print("Попытка распознать MP3 файл (ожидаем ошибку, так как нужен OGG):")
    speech_to_text("test_tts.mp3") 