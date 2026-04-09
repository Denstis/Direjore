"""
Worker — агент-исполнитель роли.

Цикл: chat → tool_calls → execute → append → retry/final
Принудительный callback к Director после завершения.
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

from ..core.lm_client import LMStudioClient
from ..core.tool_registry import ToolRegistry
from ..director.protocol import AgentReport, AgentStatus, ToolCallResult

logger = logging.getLogger(__name__)


class Worker:
    """Агент-исполнитель роли."""

    def __init__(
        self,
        role_name: str,
        task: str,
        tools: list[str],
        context_keys: list[str],
        conductor: Any,  # Conductor reference
    ):
        self.role_name = role_name
        self.task = task
        self.allowed_tools = tools
        self.context_keys = context_keys
        self.conductor = conductor
        
        # Загрузка конфигурации роли
        self.role_config = self._load_role_config()
        
        # Состояние
        self.messages: list[dict] = []
        self.tool_results: list[ToolCallResult] = []
        self.max_tool_iterations = 5
        
        # Регистрии из кондуктора
        self.client = conductor.client
        self.tool_registry = conductor.tool_registry
        self.model_registry = conductor.model_registry

    def _load_role_config(self) -> dict:
        """Загрузить конфигурацию роли из YAML."""
        roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
        role_yaml = roles_dir / f"{self.role_name}.yaml"
        
        if not role_yaml.exists():
            logger.warning(f"Конфигурация роли {self.role_name} не найдена")
            return {}
            
        with open(role_yaml, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    async def execute(self):
        """
        Выполнение задачи роли.
        
        Yields:
            События для GUI (tool_call, progress, done)
        """
        logger.info(f"Начало выполнения роли {self.role_name}: {self.task}")
        
        try:
            # Выбор модели для роли
            model_id = self.model_registry.select_for_role(self.role_config)
            if not model_id:
                raise ValueError(f"Не удалось выбрать модель для роли {self.role_name}")
                
            # Построение начального контекста
            system_prompt = self.role_config.get("system_prompt", "")
            
            self.messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Задача: {self.task}"},
            ]
            
            # Добавление контекста проекта
            if self.context_keys:
                project_context = await self._get_project_context(self.context_keys)
                if project_context:
                    self.messages.insert(
                        1,
                        {"role": "user", "content": f"Контекст:\n{json.dumps(project_context, ensure_ascii=False, indent=2)}"}
                    )
                    
            # Получение разрешённых инструментов
            allowed_schemas = self.tool_registry.get_tools_for_openai(self.allowed_tools)
            
            # Цикл выполнения
            iteration = 0
            while iteration < self.max_tool_iterations:
                iteration += 1
                
                # Вызов LLM
                response = await self.client.chat_completion(
                    model=model_id,
                    messages=self.messages,
                    tools=allowed_schemas if iteration == 1 else None,  # Tools только в первом запросе
                    temperature=self.role_config.get("temperature", 0.3),
                    max_tokens=self.role_config.get("max_tokens", 2048),
                )
                
                assistant_message = response.choices[0].message
                self.messages.append({"role": "assistant", "content": assistant_message.content})
                
                # Проверка на tool_calls
                if assistant_message.tool_calls:
                    # Выполнение инструментов
                    for tool_call in assistant_message.tool_calls:
                        if self.conductor.cancel_flag:
                            yield {"type": "cancelled", "message": "Операция прервана"}
                            return
                            
                        tool_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        yield {
                            "type": "tool_call",
                            "tool": tool_name,
                            "arguments": arguments,
                        }
                        
                        # Валидация аргументов
                        valid, error = self.tool_registry.validate_arguments(tool_name, arguments)
                        if not valid:
                            result = {"error": error}
                            success = False
                        else:
                            # Выполнение инструмента
                            handler = self.tool_registry.get_handler(tool_name)
                            if not handler:
                                result = {"error": f"Handler не найден для {tool_name}"}
                                success = False
                            else:
                                try:
                                    # Handler уже имеет project_path через partial
                                    result = await handler(**arguments)
                                    success = True
                                except Exception as e:
                                    result = {"error": str(e)}
                                    success = False
                                    
                        # Сохранение результата
                        tool_result = ToolCallResult(
                            tool_name=tool_name,
                            arguments=arguments,
                            success=success,
                            result=result,
                            error=result.get("error") if isinstance(result, dict) else None,
                        )
                        self.tool_results.append(tool_result)
                        
                        # Добавление в историю
                        self.messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                        
                        yield {
                            "type": "tool_result",
                            "tool": tool_name,
                            "success": success,
                            "result": result,
                        }
                        
                else:
                    # Нет tool_calls — формирование финального отчёта
                    break
                    
            # Формирование отчёта
            report = await self._generate_report(model_id)
            
            yield {
                "type": "agent_done",
                "success": report.status == AgentStatus.SUCCESS,
                "report": report.model_dump(mode="json"),
            }
            
            # Логирование
            await self._log_execution()
            
        except Exception as e:
            logger.error(f"Ошибка выполнения роли {self.role_name}: {e}", exc_info=True)
            yield {
                "type": "agent_error",
                "error": str(e),
            }

    async def _generate_report(self, model_id: str) -> AgentReport:
        """Генерация финального отчёта через LLM."""
        prompt = """
Сформируй JSON-отчёт о выполненной задаче в строгом формате:
{
    "status": "success|error|partial",
    "summary": "Краткое описание выполненного",
    "files_created": ["путь/к/файлу"],
    "files_modified": ["путь/к/файлу"],
    "errors": [],
    "artifacts": {},
    "recommendations": []
}
"""
        self.messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat_completion(
            model=model_id,
            messages=self.messages,
            temperature=0.3,
            max_tokens=512,
        )
        
        raw_content = response.choices[0].message.content
        
        # Извлечение JSON
        start = raw_content.find("{")
        end = raw_content.rfind("}") + 1
        json_str = raw_content[start:end] if start != -1 else raw_content
        
        try:
            report = AgentReport.model_validate_json(json_str)
        except Exception:
            # Fallback
            report = AgentReport(
                status=AgentStatus.SUCCESS,
                summary=raw_content[:500],
            )
            
        # Добавление tool_results
        report.tool_calls = self.tool_results
        
        return report

    async def _get_project_context(self, keys: list[str]) -> dict:
        """Получить контекст проекта по ключам."""
        memory_file = self.conductor.project_path / "memory" / "project.json"
        if not memory_file.exists():
            return {}
            
        with open(memory_file, "r", encoding="utf-8") as f:
            all_data = json.load(f)
            
        if not keys:
            return all_data
            
        return {k: all_data.get(k) for k in keys if k in all_data}

    async def _log_execution(self) -> None:
        """Логирование выполнения."""
        log_file = self.conductor.project_path / "logs" / f"{self.role_name}_calls.log"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n=== Execution {datetime.now().isoformat()} ===\n")
            f.write(f"Task: {self.task}\n")
            f.write(f"Tool calls: {len(self.tool_results)}\n")
            for tr in self.tool_results:
                f.write(f"  - {tr.tool_name}: {'OK' if tr.success else 'ERROR'}\n")
