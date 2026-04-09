"""
LM Studio Client — обёртка над OpenAI-совместимым API LM Studio.

Поддерживает:
- Chat completions с tools/tool_choice
- Streaming (SSE)
- Получение списка моделей
- Нативный API для расширенных параметров (context_length и др.)
"""

import asyncio
import json
import logging
from typing import Any, Optional
from dataclasses import dataclass

import aiohttp
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Информация о модели."""
    id: str
    context_window: int = 8192
    supports_tools: bool = False
    supports_parallel_tools: bool = False
    quantization: Optional[str] = None


class LMStudioClient:
    """Клиент для работы с LM Studio Server."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        api_key: str = "lm-studio",
        timeout: int = 120
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        
        # OpenAI-совместимый клиент
        self.openai_client = AsyncOpenAI(
            base_url=f"{self.base_url}/v1",
            api_key=self.api_key,
            timeout=self.timeout
        )
        
        # Кэш моделей
        self._models_cache: dict[str, ModelInfo] = {}

    async def list_models(self) -> list[ModelInfo]:
        """Получить список доступных моделей."""
        logger.info(f"Попытка подключения к LM Studio по адресу: {self.base_url}/v1/models")
        try:
            logger.debug(f"Инициализация запроса к API LM Studio")
            response = await self.openai_client.models.list()
            logger.info(f"Успешно получено {len(response.data)} моделей от LM Studio")
            models = []
            for model in response.data:
                info = ModelInfo(id=model.id)
                # Попытка получить дополнительную информацию из нативного API
                native_info = await self._get_native_model_info(model.id)
                if native_info:
                    info.context_window = native_info.get("context_length", info.context_window)
                models.append(info)
                self._models_cache[model.id] = info
                logger.debug(f"Добавлена модель в кэш: {model.id}")
            return models
        except Exception as e:
            logger.error(f"Ошибка получения списка моделей: {e}")
            logger.error(f"Проверьте, что LM Studio Server запущен и доступен по адресу {self.base_url}")
            return []

    async def _get_native_model_info(self, model_id: str) -> Optional[dict]:
        """Получить расширенную информацию о модели через нативный API."""
        try:
            logger.debug(f"Запрос нативной информации о модели {model_id} по адресу {self.base_url}/api/v1/models/{model_id}")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v1/models/{model_id}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    logger.debug(f"Статус ответа нативного API: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        # LM Studio может возвращать данные в разных форматах
                        # Проверяем наличие ключей для определения поддержки tools
                        result = {}
                        if "context_length" in data:
                            result["context_length"] = data["context_length"]
                        # Проверяем поддержку tools по наличию capabilities или других признаков
                        if "capabilities" in data:
                            caps = data["capabilities"]
                            if isinstance(caps, dict):
                                result["supports_tools"] = caps.get("tools", False)
                                result["supports_parallel_tools"] = caps.get("parallel_tool_calls", False)
                        return result if result else data
        except Exception as e:
            logger.debug(f"Не удалось получить нативную инфо о модели {model_id}: {e}")
        return None

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        parallel_tool_calls: bool = False,
        **kwargs
    ) -> Any:
        """
        Вызов chat completions с поддержкой tools.
        
        Args:
            model: ID модели
            messages: Список сообщений в формате OpenAI
            tools: Список инструментов в формате OpenAI
            tool_choice: "auto", "none", "required", или {"type": "function", "function": {"name": "..."]]
            temperature: Температура генерации
            top_p: Top-p sampling
            max_tokens: Максимум токенов в ответе
            stream: Включить streaming
            parallel_tool_calls: Разрешить параллельный вызов инструментов
            
        Returns:
            Response object от OpenAI клиента
        """
        try:
            # Подготовка аргументов
            args = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "stream": stream,
            }
            
            if max_tokens:
                args["max_tokens"] = max_tokens
                
            if tools:
                args["tools"] = tools
                # tool_choice="auto" по умолчанию если есть tools
                if tool_choice:
                    args["tool_choice"] = tool_choice
                else:
                    args["tool_choice"] = "auto"
                    
            # parallel_tool_calls поддерживается не всеми моделями
            if not parallel_tool_calls:
                # Явно отключаем если модель не поддерживает
                pass  # LM Studio игнорирует этот параметр для GGUF
            
            # Добавляем дополнительные аргументы
            args.update(kwargs)
            
            logger.info(f"Вызов chat_completion для модели {model}, tools={len(tools) if tools else 0}, stream={stream}")
            logger.debug(f"Параметры запроса: temperature={temperature}, max_tokens={max_tokens}, top_p={top_p}")
            logger.debug(f"Количество сообщений в запросе: {len(messages)}")
            
            response = await self.openai_client.chat.completions.create(**args)
            
            logger.debug(f"Получен ответ от API для модели {model}")
            
            if stream:
                return response  # Async generator
            else:
                # Логирование для отладки
                if hasattr(response, 'usage') and response.usage:
                    logger.info(
                        f"Токены: input={response.usage.prompt_tokens}, "
                        f"output={response.usage.completion_tokens}"
                    )
                else:
                    logger.debug("Ответ получен (информация о использовании токенов недоступна)")
                return response
                
        except Exception as e:
            logger.error(f"Ошибка chat_completion: {e}")
            raise

    async def get_context_length(self, model: str) -> int:
        """Получить контекстное окно модели."""
        if model in self._models_cache:
            return self._models_cache[model].context_window
            
        # Попытка получить из нативного API
        info = await self._get_native_model_info(model)
        if info and "context_length" in info:
            return info["context_length"]
            
        # Значение по умолчанию
        return 8192

    def update_model_cache(self, model_id: str, info: ModelInfo):
        """Обновить кэш информации о модели (из config/models.json)."""
        self._models_cache[model_id] = info

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Получить информацию о модели из кэша."""
        return self._models_cache.get(model_id)
