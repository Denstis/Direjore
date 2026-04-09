"""
Platform Utilities - Кроссплатформенные утилиты

Модуль для определения операционной системы и адаптации путей/команд.
Автоматически выбирает правильную оболочку и разделители путей.
"""

import os
import sys
import platform
from pathlib import Path
from typing import Optional


class PlatformDetector:
    """Определение и утилиты платформы"""
    
    def __init__(self):
        self._os_type: Optional[str] = None
        self._detect()
    
    def _detect(self):
        """Определить тип ОС"""
        system = platform.system().lower()
        
        if system == "windows":
            self._os_type = "windows"
        elif system in ("linux", "darwin"):  # Darwin = macOS
            self._os_type = "unix"
        else:
            self._os_type = "unknown"
    
    @property
    def os_type(self) -> str:
        """Тип ОС: 'windows', 'unix', или 'unknown'"""
        return self._os_type
    
    @property
    def is_windows(self) -> bool:
        """Работаем ли на Windows"""
        return self._os_type == "windows"
    
    @property
    def is_unix(self) -> bool:
        """Работаем ли на Unix-подобной системе (Linux/macOS)"""
        return self._os_type == "unix"
    
    @property
    def path_separator(self) -> str:
        """Разделитель путей: '\\' для Windows, '/' для Unix"""
        return "\\" if self.is_windows else "/"
    
    @property
    def shell_command(self) -> list:
        """Команда для запуска оболочки"""
        if self.is_windows:
            return ["cmd.exe", "/c"]
        else:
            return ["/bin/bash", "-c"]
    
    @property
    def python_executable(self) -> str:
        """Путь к исполняемому файлу Python"""
        if self.is_windows:
            return "python.exe"
        else:
            return "python3"
    
    @property
    def pip_command(self) -> str:
        """Команда pip"""
        if self.is_windows:
            return "pip"
        else:
            return "pip3"
    
    def safe_join(self, base_path: str, *paths: str) -> str:
        """
        Безопасное соединение путей с защитой от выхода за пределы base_path.
        
        Args:
            base_path: Базовый путь (корень)
            *paths: Дополнительные компоненты пути
            
        Returns:
            Абсолютный нормализованный путь
            
        Raises:
            ValueError: Если результат выходит за пределы base_path
        """
        base = Path(base_path).resolve()
        
        # Соединяем все компоненты
        result = base
        for p in paths:
            # Очищаем путь от опасных компонентов
            clean_p = p.replace("..", "").replace("//", "/")
            result = result / clean_p
        
        result = result.resolve()
        
        # Проверяем, что результат внутри base_path
        try:
            result.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Path traversal detected! Result '{result}' is outside base '{base}'"
            )
        
        return str(result)
    
    def normalize_path(self, path: str) -> str:
        """Нормализовать путь для текущей ОС"""
        # Заменяем разделители
        if self.is_windows:
            return path.replace("/", "\\")
        else:
            return path.replace("\\", "/")
    
    def get_env_var(self, name: str, default: str = "") -> str:
        """Получить переменную окружения"""
        return os.environ.get(name, default)
    
    def is_safe_command(self, command: str) -> tuple[bool, str]:
        """
        Проверить команду на безопасность.
        
        Returns:
            (is_safe, reason): Кортеж из флага безопасности и причины
        """
        dangerous_patterns = [
            "sudo",
            "rm -rf",
            "format",
            "del /f /s /q",
            "rmdir /s /q",
            "> \\\\",
            ">> \\\\",
            "net use",
            "reg delete",
            "shutdown",
            "restart",
            "reboot",
        ]
        
        cmd_lower = command.lower()
        
        for pattern in dangerous_patterns:
            if pattern in cmd_lower:
                return False, f"Dangerous pattern detected: '{pattern}'"
        
        # Check for absolute paths outside workspace
        if self.is_windows:
            # Windows drive letter check (e.g., C:\)
            if len(cmd_lower) > 2 and cmd_lower[1] == ':' and 'workspace' not in cmd_lower:
                # Allow only relative paths or paths within workspace
                pass  # Additional validation can be added here
        else:
            if cmd_lower.startswith("/") and "workspace" not in cmd_lower:
                return False, "Absolute paths outside workspace are not allowed"
        
        return True, "OK"


# Глобальный экземпляр
platform_utils = PlatformDetector()


def get_platform() -> str:
    """Получить тип текущей платформы"""
    return platform_utils.os_type


def safe_path_join(base: str, *paths: str) -> str:
    """Безопасно соединить пути"""
    return platform_utils.safe_join(base, *paths)


def is_windows() -> bool:
    """Проверка на Windows"""
    return platform_utils.is_windows


def get_shell_command() -> list:
    """Получить команду оболочки"""
    return platform_utils.shell_command
