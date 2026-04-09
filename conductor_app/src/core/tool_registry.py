"""
Tool Registry — загрузка схем инструментов и маппинг name → handler.

Загружает JSON-описания из config/tools/, регистрирует handlers,
предоставляет семантический поиск по описанию.
"""

import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Реестр инструментов с поддержкой динамической регистрации."""

    def __init__(self, tools_dir: Optional[Path] = None):
        self.tools_dir = tools_dir or Path(__file__).parent.parent.parent / "config" / "tools"
        self._tools: dict[str, dict] = {}  # name → schema
        self._handlers: dict[str, Callable] = {}  # name → async handler
        self._categories: dict[str, list[str]] = {}  # category → [names]

    def load_all(self) -> int:
        """
        Загрузить все инструменты из JSON-файлов в tools_dir.
        
        Returns:
            Количество загруженных инструментов
        """
        if not self.tools_dir.exists():
            logger.warning(f"Директория инструментов не найдена: {self.tools_dir}")
            return 0
            
        count = 0
        for json_file in self.tools_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    tools_data = json.load(f)
                    
                if not isinstance(tools_data, list):
                    logger.warning(f"Ожидается список в {json_file}, пропуск")
                    continue
                    
                for tool_schema in tools_data:
                    name = tool_schema.get("name")
                    if not name:
                        logger.warning(f"Инструмент без имени в {json_file}, пропуск")
                        continue
                        
                    self._tools[name] = tool_schema
                    
                    # Регистрация категории
                    category = tool_schema.get("category", "other")
                    if category not in self._categories:
                        self._categories[category] = []
                    self._categories[category].append(name)
                    
                    count += 1
                    
                logger.debug(f"Загружено инструментов из {json_file.name}: {count}")
                
            except Exception as e:
                logger.error(f"Ошибка загрузки {json_file}: {e}")
                
        logger.info(f"Всего загружено инструментов: {count}")
        return count

    def register_handler(self, name: str, handler: Callable) -> bool:
        """
        Зарегистрировать handler для инструмента.
        
        Args:
            name: Имя инструмента
            handler: Async функция для вызова
            
        Returns:
            True если успешно, False если инструмент не найден
        """
        if name not in self._tools:
            logger.warning(f"Попытка зарегистрировать handler для несуществующего инструмента: {name}")
            return False
            
        self._handlers[name] = handler
        logger.debug(f"Зарегистрирован handler для {name}")
        return True

    def get_schema(self, name: str) -> Optional[dict]:
        """Получить схему инструмента по имени."""
        return self._tools.get(name)

    def get_handler(self, name: str) -> Optional[Callable]:
        """Получить handler инструмента по имени."""
        return self._handlers.get(name)

    def has_tool(self, name: str) -> bool:
        """Проверить наличие инструмента."""
        return name in self._tools

    def has_handler(self, name: str) -> bool:
        """Проверить наличие зарегистрированного handler."""
        return name in self._handlers

    def get_tools_for_openai(self, names: Optional[list[str]] = None) -> list[dict]:
        """
        Получить схемы инструментов в формате OpenAI API.
        
        Args:
            names: Список имён инструментов (если None — все)
            
        Returns:
            Список в формате [{"type": "function", "function": {...}}]
        """
        result = []
        tool_names = names if names else list(self._tools.keys())
        
        for name in tool_names:
            if name not in self._tools:
                continue
                
            schema = self._tools[name]
            openai_format = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": schema.get("description", ""),
                    "parameters": schema.get("parameters", {}),
                }
            }
            result.append(openai_format)
            
        return result

    def search_by_description(self, query: str, threshold: float = 0.3) -> list[str]:
        """
        Семантический поиск инструментов по описанию (простая версия).
        
        Args:
            query: Поисковый запрос
            threshold: Порог схожести (0-1)
            
        Returns:
            Список подходящих имён инструментов
        """
        # Простой поиск по ключевым словам
        query_lower = query.lower()
        results = []
        
        for name, schema in self._tools.items():
            description = schema.get("description", "").lower()
            
            # Проверка вхождения слов из запроса
            words = query_lower.split()
            matches = sum(1 for word in words if word in description)
            score = matches / len(words) if words else 0
            
            if score >= threshold:
                results.append(name)
                
        return results

    def list_categories(self) -> list[str]:
        """Вернуть список категорий."""
        return list(self._categories.keys())

    def get_tools_by_category(self, category: str) -> list[str]:
        """Вернуть инструменты категории."""
        return self._categories.get(category, [])

    def validate_arguments(self, tool_name: str, arguments: dict) -> tuple[bool, Optional[str]]:
        """
        Валидировать аргументы инструмента против схемы.
        
        Args:
            tool_name: Имя инструмента
            arguments: Аргументы для валидации
            
        Returns:
            (valid, error_message)
        """
        if tool_name not in self._tools:
            return False, f"Инструмент {tool_name} не найден"
            
        schema = self._tools[tool_name]
        params_schema = schema.get("parameters", {})
        required = params_schema.get("required", [])
        properties = params_schema.get("properties", {})
        
        # Проверка обязательных параметров
        for req_param in required:
            if req_param not in arguments:
                return False, f"Обязательный параметр отсутствует: {req_param}"
                
        # Проверка типов (базовая)
        for param_name, param_value in arguments.items():
            if param_name not in properties:
                return False, f"Неизвестный параметр: {param_name}"
                
            expected_type = properties[param_name].get("type")
            if expected_type:
                if not self._check_type(param_value, expected_type):
                    return False, f"Неверный тип параметра {param_name}: ожидается {expected_type}"
                    
        return True, None

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Проверка типа значения."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_python_type = type_map.get(expected_type)
        if not expected_python_type:
            return True  # Неизвестный тип, пропускаем проверку
        return isinstance(value, expected_python_type)
