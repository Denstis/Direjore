"""
Pydantic-протоколы для всех JSON-ответов LLM.

Строгая валидация действий Дирижёра и отчётов агентов.
"""

import re
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# =============================================================================
# ДЕЙСТВИЯ ДИРИЖЁРА
# =============================================================================

class DirectorActionType(str, Enum):
    """Типы действий Дирижёра."""
    DELEGATE = "delegate"
    ASK_USER = "ask_user"
    FINAL = "final"
    QUERY_TOOLS = "query_tools"


class DelegateAction(BaseModel):
    """Действие: делегирование задачи исполнителю."""
    action: DirectorActionType = DirectorActionType.DELEGATE
    role: str = Field(..., description="Роль исполнителя: coder, researcher, tester")
    task: str = Field(..., description="Описание задачи для исполнителя")
    tools: list[str] = Field(default_factory=list, description="Разрешённые инструменты")
    context_keys: list[str] = Field(
        default_factory=list,
        description="Ключи контекста проекта для передачи"
    )
    timeout_seconds: int = Field(default=300, description="Таймаут выполнения")


class AskUserAction(BaseModel):
    """Действие: запрос уточнения у пользователя."""
    action: DirectorActionType = DirectorActionType.ASK_USER
    question: str = Field(..., description="Вопрос пользователю")
    options: list[str] = Field(
        default_factory=list,
        description="Варианты ответов (опционально)"
    )


class FinalAction(BaseModel):
    """Действие: завершение задачи."""
    action: DirectorActionType = DirectorActionType.FINAL
    result: str = Field(..., description="Итоговый результат")
    artifacts: dict[str, Any] = Field(
        default_factory=dict,
        description="Артефакты: пути к файлам, данные"
    )


class QueryToolsAction(BaseModel):
    """Действие: запрос списка доступных инструментов."""
    action: DirectorActionType = DirectorActionType.QUERY_TOOLS
    category: Optional[str] = Field(None, description="Фильтр по категории")
    search_query: Optional[str] = Field(None, description="Поисковый запрос")


class DirectorResponse(BaseModel):
    """Универсальный ответ Дирижёра."""
    action: DirectorActionType
    role: Optional[str] = None
    task: Optional[str] = None
    tools: list[str] = Field(default_factory=list)
    context_keys: list[str] = Field(default_factory=list)
    timeout_seconds: int = 300
    question: Optional[str] = None
    options: list[str] = Field(default_factory=list)
    result: Optional[str] = None
    artifacts: dict[str, Any] = Field(default_factory=dict)
    category: Optional[str] = None
    search_query: Optional[str] = None
    
    @property
    def action_type(self) -> DirectorActionType:
        return self.action
    
    @property
    def payload(self):
        return self


# =============================================================================
# ОТЧЁТЫ АГЕНТОВ
# =============================================================================

class AgentStatus(str, Enum):
    """Статусы выполнения агента."""
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class ToolCallResult(BaseModel):
    """Результат вызова инструмента."""
    tool_name: str
    arguments: dict[str, Any]
    success: bool
    result: Any
    error: Optional[str] = None


class AgentReport(BaseModel):
    """Отчёт агента о выполнении задачи."""
    status: AgentStatus
    summary: str = Field(..., description="Краткое описание выполненного")
    files_created: list[str] = Field(default_factory=list)
    files_modified: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallResult] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)


# =============================================================================
# ПЛАНЫ И ШАГИ
# =============================================================================

class PlanStep(BaseModel):
    """Шаг плана."""
    step_number: int
    description: str
    role: str
    estimated_complexity: str = Field(
        "medium",
        description="low, medium, high"
    )
    tools_needed: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """План выполнения задачи."""
    goal: str
    steps: list[PlanStep]
    total_steps: int
    estimated_iterations: int = Field(
        default=1,
        description="Ожидаемое количество итераций"
    )


# =============================================================================
# СТАТУСЫ ПРОЕКТА
# =============================================================================

class ProjectStage(str, Enum):
    """Стадии проекта."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_USER = "waiting_user"
    REVIEW = "review"
    DONE = "done"
    ERROR = "error"


class ProjectState(BaseModel):
    """Состояние проекта."""
    stage: ProjectStage
    current_plan: Optional[Plan] = None
    current_step: int = 0
    active_role: Optional[str] = None
    iteration: int = 0
    last_error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


# =============================================================================
# ВАЛИДАЦИЯ JSON ОТ LLM
# =============================================================================

def parse_director_action(json_str: str) -> DirectorResponse:
    """
    Парсинг JSON ответа от Дирижёра с валидацией.
    
    Args:
        json_str: Сырой JSON от LLM
        
    Returns:
        Валидированный DirectorResponse
        
    Raises:
        ValidationError при невалидном JSON
    """
    from pydantic import ValidationError
    import re
    
    try:
        # Попытка прямого парсинга
        data = DirectorResponse.model_validate_json(json_str)
        return data
    except ValidationError as e:
        # Попытка исправить частые ошибки LLM
        # Если ошибка в enum (action_type), пробуем нормализовать значение
        error_str = str(e)
        
        # Извлекаем JSON из текста если он обёрнут в markdown или другой текст
        json_str = _extract_json_from_text(json_str)
        
        try:
            # Повторная попытка после извлечения JSON
            data = DirectorResponse.model_validate_json(json_str)
            return data
        except ValidationError:
            pass
        
        raise ValueError(f"Невалидный JSON от Дирижёра: {e}")


def _extract_json_from_text(text: str) -> str:
    """Извлечь JSON из текста (например, из markdown блока)."""
    if not text:
        return ""
    
    # Поиск JSON между ```json и ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    
    # Поиск первого { и последнего }
    start = text.find("{")
    end = text.rfind("}") + 1
    
    if start != -1 and end > start:
        return text[start:end]
    
    return text.strip()


def parse_agent_report(json_str: str) -> AgentReport:
    """
    Парсинг JSON отчёта агента.
    
    Args:
        json_str: Сырой JSON от LLM
        
    Returns:
        Валидированный AgentReport
    """
    return AgentReport.model_validate_json(json_str)
