"""
Memory Manager — Unified API для работы с памятью.

Scope:
- project: read/write для Director, read для агентов
- user: global preferences (read-only для агентов)
- role: temporary workspace (очищается после задачи)
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MemoryManager:
    """Менеджер памяти с изоляцией по scope."""

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.memory_dir = project_path / "memory"
        self.role_memory: dict[str, Any] = {}  # Временная память роли
        
        # Создание директории
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    # =============================================================================
    # PROJECT MEMORY (read/write)
    # =============================================================================

    async def project_read(self, key: Optional[str] = None) -> Any:
        """
        Чтение из памяти проекта.
        
        Args:
            key: Ключ для чтения (если None — вся память)
            
        Returns:
            Значение или dict со всеми данными
        """
        project_file = self.memory_dir / "project.json"
        
        if not project_file.exists():
            return {} if key is None else None
            
        try:
            with open(project_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if key is None:
                return data
            return data.get(key)
            
        except Exception as e:
            logger.error(f"Ошибка чтения project memory: {e}")
            return {} if key is None else None

    async def project_write(self, key: str, value: Any) -> bool:
        """
        Запись в память проекта.
        
        Args:
            key: Ключ для записи
            value: Значение (JSON-сериализуемое)
            
        Returns:
            True если успешно
        """
        project_file = self.memory_dir / "project.json"
        
        # Чтение существующих данных
        data = {}
        if project_file.exists():
            try:
                with open(project_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Ошибка чтения перед записью: {e}")
                
        # Обновление
        data[key] = value
        
        # Атомарная запись
        temp_file = project_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.rename(project_file)
            logger.debug(f"Записано в project memory: {key}")
            return True
        except Exception as e:
            logger.error(f"Ошибка записи project memory: {e}")
            return False

    async def project_delete(self, key: str) -> bool:
        """Удаление из памяти проекта."""
        project_file = self.memory_dir / "project.json"
        
        if not project_file.exists():
            return False
            
        try:
            with open(project_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if key in data:
                del data[key]
                
            temp_file = project_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.rename(project_file)
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления project memory: {e}")
            return False

    # =============================================================================
    # USER MEMORY (read-only для агентов)
    # =============================================================================

    async def user_get(self, key: Optional[str] = None) -> Any:
        """
        Чтение предпочтений пользователя.
        
        Args:
            key: Ключ для чтения (если None — все предпочтения)
        """
        # Глобальная память пользователя (вне проекта)
        user_file = self.project_path.parent / "user_memory.json"
        
        if not user_file.exists():
            return {} if key is None else None
            
        try:
            with open(user_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if key is None:
                return data
            return data.get(key)
            
        except Exception as e:
            logger.error(f"Ошибка чтения user memory: {e}")
            return {} if key is None else None

    async def user_set(self, key: str, value: Any) -> bool:
        """
        Запись предпочтений пользователя (только Director).
        
        Args:
            key: Ключ для записи
            value: Значение
        """
        user_file = self.project_path.parent / "user_memory.json"
        
        data = {}
        if user_file.exists():
            try:
                with open(user_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
                
        data[key] = value
        
        temp_file = user_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_file.rename(user_file)
            return True
        except Exception as e:
            logger.error(f"Ошибка записи user memory: {e}")
            return False

    # =============================================================================
    # ROLE MEMORY (temporary)
    # =============================================================================

    async def role_write(self, key: str, value: Any) -> None:
        """Запись во временную память роли."""
        self.role_memory[key] = value
        logger.debug(f"Записано в role memory: {key}")

    async def role_read(self, key: Optional[str] = None) -> Any:
        """Чтение из временной памяти роли."""
        if key is None:
            return self.role_memory
        return self.role_memory.get(key)

    async def role_clear(self) -> None:
        """Очистка временной памяти роли."""
        self.role_memory.clear()
        logger.debug("Role memory очищена")

    # =============================================================================
    # CONTEXT EXPORT
    # =============================================================================

    async def export_context(self, keys: list[str], scope: str = "project") -> dict:
        """
        Экспорт контекста по ключам.
        
        Args:
            keys: Список ключей
            scope: "project", "user", или "role"
            
        Returns:
            Dict с запрошенными данными
        """
        result = {}
        
        for key in keys:
            if scope == "project":
                value = await self.project_read(key)
            elif scope == "user":
                value = await self.user_get(key)
            elif scope == "role":
                value = await self.role_read(key)
            else:
                value = None
                
            if value is not None:
                result[key] = value
                
        return result
