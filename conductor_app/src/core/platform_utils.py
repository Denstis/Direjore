"""
Platform Utilities - Кроссплатформенные утилиты

Модуль для определения операционной системы и адаптации путей/команд.
Автоматически выбирает правильную оболочку и разделители путей.
"""

import os
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


# Глобальный экземпляр
platform_utils = PlatformDetector()
