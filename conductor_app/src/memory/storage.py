"""
Storage — файловая реализация хранилища памяти.

Расширяемо до SQLite/Redis через наследование.
Атомарная запись, backup, ротация логов.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FileStorage:
    """Файловое хранилище с атомарной записью и backup."""

    def __init__(self, base_path: Path, backup_count: int = 3):
        self.base_path = base_path
        self.backup_count = backup_count
        self.base_path.mkdir(parents=True, exist_ok=True)

    def read(self, filename: str) -> Optional[dict]:
        """
        Чтение JSON файла.
        
        Args:
            filename: Имя файла (без расширения)
            
        Returns:
            Dict с данными или None если файл не существует
        """
        file_path = self.base_path / f"{filename}.json"
        
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка чтения {filename}: {e}")
            return None

    def write(self, filename: str, data: dict, create_backup: bool = True) -> bool:
        """
        Атомарная запись JSON файла.
        
        Args:
            filename: Имя файла (без расширения)
            data: Данные для записи
            create_backup: Создать backup существующего файла
            
        Returns:
            True если успешно
        """
        file_path = self.base_path / f"{filename}.json"
        
        # Создание backup если файл существует
        if create_backup and file_path.exists():
            self._create_backup(file_path)
            
        # Атомарная запись: temp → rename
        temp_file = file_path.with_suffix(".tmp")
        
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            temp_file.rename(file_path)
            logger.debug(f"Записано: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка записи {filename}: {e}")
            return False

    def _create_backup(self, file_path: Path) -> None:
        """Создание backup файла с timestamp."""
        if not file_path.exists():
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}.{timestamp}.bak"
        backup_path = file_path.parent / backup_name
        
        try:
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Создан backup: {backup_name}")
            
            # Удаление старых backup
            self._cleanup_backups(file_path.stem)
            
        except Exception as e:
            logger.warning(f"Не удалось создать backup: {e}")

    def _cleanup_backups(self, filename_stem: str) -> None:
        """Удаление старых backup файлов."""
        backups = list(self.base_path.glob(f"{filename_stem}.*.bak"))
        
        # Сортировка по времени модификации (новые в конце)
        backups.sort(key=lambda p: p.stat().st_mtime)
        
        # Удаление старых если превышен лимит
        while len(backups) > self.backup_count:
            old_backup = backups.pop(0)
            try:
                old_backup.unlink()
                logger.debug(f"Удалён старый backup: {old_backup.name}")
            except Exception as e:
                logger.warning(f"Не удалось удалить backup {old_backup}: {e}")

    def delete(self, filename: str) -> bool:
        """Удаление файла."""
        file_path = self.base_path / f"{filename}.json"
        
        if not file_path.exists():
            return False
            
        try:
            file_path.unlink()
            logger.debug(f"Удалено: {filename}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления {filename}: {e}")
            return False

    def exists(self, filename: str) -> bool:
        """Проверка существования файла."""
        file_path = self.base_path / f"{filename}.json"
        return file_path.exists()


class SQLiteStorage(FileStorage):
    """
    SQLite реализация (расширение).
    
    Пока не используется, но готова к интеграции.
    """
    
    def __init__(self, db_path: Path):
        super().__init__(db_path.parent)
        self.db_path = db_path
        # Инициализация БД будет здесь при активации
