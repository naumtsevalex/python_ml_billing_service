from enum import Enum, auto

class TaskTypeEnum(str, Enum):
    """Типы задач для обработки"""
    TEXT = "text"  # Текст для преобразования в речь
    VOICE = "voice"  # Голосовое сообщение для преобразования в текст

class RabbitMQQueueEnum(str, Enum):
    """Названия очередей RabbitMQ"""
    TASK_PROCESSING = "tasks"  # Очередь для задач на обработку (бот -> воркер)
    # Для ответов используются временные очереди, создаваемые клиентом с уникальными именами 
    