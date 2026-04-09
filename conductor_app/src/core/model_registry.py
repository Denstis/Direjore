"""
Model Registry — управление моделями, фильтрация и выбор по роли.

Загружает информацию о моделях из:
1. LM Studio API (динамически)
2. config/models.json (ручные оверрайды)
"""

import json
import logging
from pathlib import Path
from typing import Optional

from .lm_client import LMStudioClient, ModelInfo

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Реестр моделей с поддержкой фильтрации и выбора."""

    def __init__(self, client: LMStudioClient, config_path: Optional[Path] = None):
        self.client = client
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config" / "models.json"
        self._models: dict[str, ModelInfo] = {}
        self._overrides: dict = {}

    async def load(self) -> None:
        """Загрузить модели из API и применить оверрайды из конфига."""
        # Загрузка из API
        api_models = await self.client.list_models()
        for model in api_models:
            self._models[model.id] = model
            
        # Применение оверрайдов из config/models.json
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    
                # Загрузка кэшированных моделей
                for model_data in config.get("models", []):
                    model_id = model_data["id"]
                    if model_id in self._models:
                        # Обновление существующей модели
                        existing = self._models[model_id]
                        existing.context_window = model_data.get("context_window", existing.context_window)
                        existing.supports_tools = model_data.get("supports_tools", existing.supports_tools)
                        existing.supports_parallel_tools = model_data.get(
                            "supports_parallel_tools", existing.supports_parallel_tools
                        )
                        existing.quantization = model_data.get("quantization")
                    else:
                        # Добавление новой модели из конфига
                        self._models[model_id] = ModelInfo(
                            id=model_id,
                            context_window=model_data.get("context_window", 8192),
                            supports_tools=model_data.get("supports_tools", False),
                            supports_parallel_tools=model_data.get("supports_parallel_tools", False),
                            quantization=model_data.get("quantization"),
                        )
                        
                # Глобальные оверрайды
                self._overrides = config.get("overrides", {})
                
                logger.info(f"Загружено {len(self._models)} моделей")
                
            except Exception as e:
                logger.error(f"Ошибка загрузки config/models.json: {e}")

    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        """Получить информацию о модели по ID."""
        return self._models.get(model_id)

    def list_models(self) -> list[ModelInfo]:
        """Вернуть список всех моделей."""
        return list(self._models.values())

    def filter_models(
        self,
        min_context: Optional[int] = None,
        requires_tools: bool = False,
        requires_parallel_tools: bool = False,
    ) -> list[ModelInfo]:
        """
        Фильтрация моделей по критериям.
        
        Args:
            min_context: Минимальное контекстное окно
            requires_tools: Требуется поддержка tools
            requires_parallel_tools: Требуется поддержка parallel tool calls
            
        Returns:
            Список подходящих моделей
        """
        result = []
        for model in self._models.values():
            if min_context and model.context_window < min_context:
                continue
            if requires_tools and not model.supports_tools:
                continue
            if requires_parallel_tools and not model.supports_parallel_tools:
                continue
            result.append(model)
        return result

    def select_for_role(self, role_config: dict) -> Optional[str]:
        """
        Выбрать модель для роли на основе конфигурации роли.
        
        Args:
            role_config: Конфигурация роли из YAML (с ключом model_preference)
            
        Returns:
            ID выбранной модели или None
        """
        preferred = role_config.get("model_preference")
        
        if preferred:
            # Проверка предпочтительной модели
            model = self.get_model(preferred)
            if model:
                return preferred
            logger.warning(f"Предпочтительная модель {preferred} не найдена")
        
        # Fallback: первая модель с поддержкой tools
        models_with_tools = self.filter_models(requires_tools=True)
        if models_with_tools:
            return models_with_tools[0].id
            
        # Last resort: любая доступная модель
        all_models = self.list_models()
        if all_models:
            return all_models[0].id
            
        return None

    def apply_manual_override(self, model_id: str, **kwargs) -> None:
        """
        Применить ручной оверрайд для модели.
        
        Args:
            model_id: ID модели
            kwargs: Поля для обновления (context_window, supports_tools, etc.)
        """
        if model_id not in self._models:
            self._models[model_id] = ModelInfo(id=model_id)
            
        model = self._models[model_id]
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
                
        logger.info(f"Применён оверрайд для {model_id}: {kwargs}")
