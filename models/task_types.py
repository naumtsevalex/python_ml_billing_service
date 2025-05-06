from enum import Enum

class TaskType(Enum):
    """Типы задач для обработки"""
    TEXT = "text"   # Text-to-Speech (TTS)
    VOICE = "voice" # Speech-to-Text (STT) 