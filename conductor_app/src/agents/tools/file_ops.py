"""
File Operations Tools — handlers для работы с файлами.

Инструменты:
- read_file: Чтение файла
- write_file: Запись файла
- list_files: Список файлов в директории
- delete_file: Удаление файла
- edit_file: Редактирование файла (поиск/замена)
- search_code: Поиск по содержимому файлов
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Optional

from src.core.platform_utils import safe_path_join as safe_join

logger = logging.getLogger(__name__)


async def read_file(project_path: Path, path: str, max_lines: int = 0) -> dict[str, Any]:
    """
    Чтение файла.
    
    Args:
        project_path: Путь к проекту
        path: Относительный путь к файлу
        max_lines: Максимальное количество строк (0 = без ограничений)
        
    Returns:
        {"content": "..."} или {"error": "..."}
    """
    try:
        # Безопасность: запрет выхода за пределы проекта
        full_path_str = safe_join(project_path / "workspace", path)
        full_path = Path(full_path_str)  # Конвертируем строку в Path
        
        if not full_path.exists():
            return {"error": f"Файл не найден: {path}"}
        
        # Имитация async IO
        await asyncio.sleep(0.01)
        
        with open(full_path, "r", encoding="utf-8") as f:
            if max_lines > 0:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line)
                content = "".join(lines)
                if len(lines) == max_lines:
                    content += "\n... [обрезано]"
            else:
                content = f.read()
            
        return {"content": content, "size": len(content)}
        
    except ValueError as e:
        return {"error": f"Небезопасный путь: {e}"}
    except Exception as e:
        logger.error(f"Ошибка чтения {path}: {e}")
        return {"error": str(e)}


async def write_file(project_path: Path, path: str, content: str, encoding: str = "utf-8", overwrite: bool = True) -> dict[str, Any]:
    """
    Запись файла.
    
    Args:
        project_path: Путь к проекту
        path: Относительный путь к файлу
        content: Содержимое файла
        encoding: Кодировка файла
        overwrite: Перезаписывать ли существующий файл
        
    Returns:
        {"success": true, "path": "..."} или {"error": "..."}
    """
    try:
        # Безопасность: запрет выхода за пределы проекта
        full_path_str = safe_join(project_path / "workspace", path)
        full_path = Path(full_path_str)  # Конвертируем строку в Path
        
        if full_path.exists() and not overwrite:
            return {"error": f"Файл уже существует: {path}"}
        
        # Создание директории если нужно
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Имитация async IO
        await asyncio.sleep(0.01)
        
        with open(full_path, "w", encoding=encoding) as f:
            f.write(content)
            
        return {"success": True, "path": path, "size": len(content)}
        
    except ValueError as e:
        return {"error": f"Небезопасный путь: {e}"}
    except Exception as e:
        logger.error(f"Ошибка записи {path}: {e}")
        return {"error": str(e)}


async def edit_file(
    project_path: Path,
    path: str,
    old_text: Optional[str] = None,
    new_text: Optional[str] = None,
    insert_line: Optional[int] = None,
    insert_text: Optional[str] = None
) -> dict[str, Any]:
    """
    Редактирование файла: поиск и замена или вставка.
    
    Args:
        project_path: Путь к проекту
        path: Относительный путь к файлу
        old_text: Текст для поиска
        new_text: Текст для замены
        insert_line: Номер строки для вставки (0-based)
        insert_text: Текст для вставки
        
    Returns:
        {"success": true, "changes": N} или {"error": "..."}
    """
    try:
        full_path_str = safe_join(project_path / "workspace", path)
        full_path = Path(full_path_str)  # Конвертируем строку в Path
        
        if not full_path.exists():
            return {"error": f"Файл не найден: {path}"}
        
        await asyncio.sleep(0.01)
        
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        changes = 0
        
        # Режим поиска и замены
        if old_text is not None and new_text is not None:
            if old_text in content:
                content = content.replace(old_text, new_text, 1)
                changes = 1
            else:
                return {"error": "Текст для замены не найден"}
        
        # Режим вставки
        elif insert_line is not None and insert_text is not None:
            lines = content.split("\n")
            if 0 <= insert_line <= len(lines):
                lines.insert(insert_line, insert_text)
                content = "\n".join(lines)
                changes = 1
            else:
                return {"error": f"Неверный номер строки: {insert_line}"}
        
        else:
            return {"error": "Укажите old_text/new_text или insert_line/insert_text"}
        
        # Запись изменённого содержимого
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {"success": True, "changes": changes}
        
    except ValueError as e:
        return {"error": f"Небезопасный путь: {e}"}
    except Exception as e:
        logger.error(f"Ошибка редактирования {path}: {e}")
        return {"error": str(e)}


async def list_files(project_path: Path, path: str = ".", recursive: bool = False, pattern: str = "*") -> dict[str, Any]:
    """
    Список файлов в директории.
    
    Args:
        project_path: Путь к проекту
        path: Относительный путь к директории
        recursive: Рекурсивный обход
        pattern: Glob-паттерн для фильтрации
        
    Returns:
        {"files": [...], "directories": [...]} или {"error": "..."}
    """
    try:
        base_path_str = safe_join(project_path / "workspace", path)
        base_path = Path(base_path_str)  # Конвертируем строку в Path
        
        if not base_path.exists():
            return {"error": f"Директория не найдена: {path}"}
        
        if not base_path.is_dir():
            return {"error": f"Не директория: {path}"}
        
        await asyncio.sleep(0.01)
        
        files = []
        directories = []
        
        if recursive:
            for item in base_path.rglob(pattern):
                rel_path = item.relative_to(base_path).as_posix()
                if item.is_file():
                    files.append(rel_path)
                elif item.is_dir():
                    directories.append(rel_path)
        else:
            for item in base_path.glob(pattern):
                rel_path = item.relative_to(base_path).as_posix()
                if item.is_file():
                    files.append(rel_path)
                elif item.is_dir():
                    directories.append(rel_path)
        
        return {
            "directory": path or "/",
            "files": sorted(files),
            "directories": sorted(directories),
        }
        
    except ValueError as e:
        return {"error": f"Небезопасный путь: {e}"}
    except Exception as e:
        logger.error(f"Ошибка списка файлов в {path}: {e}")
        return {"error": str(e)}


async def search_code(
    project_path: Path,
    pattern: str,
    path: str = ".",
    file_pattern: str = "*",
    max_results: int = 50
) -> dict[str, Any]:
    """
    Поиск по содержимому файлов с использованием регулярных выражений.
    
    Args:
        project_path: Путь к проекту
        pattern: Регулярное выражение для поиска
        path: Директория для поиска
        file_pattern: Glob-паттерн для имён файлов
        max_results: Максимум результатов
        
    Returns:
        {"results": [{"file": "...", "line": N, "text": "..."}]} или {"error": "..."}
    """
    try:
        base_path_str = safe_join(project_path / "workspace", path)
        base_path = Path(base_path_str)  # Конвертируем строку в Path
        
        if not base_path.exists():
            return {"error": f"Директория не найдена: {path}"}
        
        try:
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        except re.error as e:
            return {"error": f"Неверное регулярное выражение: {e}"}
        
        await asyncio.sleep(0.01)
        
        results = []
        
        for file_path in base_path.glob(file_pattern):
            if not file_path.is_file():
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            rel_path = file_path.relative_to(base_path).as_posix()
                            results.append({
                                "file": rel_path,
                                "line": line_num,
                                "text": line.strip()[:200]  # Ограничение длины строки
                            })
                            
                            if len(results) >= max_results:
                                break
            except Exception:
                pass  # Пропускаем файлы которые не удалось прочитать
            
            if len(results) >= max_results:
                break
        
        return {
            "pattern": pattern,
            "results_count": len(results),
            "results": results
        }
        
    except ValueError as e:
        return {"error": f"Небезопасный путь: {e}"}
    except Exception as e:
        logger.error(f"Ошибка поиска в коде: {e}")
        return {"error": str(e)}


async def delete_file(project_path: Path, path: str) -> dict[str, Any]:
    """
    Удаление файла.
    
    Args:
        project_path: Путь к проекту
        path: Относительный путь к файлу
        
    Returns:
        {"success": true} или {"error": "..."}
    """
    try:
        full_path_str = safe_join(project_path / "workspace", path)
        full_path = Path(full_path_str)  # Конвертируем строку в Path
        
        if not full_path.exists():
            return {"error": f"Файл не найден: {path}"}
        
        if full_path.is_dir():
            return {"error": "Удаление директорий не поддерживается"}
        
        await asyncio.sleep(0.01)
        
        full_path.unlink()
        
        return {"success": True, "deleted": path}
        
    except ValueError as e:
        return {"error": f"Небезопасный путь: {e}"}
    except Exception as e:
        logger.error(f"Ошибка удаления {path}: {e}")
        return {"error": str(e)}


def register_file_handlers(tool_registry, project_path: Path) -> None:
    """
    Регистрация всех file ops handlers в реестре.
    
    Args:
        tool_registry: ToolRegistry instance
        project_path: Путь к проекту
    """
    from functools import partial
    
    handlers = {
        "read_file": partial(read_file, project_path),
        "write_file": partial(write_file, project_path),
        "edit_file": partial(edit_file, project_path),
        "list_files": partial(list_files, project_path),
        "search_code": partial(search_code, project_path),
        "delete_file": partial(delete_file, project_path),
    }
    
    for name, handler in handlers.items():
        if tool_registry.has_tool(name):
            tool_registry.register_handler(name, handler)
            logger.debug(f"Зарегистрирован handler для {name}")
        else:
            logger.warning(f"Инструмент {name} не найден в реестре")
