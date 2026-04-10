"""
System Operations Tools — handlers для системных операций.

Инструменты:
- run_command: Выполнение команд оболочки
- pip_install: Установка Python пакетов
- git_clone: Клонирование репозиториев
- git_command: Git операции
"""

import asyncio
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from src.core.platform_utils import platform_utils

logger = logging.getLogger(__name__)


def safe_join(base_path: str, *paths: str) -> str:
    """Безопасное соединение путей через platform_utils."""
    return platform_utils.safe_join(base_path, *paths)


def is_windows() -> bool:
    """Проверка на Windows."""
    return platform_utils.is_windows


# Список запрещённых паттернов команд
DANGEROUS_PATTERNS = [
    r"sudo",
    r"rm\s+(-rf|--recursive)",
    r"format\s+",
    r"del\s+/[sq]",
    r"rmdir\s+/s",
    r"fdisk",
    r"mkfs",
    r"dd\s+",
    r":(){\s*:\|:&\s*}",  # fork bomb
    r"\$\(\(",  # command substitution в bash
    r"`.*`",  # backticks
]


def is_command_safe(command: str) -> tuple[bool, Optional[str]]:
    """
    Проверить команду на безопасность.
    
    Returns:
        (is_safe, error_message)
    """
    cmd_lower = command.lower()
    
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return False, f"Обнаружена опасная команда: {pattern}"
    
    # Запрет абсолютных путей вне workspace
    if command.startswith("/") and not is_windows():
        pass  # Будет проверено в контексте workspace
    
    return True, None


async def run_command(
    project_path: Path,
    command: str,
    cwd: str = ".",
    timeout: int = 30,
    shell: bool = True
) -> dict[str, Any]:
    """
    Выполнение системной команды.
    
    Args:
        project_path: Путь к проекту
        command: Команда для выполнения
        cwd: Рабочая директория относительно workspace
        timeout: Таймаут в секундах
        shell: Использовать оболочку
        
    Returns:
        {"stdout": "...", "stderr": "...", "returncode": 0} или {"error": "..."}
    """
    try:
        # Проверка безопасности
        is_safe, error_msg = is_command_safe(command)
        if not is_safe:
            return {"error": f"Команда заблокирована: {error_msg}"}
        
        # Определение рабочей директории
        try:
            work_dir = safe_join(project_path / "workspace", cwd)
        except ValueError as e:
            return {"error": f"Небезопасный путь cwd: {e}"}
        
        if not work_dir.exists():
            work_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Выполнение команды в {work_dir}: {command}")
        
        # Получение оболочки для текущей ОС
        if shell:
            if is_windows():
                full_cmd = f"cmd.exe /c \"{command}\""
            else:
                full_cmd = f"/bin/bash -c \"{command}\""
        else:
            full_cmd = command
        
        # Асинхронное выполнение
        process = await asyncio.create_subprocess_shell(
            full_cmd if shell else command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir),
            shell=shell
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {"error": f"Таймаут выполнения команды ({timeout}с)"}
        
        result = {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "returncode": process.returncode,
            "command": command,
            "cwd": str(work_dir.relative_to(project_path / "workspace"))
        }
        
        if process.returncode != 0:
            logger.warning(f"Команда вернула код {process.returncode}: {command}")
        
        return result
        
    except Exception as e:
        logger.error(f"Ошибка выполнения команды {command}: {e}")
        return {"error": str(e)}


async def pip_install(
    project_path: Path,
    packages: Optional[list[str]] = None,
    upgrade: bool = False,
    requirements_file: Optional[str] = None
) -> dict[str, Any]:
    """
    Установка Python пакетов через pip.
    
    Args:
        project_path: Путь к проекту
        packages: Список пакетов для установки
        upgrade: Обновлять ли пакеты
        requirements_file: Путь к requirements.txt
        
    Returns:
        {"success": true, "installed": [...]} или {"error": "..."}
    """
    try:
        # Определение команды pip
        if is_windows():
            pip_cmd = "pip"
        else:
            pip_cmd = "pip3"
        
        # Формирование аргументов
        args = [pip_cmd, "install"]
        
        if upgrade:
            args.append("--upgrade")
        
        if requirements_file:
            try:
                req_path = safe_join(project_path / "workspace", requirements_file)
                if not req_path.exists():
                    return {"error": f"requirements.txt не найден: {requirements_file}"}
                args.extend(["-r", str(req_path)])
            except ValueError as e:
                return {"error": f"Небезопасный путь requirements: {e}"}
        elif packages:
            args.extend(packages)
        else:
            return {"error": "Укажите packages или requirements_file"}
        
        # Выполнение в workspace проекта
        workspace = project_path / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Установка пакетов: {' '.join(args)}")
        
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(workspace)
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=120  # pip может работать долго
        )
        
        result = {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "returncode": process.returncode
        }
        
        if process.returncode == 0:
            result["success"] = True
            result["installed"] = packages or ["from requirements"]
        else:
            result["error"] = f"pip вернул код {process.returncode}"
        
        return result
        
    except asyncio.TimeoutError:
        return {"error": "Таймаут установки пакетов (120с)"}
    except FileNotFoundError:
        return {"error": "pip не найден. Убедитесь что Python установлен."}
    except Exception as e:
        logger.error(f"Ошибка pip install: {e}")
        return {"error": str(e)}


async def git_clone(
    project_path: Path,
    url: str,
    directory: Optional[str] = None,
    branch: str = "main",
    depth: int = 1
) -> dict[str, Any]:
    """
    Клонирование Git репозитория.
    
    Args:
        project_path: Путь к проекту
        url: URL репозитория
        directory: Имя директории для клонирования
        branch: Ветка
        depth: Глубина клонирования
        
    Returns:
        {"success": true, "path": "..."} или {"error": "..."}
    """
    try:
        # Извлечение имени репозитория из URL
        if not directory:
            repo_name = url.rstrip("/").split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            directory = repo_name
        
        # Проверка безопасности имени директории
        if ".." in directory or directory.startswith("/"):
            return {"error": f"Небезопасное имя директории: {directory}"}
        
        target_path = project_path / "workspace" / directory
        
        if target_path.exists():
            return {"error": f"Директория уже существует: {directory}"}
        
        # Формирование команды git
        args = ["git", "clone"]
        
        if branch and branch != "main":
            args.extend(["-b", branch])
        
        if depth > 0:
            args.extend(["--depth", str(depth)])
        
        args.extend([url, str(target_path)])
        
        logger.info(f"Клонирование репозитория: {' '.join(args)}")
        
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=300  # Клонирование может занять время
        )
        
        if process.returncode == 0:
            return {
                "success": True,
                "path": directory,
                "stdout": stdout.decode("utf-8", errors="replace")
            }
        else:
            return {
                "error": f"Git clone failed: {stderr.decode('utf-8', errors='replace')}"
            }
            
    except asyncio.TimeoutError:
        return {"error": "Таймаут клонирования репозитория (300с)"}
    except FileNotFoundError:
        return {"error": "git не найден. Установите Git."}
    except Exception as e:
        logger.error(f"Ошибка git clone: {e}")
        return {"error": str(e)}


async def git_command(
    project_path: Path,
    command: str,
    repo_path: str = "."
) -> dict[str, Any]:
    """
    Выполнение Git команды в существующем репозитории.
    
    Args:
        project_path: Путь к проекту
        command: Git команда без префикса 'git'
        repo_path: Путь к репозиторию относительно workspace
        
    Returns:
        {"stdout": "...", "stderr": "...", "returncode": 0} или {"error": "..."}
    """
    try:
        # Проверка безопасности пути
        try:
            repo_dir = safe_join(project_path / "workspace", repo_path)
        except ValueError as e:
            return {"error": f"Небезопасный путь репозитория: {e}"}
        
        if not repo_dir.exists():
            return {"error": f"Директория не найдена: {repo_path}"}
        
        # Проверка что это git репозиторий
        git_dir = repo_dir / ".git"
        if not git_dir.exists():
            return {"error": f"Не git репозиторий: {repo_path}"}
        
        # Формирование полной команды
        full_command = f"git {command}"
        
        # Проверка безопасности команды
        is_safe, error_msg = is_command_safe(full_command)
        if not is_safe:
            return {"error": f"Git команда заблокирована: {error_msg}"}
        
        logger.info(f"Git команда в {repo_path}: {full_command}")
        
        process = await asyncio.create_subprocess_shell(
            full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(repo_dir),
            shell=True
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=60
        )
        
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "returncode": process.returncode,
            "command": command
        }
        
    except asyncio.TimeoutError:
        return {"error": "Таймаут git команды (60с)"}
    except Exception as e:
        logger.error(f"Ошибка git команды: {e}")
        return {"error": str(e)}


def register_system_handlers(tool_registry, project_path: Path) -> None:
    """
    Регистрация всех system ops handlers в реестре.
    
    Args:
        tool_registry: ToolRegistry instance
        project_path: Путь к проекту
    """
    from functools import partial
    
    handlers = {
        "run_command": partial(run_command, project_path),
        "pip_install": partial(pip_install, project_path),
        "git_clone": partial(git_clone, project_path),
        "git_command": partial(git_command, project_path),
    }
    
    for name, handler in handlers.items():
        if tool_registry.has_tool(name):
            tool_registry.register_handler(name, handler)
            logger.debug(f"Зарегистрирован handler для {name}")
        else:
            logger.warning(f"Инструмент {name} не найден в реестре")
