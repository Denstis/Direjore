"""
Memory Operations Tools — handlers для работы с памятью.

Инструменты:
- read_project_memory: Чтение из памяти проекта
- write_project_memory: Запись в память проекта
- delete_project_memory: Удаление из памяти проекта
- read_user_memory: Чтение пользовательских предпочтений
- read_role_memory: Чтение временной памяти роли
- write_role_memory: Запись во временную память роли
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def read_project_memory(project_path: Path, key: Optional[str] = None) -> dict[str, Any]:
    """
    Чтение из памяти проекта.
    
    Args:
        project_path: Путь к проекту
        key: Ключ для чтения (если None — все данные)
        
    Returns:
        {"value": ...} или {"error": "..."}
    """
    try:
        memory_file = project_path / "memory" / "project.json"
        
        await asyncio.sleep(0.01)
        
        if not memory_file.exists():
            return {"value": {} if key is None else None}
        
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if key is None:
            return {"value": data, "all": True}
        else:
            return {"key": key, "value": data.get(key)}
        
    except Exception as e:
        logger.error(f"Ошибка чтения памяти проекта: {e}")
        return {"error": str(e)}


async def write_project_memory(project_path: Path, key: str, value: Any) -> dict[str, Any]:
    """
    Запись в память проекта.
    
    Args:
        project_path: Путь к проекту
        key: Ключ для записи
        value: Значение
        
    Returns:
        {"success": true} или {"error": "..."}
    """
    try:
        memory_dir = project_path / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_file = memory_dir / "project.json"
        
        await asyncio.sleep(0.01)
        
        # Чтение существующих данных
        data = {}
        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # Обновление
        data[key] = value
        
        # Атомарная запись
        temp_file = memory_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_file.replace(memory_file)
        
        return {"success": True, "key": key}
        
    except Exception as e:
        logger.error(f"Ошибка записи памяти проекта {key}: {e}")
        return {"error": str(e)}


async def delete_project_memory(project_path: Path, key: str) -> dict[str, Any]:
    """
    Удаление из памяти проекта.
    
    Args:
        project_path: Путь к проекту
        key: Ключ для удаления
        
    Returns:
        {"success": true} или {"error": "..."}
    """
    try:
        memory_file = project_path / "memory" / "project.json"
        
        await asyncio.sleep(0.01)
        
        if not memory_file.exists():
            return {"error": "Память проекта пуста"}
        
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if key in data:
            del data[key]
            
            # Атомарная запись
            temp_file = memory_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_file.replace(memory_file)
            
            return {"success": True, "deleted": key}
        else:
            return {"error": f"Ключ не найден: {key}"}
        
    except Exception as e:
        logger.error(f"Ошибка удаления из памяти проекта: {e}")
        return {"error": str(e)}


async def read_user_memory(project_path: Path, key: Optional[str] = None) -> dict[str, Any]:
    """
    Чтение пользовательских предпочтений.
    
    Args:
        project_path: Путь к проекту
        key: Ключ для чтения (если None — все данные)
        
    Returns:
        {"value": ...} или {"error": "..."}
    """
    try:
        # Пользовательская память хранится в корневой директории приложения
        app_root = project_path.parent.parent
        user_memory_file = app_root / "user_memory.json"
        
        await asyncio.sleep(0.01)
        
        if not user_memory_file.exists():
            return {"value": {} if key is None else None}
        
        with open(user_memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if key is None:
            return {"value": data, "all": True}
        else:
            return {"key": key, "value": data.get(key)}
        
    except Exception as e:
        logger.error(f"Ошибка чтения пользовательской памяти: {e}")
        return {"error": str(e)}


async def read_role_memory(project_path: Path, role_name: str, key: Optional[str] = None) -> dict[str, Any]:
    """
    Чтение временной памяти роли.
    
    Args:
        project_path: Путь к проекту
        role_name: Имя роли
        key: Ключ для чтения (если None — все данные)
        
    Returns:
        {"value": ...} или {"error": "..."}
    """
    try:
        memory_file = project_path / "memory" / f"role_{role_name}.json"
        
        await asyncio.sleep(0.01)
        
        if not memory_file.exists():
            return {"value": {} if key is None else None}
        
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if key is None:
            return {"value": data, "all": True, "role": role_name}
        else:
            return {"key": key, "value": data.get(key), "role": role_name}
        
    except Exception as e:
        logger.error(f"Ошибка чтения памяти роли: {e}")
        return {"error": str(e)}


async def write_role_memory(project_path: Path, role_name: str, key: str, value: Any) -> dict[str, Any]:
    """
    Запись во временную память роли.
    
    Args:
        project_path: Путь к проекту
        role_name: Имя роли
        key: Ключ для записи
        value: Значение
        
    Returns:
        {"success": true} или {"error": "..."}
    """
    try:
        memory_dir = project_path / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        memory_file = memory_dir / f"role_{role_name}.json"
        
        await asyncio.sleep(0.01)
        
        # Чтение существующих данных
        data = {}
        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        # Обновление
        data[key] = value
        
        # Атомарная запись
        temp_file = memory_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_file.replace(memory_file)
        
        return {"success": True, "key": key, "role": role_name}
        
    except Exception as e:
        logger.error(f"Ошибка записи памяти роли {key}: {e}")
        return {"error": str(e)}


def register_memory_handlers(tool_registry, memory_manager: "MemoryManager") -> None:
    """
    Регистрация всех memory ops handlers в реестре.
    
    Args:
        tool_registry: ToolRegistry instance
        memory_manager: MemoryManager instance для доступа к памяти
    """
    from functools import partial
    
    handlers = {
        "read_project_memory": partial(memory_manager.project_read),
        "write_project_memory": partial(memory_manager.project_write),
        "delete_project_memory": partial(memory_manager.project_delete),
        "read_user_memory": partial(memory_manager.user_get),
        "read_role_memory": partial(memory_manager.role_read),
        "write_role_memory": partial(memory_manager.role_write),
    }
    
    for name, handler in handlers.items():
        if tool_registry.has_tool(name):
            tool_registry.register_handler(name, handler)
            logger.debug(f"Зарегистрирован handler для {name}")
        else:
            logger.warning(f"Инструмент {name} не найден в реестре")
