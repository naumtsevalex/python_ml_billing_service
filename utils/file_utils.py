from typing import Union
from .storage import StorageInterface, create_storage


class FileManager:
    """Менеджер для работы с файлами"""
    
    def __init__(
        self,
        storage: StorageInterface = None,
        storage_type: str = "local",
        **storage_kwargs
    ):
        """
        Args:
            storage: Экземпляр хранилища (если None, создается новый)
            storage_type: Тип хранилища ('local' или 's3')
            **storage_kwargs: Параметры для создания хранилища
        """
        self.storage = storage or create_storage(storage_type, **storage_kwargs)
    
    async def save_audio(
        self,
        audio_content: bytes,
        user_id: int,
        task_id: str,
        direction: str = "in"
    ) -> str:
        """
        Сохраняет аудио файл
        
        Args:
            audio_content: Байты аудио файла
            user_id: ID пользователя
            task_id: ID задачи
            direction: Направление передачи (in или out)
            
        Returns:
            str: Путь к сохраненному файлу
        """
        return self.storage.save_file(
            content=audio_content,
            user_id=user_id,
            task_id=task_id,
            ext="ogg",
            subdir="audio",
            is_binary=True,
            direction=direction
        )
    
    async def save_text(
        self,
        text_content: str,
        user_id: int,
        task_id: str,
        direction: str = "out"
    ) -> str:
        """
        Сохраняет текстовый файл
        
        Args:
            text_content: Текст для сохранения
            user_id: ID пользователя
            task_id: ID задачи
            direction: Направление передачи (in или out)
            
        Returns:
            str: Путь к сохраненному файлу
        """
        return self.storage.save_file(
            content=text_content,
            user_id=user_id,
            task_id=task_id,
            ext="txt",
            subdir="text",
            is_binary=False,
            direction=direction
        )
    
    async def get_audio(self, path: str) -> bytes:
        """
        Получает аудио файл
        
        Args:
            path: Путь к файлу
            
        Returns:
            bytes: Содержимое аудио файла
        """
        content = self.storage.get_file(path)
        if not isinstance(content, bytes):
            raise ValueError(f"Expected bytes content for audio file: {path}")
        return content
    
    async def get_text(self, path: str) -> str:
        """
        Получает текстовый файл
        
        Args:
            path: Путь к файлу
            
        Returns:
            str: Содержимое текстового файла
        """
        content = self.storage.get_file(path)
        if isinstance(content, bytes):
            return content.decode('utf-8')
        return content
    
    async def delete_file(self, path: str) -> None:
        """
        Удаляет файл
        
        Args:
            path: Путь к файлу
        """
        self.storage.delete_file(path) 