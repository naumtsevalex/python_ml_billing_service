from enum import Enum

class TaskTypeEnum(str, Enum):
    """Типы задач для обработки"""
    TEXT = "text"  # Текст для преобразования в речь
    VOICE = "voice"  # Голосовое сообщение для преобразования в текст

class RabbitMQQueueEnum(str, Enum):
    """Названия очередей RabbitMQ"""
    TASK_PROCESSING = "tasks"  # Очередь для задач на обработку (бот -> воркер)
    TASK_RESULTS = "results"  # Очередь для результатов обработки (воркер -> бот) 
    