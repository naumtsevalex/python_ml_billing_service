from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Union, Optional


class StorageInterface(ABC):
    """Абстрактный интерфейс для работы с файлами"""
    
    @abstractmethod
    def save_file(
        self,
        content: Union[str, bytes],
        user_id: int,
        task_id: str,
        ext: str,
        subdir: Optional[str] = None,
        is_binary: bool = False,
        direction: str = "out"  # "in" или "out"
    ) -> str:
        """
        Сохраняет файл
        
        Args:
            content: Содержимое файла (строка или байты)
            user_id: ID пользователя
            task_id: ID задачи
            ext: Расширение файла (без точки)
            subdir: Поддиректория (например, 'audio' или 'text')
            is_binary: True если content это bytes, False если str
            direction: Направление файла ("in" - от пользователя, "out" - к пользователю)
            
        Returns:
            str: Путь к сохраненному файлу
        """
        pass
    
    @abstractmethod
    def get_file(self, path: str) -> Union[str, bytes]:
        """
        Получает содержимое файла
        
        Args:
            path: Путь к файлу
            
        Returns:
            Union[str, bytes]: Содержимое файла
        """
        pass
    
    @abstractmethod
    def delete_file(self, path: str) -> None:
        """
        Удаляет файл
        
        Args:
            path: Путь к файлу
        """
        pass

    @abstractmethod
    def get_file_path(
        self,
        user_id: int,
        task_id: str,
        ext: str,
        subdir: str = "text",
        direction: str = "in"
    ) -> str:
        """Получить путь к файлу"""
        # Используем абсолютный путь в контейнере
        base_path = Path("/app/data")
        filepath = base_path / subdir / f"{direction}_{user_id}_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        return str(filepath)


class LocalStorage(StorageInterface):
    """Локальное хранилище файлов"""
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
    
    def _generate_filename(self, user_id: int, task_id: str, ext: str, direction: str = "out") -> str:
        """Генерирует имя файла"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{direction}_{user_id}_{task_id}_{timestamp}.{ext}"
    
    def _ensure_dir_exists(self, path: Union[str, Path]) -> None:
        """Создает директорию, если она не существует"""
        Path(path).mkdir(parents=True, exist_ok=True)
    
    def get_file_path(
        self,
        user_id: int,
        task_id: str,
        ext: str,
        subdir: Optional[str] = None,
        direction: str = "out"
    ) -> str:
        """Получает полный путь к файлу без его создания"""
        # Формируем путь
        base_dir = Path("/app") / self.base_dir
        if subdir:
            base_dir = base_dir / subdir
        
        # Создаем директории
        self._ensure_dir_exists(base_dir)
        
        # Генерируем имя файла
        filename = self._generate_filename(user_id, task_id, ext, direction)
        filepath = base_dir / filename
        
        return str(filepath)
    
    def save_file(
        self,
        content: Union[str, bytes],
        user_id: int,
        task_id: str,
        ext: str,
        subdir: Optional[str] = None,
        is_binary: bool = False,
        direction: str = "out"
    ) -> str:
        # Получаем путь
        filepath = self.get_file_path(user_id, task_id, ext, subdir, direction)
        
        # Сохраняем файл
        mode = "wb" if is_binary else "w"
        encoding = None if is_binary else "utf-8"
        
        with open(filepath, mode, encoding=encoding) as f:
            f.write(content)
        
        return filepath
    
    def get_file(self, path: str) -> Union[str, bytes]:
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        # Определяем, бинарный файл или текстовый
        is_binary = filepath.suffix.lower() in {'.ogg', '.mp3', '.wav', '.jpg', '.png'}
        
        mode = "rb" if is_binary else "r"
        encoding = None if is_binary else "utf-8"
        
        with open(filepath, mode, encoding=encoding) as f:
            return f.read()
    
    def delete_file(self, path: str) -> None:
        filepath = Path(path)
        if filepath.exists():
            filepath.unlink()


class S3Storage(StorageInterface):
    """Хранилище файлов в Amazon S3 (заглушка)"""
    
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("S3 storage is not implemented yet")
    
    def save_file(self, *args, **kwargs) -> str:
        raise NotImplementedError("S3 storage is not implemented yet")
    
    def get_file(self, *args, **kwargs) -> Union[str, bytes]:
        raise NotImplementedError("S3 storage is not implemented yet")
    
    def delete_file(self, *args, **kwargs) -> None:
        raise NotImplementedError("S3 storage is not implemented yet")


# Фабрика для создания хранилища
def create_storage(
    storage_type: str = "local",
    **kwargs
) -> StorageInterface:
    """
    Создает экземпляр хранилища
    
    Args:
        storage_type: Тип хранилища ('local' или 's3')
        **kwargs: Дополнительные параметры для конкретного хранилища
        
    Returns:
        StorageInterface: Экземпляр хранилища
    """
    if storage_type == "local":
        return LocalStorage(**kwargs)
    elif storage_type == "s3":
        return S3Storage(**kwargs)
    else:
        raise ValueError(f"Unknown storage type: {storage_type}") 