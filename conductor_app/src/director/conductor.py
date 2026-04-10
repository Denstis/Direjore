"""
Conductor — главный оркестратор системы.

Цикл: анализ → план → утверждение → делегирование → проверка → коррекция/финал
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

import yaml

from ..core.lm_client import LMStudioClient
from ..core.model_registry import ModelRegistry
from ..core.tool_registry import ToolRegistry
from .protocol import (
    DirectorActionType,
    DelegateAction,
    AskUserAction,
    FinalAction,
    Plan,
    PlanStep,
    ProjectState,
    ProjectStage,
)

logger = logging.getLogger(__name__)


class Conductor:
    """Главный оркестратор многоагентной системы."""

    def __init__(
        self,
        client: LMStudioClient,
        model_registry: ModelRegistry,
        tool_registry: ToolRegistry,
        project_id: str,
        project_root: Path,
    ):
        self.client = client
        self.model_registry = model_registry
        self.tool_registry = tool_registry
        self.project_id = project_id
        self.project_root = project_root
        self.project_path = project_root / project_id
        
        # Состояние
        self.state: Optional[ProjectState] = None
        self.iteration = 0
        self.max_iterations = 10
        
        # Флаг прерывания
        self.cancel_flag = False
        
        # Загрузка конфигурации Дирижёра
        self.role_config = self._load_role_config()

    def _load_role_config(self) -> dict:
        """Загрузить конфигурацию роли Дирижёра из YAML."""
        roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
        director_yaml = roles_dir / "director.yaml"
        
        if not director_yaml.exists():
            logger.warning("Конфигурация director.yaml не найдена")
            return {}
            
        with open(director_yaml, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    async def initialize(self) -> None:
        """Инициализация проекта и загрузка состояния."""
        logger.info(f"Инициализация проекта {self.project_id}")
        # Создание папок проекта если не существуют
        self.project_path.mkdir(parents=True, exist_ok=True)
        (self.project_path / "workspace").mkdir(exist_ok=True)
        (self.project_path / "memory").mkdir(exist_ok=True)
        (self.project_path / "logs").mkdir(exist_ok=True)
        logger.debug(f"Созданы директории проекта в {self.project_path}")
        
        # Загрузка или создание state.json
        state_file = self.project_path / "state.json"
        if state_file.exists():
            with open(state_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            self.state = ProjectState(**state_data)
            logger.info(f"Загружено состояние проекта {self.project_id}")
            logger.debug(f"Состояние: stage={self.state.stage}, created_at={self.state.created_at}")
        else:
            self.state = ProjectState(
                stage=ProjectStage.IDLE,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
            )
            await self._save_state()
            logger.info(f"Создано новое состояние проекта {self.project_id}")

    async def _save_state(self) -> None:
        """Атомарное сохранение состояния."""
        if not self.state:
            return
            
        state_file = self.project_path / "state.json"
        state_data = self.state.model_dump(mode="json")
        state_data["updated_at"] = datetime.now().isoformat()
        
        # Атомарная запись: temp → rename
        temp_file = state_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)
        
        # На Windows rename может失败 если target существует, поэтому сначала удаляем
        import sys
        if sys.platform == "win32" and state_file.exists():
            state_file.unlink()
        temp_file.rename(state_file)

    async def process_request(self, user_message: str) -> AsyncGenerator[dict, None]:
        """
        Обработка запроса пользователя.
        
        Args:
            user_message: Сообщение от пользователя
            
        Yields:
            События для GUI (статусы, вопросы, результаты)
        """
        logger.info(f"Получен запрос от пользователя: {user_message[:100]}...")
        
        if self.cancel_flag:
            logger.warning("Операция прервана флагом cancel_flag")
            yield {"type": "cancelled", "message": "Операция прервана"}
            return
            
        self.iteration = 0
        
        try:
            # ШАГ 1: Запись задания в память проекта при получении
            logger.info("ШАГ 1: Запись задания в память проекта")
            await self._log_task_assignment(user_message)
            
            # Переключение в стадию планирования
            self.state.stage = ProjectStage.PLANNING
            await self._save_state()
            logger.debug(f"Стадия изменена на: planning")
            yield {"type": "stage_changed", "stage": "planning"}
            
            # Цикл выполнения
            while self.iteration < self.max_iterations and not self.cancel_flag:
                self.iteration += 1
                logger.info(f"Итерация {self.iteration}/{self.max_iterations}")
                
                # Анализ и выбор действия
                logger.debug(f"Начало анализа и выбора действия на итерации {self.iteration}")
                action = await self._analyze_and_decide(user_message)
                logger.debug(f"Выбрано действие: {action.action_type}")
                
                if action.action_type == DirectorActionType.ASK_USER:
                    # Запрос уточнения у пользователя
                    self.state.stage = ProjectStage.WAITING_USER
                    await self._save_state()
                    yield {
                        "type": "ask_user",
                        "question": action.payload.question,
                        "options": action.payload.options,
                    }
                    # Ожидание ответа пользователя (возврат управления GUI)
                    return
                    
                elif action.action_type == DirectorActionType.DELEGATE:
                    # Делегирование исполнителю
                    self.state.stage = ProjectStage.EXECUTING
                    self.state.active_role = action.payload.role
                    await self._save_state()
                    
                    yield {
                        "type": "delegated",
                        "role": action.payload.role,
                        "task": action.payload.task,
                    }
                    
                    # Выполнение агентом (Worker)
                    from ..agents.worker import Worker
                    
                    # Объединяем tools и allowed_tools для передачи Worker
                    all_allowed_tools = list(set(action.payload.tools + action.payload.allowed_tools))
                    
                    worker = Worker(
                        role_name=action.payload.role,
                        task=action.payload.task,
                        tools=all_allowed_tools,
                        context_keys=action.payload.context_keys,
                        conductor=self,
                    )
                    
                    async for event in worker.execute():
                        yield event
                        
                    # ШАГ 2: Запись результатов работы агентов в память проекта
                    logger.info("ШАГ 2: Запись результатов работы агентов в память проекта")
                    if event.get("type") == "agent_done":
                        await self._log_agent_completion(event)
                    
                    # Проверка результата
                    if event.get("type") == "agent_done" and event.get("success"):
                        # Переход к следующему шагу или финал
                        pass
                    else:
                        # Ошибка или требуется коррекция
                        yield {"type": "needs_correction", "error": event.get("error")}
                        
                elif action.action_type == DirectorActionType.FINAL:
                    # ШАГ 3: Проверка директором и принятие решения о завершении
                    logger.info("ШАГ 3: Проверка директором - принятие решения о завершении")
                    
                    # Чтение памяти проекта для принятия решения
                    memory_context = await self._get_project_context()
                    task_history = memory_context.get("task_history", [])
                    completed_tasks = memory_context.get("completed_tasks", [])
                    
                    logger.info(f"Всего задач в истории: {len(task_history)}, завершено: {len(completed_tasks)}")
                    
                    # Завершение
                    self.state.stage = ProjectStage.DONE
                    await self._save_state()
                    
                    yield {
                        "type": "final",
                        "result": action.payload.result,
                        "artifacts": action.payload.artifacts,
                    }
                    return
                    
            # Превышено количество итераций
            self.state.stage = ProjectStage.ERROR
            self.state.last_error = "Превышен лимит итераций"
            await self._save_state()
            yield {"type": "error", "message": "Превышен лимит итераций"}
            
        except Exception as e:
            logger.error(f"Ошибка в процессе выполнения: {e}", exc_info=True)
            self.state.stage = ProjectStage.ERROR
            self.state.last_error = str(e)
            await self._save_state()
            yield {"type": "error", "message": str(e)}

    async def _analyze_and_decide(self, user_message: str) -> Any:
        """
        Анализ запроса и выбор действия.
        
        Returns:
            DirectorResponse с выбранным действием
        """
        logger.debug(f"Начало анализа запроса для выбора действия")
        
        # Выбор модели для Дирижёра
        model_id = self.model_registry.select_for_role(self.role_config)
        if not model_id:
            logger.error("Не удалось выбрать модель для Дирижёра")
            raise ValueError("Не удалось выбрать модель для Дирижёра")
        
        logger.info(f"Выбрана модель для Дирижёра: {model_id}")
        
        # Построение контекста
        system_prompt = self.role_config.get("system_prompt", "")
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Добавление контекста проекта (памяти) - КРИТИЧЕСКИ ВАЖНО
        memory_context = await self._get_project_context()
        state_context = await self._get_state_context()
        
        # Объединяем контексты
        full_context = {}
        if memory_context:
            full_context["memory"] = memory_context
        if state_context:
            full_context["state"] = state_context
            
        if full_context:
            logger.debug(f"Добавлен контекст проекта: {len(json.dumps(full_context))} байт")
            messages.append(
                {"role": "user", "content": f"Контекст проекта (память и состояние):\n{json.dumps(full_context, ensure_ascii=False, indent=2)}"}
            )
        else:
            logger.debug("Контекст проекта пуст")
        
        # Добавляем запрос пользователя
        messages.append({"role": "user", "content": f"Запрос пользователя: {user_message}"})
        
        # Вызов LLM
        logger.info(f"Вызов LLM для анализа запроса (модель: {model_id})")
        response = await self.client.chat_completion(
            model=model_id,
            messages=messages,
            temperature=self.role_config.get("temperature", 0.7),
            max_tokens=self.role_config.get("max_tokens", 1024),
        )
        
        # Парсинг ответа
        raw_content = response.choices[0].message.content
        logger.debug(f"Получен ответ от LLM длиной {len(raw_content)} символов")
        
        # Попытка извлечь JSON
        json_str = self._extract_json(raw_content)
        
        from .protocol import parse_director_action
        director_response = parse_director_action(json_str)
        
        logger.info(f"Действие успешно распарсено: {director_response.action_type}")
        
        # Логирование
        log_file = self.project_path / "logs" / "director_calls.log"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n=== Iteration {self.iteration} ===\n")
            f.write(f"Request: {user_message}\n")
            f.write(f"State: stage={self.state.stage}, step={self.state.current_step}\n")
            f.write(f"Response: {raw_content}\n")
            f.write(f"Parsed: {director_response.model_dump_json()}\n")
            
        return director_response

    def _extract_json(self, text: str) -> str:
        """Извлечение JSON из текста ответа LLM."""
        # Попытка найти JSON между { и }
        start = text.find("{")
        end = text.rfind("}") + 1
        
        if start != -1 and end > start:
            return text[start:end]
            
        return text.strip()

    async def _get_project_context(self) -> dict:
        """Получить контекст проекта из памяти."""
        memory_file = self.project_path / "memory" / "project.json"
        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    async def _get_state_context(self) -> dict:
        """Получить текущее состояние проекта для контекста."""
        if not self.state:
            return {}
            
        return {
            "stage": self.state.stage.value,
            "current_step": self.state.current_step,
            "iteration": self.state.iteration,
            "active_role": self.state.active_role,
            "last_error": self.state.last_error,
        }

    # =============================================================================
    # МЕТОДЫ ДЛЯ АЛГОРИТМА ПЕРЕДАЧИ КОНТЕКСТА
    # =============================================================================

    async def _log_task_assignment(self, user_message: str) -> None:
        """
        ШАГ 1: Запись задания в память проекта при получении.
        
        Args:
            user_message: Текст задания от пользователя
        """
        logger.info(f"Запись задания в память проекта: {user_message[:100]}...")
        
        memory_file = self.project_path / "memory" / "project.json"
        
        # Чтение существующих данных
        data = {}
        if memory_file.exists():
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Ошибка чтения перед записью: {e}")
        
        # Инициализация структуры task_history если не существует
        if "task_history" not in data:
            data["task_history"] = []
        
        # Добавление новой задачи в историю
        task_entry = {
            "id": len(data["task_history"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "task": user_message,
            "status": "assigned",
            "iteration": self.iteration,
        }
        
        data["task_history"].append(task_entry)
        
        # Обновление текущего задания
        data["current_task"] = {
            "id": task_entry["id"],
            "task": user_message,
            "assigned_at": task_entry["timestamp"],
            "status": "in_progress",
        }
        
        # Атомарная запись с использованием os.replace() для кроссплатформенности
        temp_file = memory_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Кроссплатформенное атомарное переименование через os.replace
            import os
            os.replace(str(temp_file), str(memory_file))
            logger.info(f"Задание записано в память проекта под ID {task_entry['id']}")
        except Exception as e:
            logger.error(f"Ошибка записи задания в память: {e}")
            # Очистка temp файла если он остался
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    async def _log_agent_completion(self, event: dict) -> None:
        """
        ШАГ 2: Запись результатов работы агентов в память проекта.
        
        Args:
            event: Событие agent_done с результатами работы
        """
        logger.info("Запись результатов работы агента в память проекта")
        
        memory_file = self.project_path / "memory" / "project.json"
        
        # Чтение существующих данных
        data = {}
        if memory_file.exists():
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"Ошибка чтения перед записью: {e}")
        
        # Извлечение отчёта из события
        report = event.get("report", {})
        success = event.get("success", False)
        
        # Инициализация структуры completed_tasks если не существует
        if "completed_tasks" not in data:
            data["completed_tasks"] = []
        
        # Создание записи о завершённой задаче
        completion_entry = {
            "id": len(data["completed_tasks"]) + 1,
            "timestamp": datetime.now().isoformat(),
            "task_id": data.get("current_task", {}).get("id"),
            "status": "completed" if success else "failed",
            "summary": report.get("summary", ""),
            "files_created": report.get("files_created", []),
            "files_modified": report.get("files_modified", []),
            "errors": report.get("errors", []),
            "artifacts": report.get("artifacts", {}),
            "recommendations": report.get("recommendations", []),
            "tool_calls_count": len(report.get("tool_calls", [])),
        }
        
        data["completed_tasks"].append(completion_entry)
        
        # Обновление статуса текущего задания
        if "current_task" in data:
            data["current_task"]["status"] = "completed" if success else "failed"
            data["current_task"]["completed_at"] = datetime.now().isoformat()
            data["current_task"]["result_summary"] = report.get("summary", "")
        
        # Добавление в общую историю изменений
        if "history" not in data:
            data["history"] = []
        
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "agent_completion",
            "role": self.state.active_role if self.state else "unknown",
            "success": success,
            "summary": report.get("summary", ""),
        }
        data["history"].append(history_entry)
        
        # Атомарная запись с использованием os.replace() для кроссплатформенности
        temp_file = memory_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Кроссплатформенное атомарное переименование через os.replace
            import os
            os.replace(str(temp_file), str(memory_file))
            logger.info(f"Результаты агента записаны в память проекта (успех: {success})")
        except Exception as e:
            logger.error(f"Ошибка записи результатов агента в память: {e}")
            # Очистка temp файла если он остался
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass

    def cancel(self) -> None:
        """Установка флага прерывания."""
        self.cancel_flag = True
        logger.info("Установлен флаг прерывания")

    def reset_cancel(self) -> None:
        """Сброс флага прерывания."""
        self.cancel_flag = False
