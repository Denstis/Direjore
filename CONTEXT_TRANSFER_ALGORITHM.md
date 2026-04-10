# Алгоритм передачи контекста для Директора

## Цель
Обеспечить понимание директором текущего состояния проекта через единую систему памяти, чтобы он мог принимать обоснованные решения о продолжении или завершении работы.

## Принципы работы

### 1. Память проекта (project.json)
Единое хранилище контекста в формате JSON, доступное всем агентам системы.

**Структура:**
```json
{
  "task_log": [
    {
      "timestamp": "2025-01-15T10:00:00",
      "type": "task_received|task_completed|decision_made",
      "description": "Описание события",
      "details": {...},
      "result": {...}
    }
  ],
  "current_task": {
    "id": "...",
    "description": "...",
    "status": "pending|in_progress|completed|failed",
    "assigned_to": "role_name",
    "created_at": "...",
    "completed_at": "..."
  },
  "completed_tasks": [...],
  "decisions": [
    {
      "timestamp": "...",
      "decision": "continue|complete|change_direction",
      "reason": "..."
    }
  ],
  "artifacts": {...},
  "errors": [...]
}
```

## Алгоритм работы

### Этап 1: Получение задания (запись в память)

**Когда:** Директор получает запрос от пользователя

**Действия:**
1. Создать запись в `task_log` с типом `task_received`
2. Обновить `current_task`:
   - Установить `status = "pending"`
   - Записать `description`, `created_at`
3. Сохранить состояние в `project.json`

**Код (Conductor.process_request):**
```python
async def process_request(self, user_message: str) -> AsyncGenerator[dict, None]:
    # Шаг 1: Записать получение задания в память
    await self._log_task_received(user_message)
    
    # Шаг 2: Переключение в стадию планирования
    self.state.stage = ProjectStage.PLANNING
    await self._save_state()
    
    # ... остальная логика
```

**Метод `_log_task_received`:**
```python
async def _log_task_received(self, task_description: str) -> None:
    """Записать получение нового задания в память проекта."""
    from datetime import datetime
    
    memory_file = self.project_path / "memory" / "project.json"
    
    # Чтение существующих данных
    data = {}
    if memory_file.exists():
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    # Инициализация структуры
    if "task_log" not in data:
        data["task_log"] = []
    if "completed_tasks" not in data:
        data["completed_tasks"] = []
    
    # Архивирование текущей задачи если есть
    if data.get("current_task"):
        data["completed_tasks"].append(data["current_task"])
    
    # Создание новой записи
    timestamp = datetime.now().isoformat()
    task_id = f"task_{len(data['task_log']) + 1}"
    
    data["current_task"] = {
        "id": task_id,
        "description": task_description,
        "status": "pending",
        "assigned_to": None,
        "created_at": timestamp,
        "completed_at": None
    }
    
    # Добавление в лог
    data["task_log"].append({
        "timestamp": timestamp,
        "type": "task_received",
        "description": task_description,
        "task_id": task_id
    })
    
    # Атомарная запись
    temp_file = memory_file.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.rename(memory_file)
    
    logger.info(f"Задание записано в память проекта: {task_id}")
```

---

### Этап 2: Делегирование агенту (обновление статуса)

**Когда:** Директор принимает решение делегировать задачу

**Действия:**
1. Обновить `current_task.status = "in_progress"`
2. Записать `assigned_to = role_name`
3. Добавить в `task_log` запись типа `task_delegated`

**Код (Conductor.process_request):**
```python
elif action.action_type == DirectorActionType.DELEGATE:
    # Обновление статуса задачи
    await self._log_task_delegated(action.payload.role, action.payload.task)
    
    self.state.stage = ProjectStage.EXECUTING
    self.state.active_role = action.payload.role
    await self._save_state()
    
    # ... выполнение агентом
```

**Метод `_log_task_delegated`:**
```python
async def _log_task_delegated(self, role: str, task: str) -> None:
    """Записать делегирование задачи агенту."""
    from datetime import datetime
    
    memory_file = self.project_path / "memory" / "project.json"
    
    data = {}
    if memory_file.exists():
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    timestamp = datetime.now().isoformat()
    
    # Обновление текущей задачи
    if data.get("current_task"):
        data["current_task"]["status"] = "in_progress"
        data["current_task"]["assigned_to"] = role
        data["current_task"]["updated_at"] = timestamp
    
    # Логирование
    data["task_log"].append({
        "timestamp": timestamp,
        "type": "task_delegated",
        "role": role,
        "task": task,
        "task_id": data.get("current_task", {}).get("id")
    })
    
    # Запись
    temp_file = memory_file.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.rename(memory_file)
```

---

### Этап 3: Завершение работы агента (запись результатов)

**Когда:** Агент завершает выполнение (успешно или с ошибкой)

**Действия:**
1. Получить отчёт от агента (AgentReport)
2. Обновить `current_task`:
   - `status = "completed"` или `"failed"`
   - `completed_at = timestamp`
   - Сохранить `artifacts`, `files_created`, `files_modified`
3. Добавить в `task_log` запись типа `task_completed`
4. При ошибках добавить в `errors`

**Код (Conductor.process_request):**
```python
async for event in worker.execute():
    yield event
    
# После завершения работы агента
if event.get("type") == "agent_done":
    report = event.get("report")
    await self._log_task_completed(report)
    
    if event.get("success"):
        # Задача выполнена - переход к проверке
        pass
    else:
        # Ошибка - требуется коррекция
        yield {"type": "needs_correction", "error": event.get("error")}
```

**Метод `_log_task_completed`:**
```python
async def _log_task_completed(self, report: dict) -> None:
    """Записать результаты выполнения задачи в память проекта."""
    from datetime import datetime
    
    memory_file = self.project_path / "memory" / "project.json"
    
    data = {}
    if memory_file.exists():
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    timestamp = datetime.now().isoformat()
    task_id = data.get("current_task", {}).get("id", "unknown")
    
    # Определение статуса
    status = report.get("status", "unknown")
    is_success = status in ["success", "partial"]
    
    # Обновление текущей задачи
    if data.get("current_task"):
        data["current_task"]["status"] = "completed" if is_success else "failed"
        data["current_task"]["completed_at"] = timestamp
        data["current_task"]["result_summary"] = report.get("summary", "")
        
        # Сохранение артефактов
        if report.get("artifacts"):
            data["artifacts"] = data.get("artifacts", {})
            data["artifacts"].update(report["artifacts"])
        
        # Сохранение файлов
        data["current_task"]["files_created"] = report.get("files_created", [])
        data["current_task"]["files_modified"] = report.get("files_modified", [])
    
    # Логирование
    data["task_log"].append({
        "timestamp": timestamp,
        "type": "task_completed",
        "task_id": task_id,
        "status": status,
        "summary": report.get("summary", ""),
        "files_created": report.get("files_created", []),
        "files_modified": report.get("files_modified", []),
        "errors": report.get("errors", [])
    })
    
    # Добавление ошибок если есть
    if report.get("errors"):
        data["errors"] = data.get("errors", [])
        for error in report["errors"]:
            data["errors"].append({
                "timestamp": timestamp,
                "task_id": task_id,
                "error": error
            })
    
    # Запись
    temp_file = memory_file.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.rename(memory_file)
    
    logger.info(f"Результаты задачи записаны в память: {task_id}, статус={status}")
```

---

### Этап 4: Проверка директором (принятие решения)

**Когда:** После завершения работы агента(s)

**Действия:**
1. Прочитать полную память проекта
2. Проанализировать:
   - Статус последней задачи
   - Наличие ошибок
   - Рекомендации от агентов
   - Общее состояние проекта
3. Принять решение:
   - `continue` - продолжить работу (новый шаг плана)
   - `complete` - задача завершена
   - `change_direction` - требуется коррекция плана
   - `ask_user` - нужен вопрос пользователю

**Код (Conductor._analyze_and_decide):**
```python
async def _analyze_and_decide(self, user_message: str) -> Any:
    # Получение полного контекста из памяти
    memory_context = await self._get_project_context()
    state_context = await self._get_state_context()
    
    # Формирование промпта для анализа
    analysis_prompt = self._build_decision_prompt(memory_context, state_context, user_message)
    
    # Вызов LLM для принятия решения
    response = await self.client.chat_completion(...)
    
    # Парсинг решения
    decision = parse_director_action(response)
    
    # Запись решения в память
    await self._log_decision(decision)
    
    return decision
```

**Метод `_build_decision_prompt`:**
```python
def _build_decision_prompt(self, memory: dict, state: dict, user_request: str) -> str:
    """Построить промпт для принятия решения на основе контекста."""
    
    current_task = memory.get("current_task", {})
    task_log = memory.get("task_log", [])[-5:]  # Последние 5 записей
    errors = memory.get("errors", [])[-3:]  # Последние 3 ошибки
    artifacts = memory.get("artifacts", {})
    
    prompt = f"""
=== КОНТЕКСТ ПРОЕКТА ===

Текущая задача:
- ID: {current_task.get('id', 'N/A')}
- Описание: {current_task.get('description', 'N/A')}
- Статус: {current_task.get('status', 'N/A')}
- Исполнитель: {current_task.get('assigned_to', 'N/A')}

Последние события:
{json.dumps(task_log, indent=2, ensure_ascii=False)}

Ошибки (если есть):
{json.dumps(errors, indent=2, ensure_ascii=False)}

Артефакты:
{list(artifacts.keys()) if artifacts else 'Нет'}

Текущее состояние системы:
{json.dumps(state, indent=2, ensure_ascii=False)}

Запрос пользователя: {user_request}

=== ЗАДАЧА ДЛЯ АНАЛИЗА ===

На основе предоставленного контекста прими решение:
1. Если задача полностью выполнена - выбери action=final с результатом
2. Если нужны дополнительные шаги - выбери action=delegate со следующей задачей
3. Если нужна информация от пользователя - выбери action=ask_user
4. Если обнаружены критические ошибки - сообщи об этом

Важно: Учитывай всю историю выполнения и текущее состояние проекта.
"""
    
    return prompt
```

**Метод `_log_decision`:**
```python
async def _log_decision(self, decision: Any) -> None:
    """Записать принятое решение в память проекта."""
    from datetime import datetime
    
    memory_file = self.project_path / "memory" / "project.json"
    
    data = {}
    if memory_file.exists():
        with open(memory_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    
    timestamp = datetime.now().isoformat()
    
    # Добавление в decisions
    if "decisions" not in data:
        data["decisions"] = []
    
    data["decisions"].append({
        "timestamp": timestamp,
        "action_type": decision.action_type.value,
        "role": decision.role,
        "task": decision.task,
        "result": decision.result,
        "reasoning": "Decision made based on project context"
    })
    
    # Запись
    temp_file = memory_file.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.rename(memory_file)
```

---

## Схема потока данных

```
┌─────────────┐
│  Пользователь│
└──────┬──────┘
       │ Запрос
       ▼
┌─────────────────┐
│    ДИРЕКТОР     │
│  (Conductor)    │
└────────┬────────┘
         │
         ├──────────────────────────────────┐
         │                                  │
         ▼                                  ▼
┌─────────────────┐              ┌──────────────────┐
│  ЗАПИСЬ В ПАМЯТЬ│              │ ЧТЕНИЕ ИЗ ПАМЯТИ │
│  (task_received)│              │  (полный контекст)│
└────────┬────────┘              └─────────┬────────┘
         │                                 │
         ▼                                 │
┌─────────────────┐                        │
│  АНАЛИЗ И РЕШЕНИЕ│◄───────────────────────┘
│  (analyze_and_  │
│   decide)       │
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌─────────────┐  ┌─────────────┐
│  DELEGATE   │  │    FINAL    │
└──────┬──────┘  └──────┬──────┘
       │                │
       ▼                │
┌─────────────┐         │
│   АГЕНТ     │         │
│  (Worker)   │         │
└──────┬──────┘         │
       │                │
       ▼                │
┌─────────────┐         │
│ ЗАПИСЬ В    │         │
│ ПАМЯТЬ      │         │
│ (completed) │         │
└──────┬──────┘         │
       │                │
       └────────────────┘
                │
                ▼
       ┌─────────────────┐
       │  ПРОВЕРКА И     │
       │  НОВОЕ РЕШЕНИЕ  │
       │  (continue/     │
       │   complete)     │
       └─────────────────┘
```

---

## Примеры использования

### Сценарий 1: Успешное выполнение задачи

1. **Пользователь:** "Создай простой веб-сайт с главной страницей"
2. **Директор:** Записывает `task_received` в память
3. **Директор:** Решает делегировать coder → записывает `task_delegated`
4. **Агент coder:** Создаёт файл index.html → записывает `task_completed` с артефактами
5. **Директор:** Читает память, видит что задача выполнена → `action=final`

### Сценарий 2: Многоступенчатая задача

1. **Пользователь:** "Разработай API с базой данных"
2. **Директор:** Записывает задачу, создаёт план
3. **Цикл:**
   - Делегирует researcher (анализ требований) → запись результатов
   - Делегирует coder (создание моделей) → запись результатов
   - Делегирует coder (создание endpoints) → запись результатов
   - Делегирует tester (тестирование) → запись результатов
4. **Директор:** После каждого шага читает память, проверяет прогресс
5. **Директор:** Все шаги выполнены → `action=final`

### Сценарий 3: Ошибка и коррекция

1. **Агент:** Возвращает `status=error` с описанием проблемы
2. **Директор:** Читает память, видит ошибку
3. **Директор:** Принимает решение:
   - `action=delegate` другому агенту для исправления, ИЛИ
   - `action=ask_user` для уточнения, ИЛИ
   - `action=final` с сообщением о проблеме

---

## Критерии принятия решений директором

### Продолжить работу (`continue`):
- ✅ Текущая задача выполнена успешно (`status=success`)
- ✅ Есть следующие шаги в плане
- ✅ Нет критических ошибок
- ✅ Пользователь не запрашивал завершение

### Завершить работу (`complete`):
- ✅ Все задачи плана выполнены
- ✅ Пользователь подтвердил завершение
- ✅ Достигнут удовлетворительный результат
- ✅ Нет незакрытых вопросов

### Изменить направление (`change_direction`):
- ⚠️ Обнаружены непреодолимые препятствия
- ⚠️ Пользователь изменил требования
- ⚠️ Текущий подход не работает (multiple errors)
- ⚠️ Появилась новая информация

### Запросить пользователя (`ask_user`):
- ❓ Недостаточно информации для продолжения
- ❓ Требуется подтверждение важного решения
- ❓ Неоднозначность в требованиях
- ❓ Критическая ошибка требует вмешательства

---

## Реализация

Файлы для изменения:
1. `conductor_app/src/director/conductor.py` - добавить методы логирования
2. `conductor_app/src/memory/manager.py` - расширить API для работы с task_log
3. `conductor_app/src/agents/worker.py` - убедиться что отчёты полные

Этот алгоритм обеспечивает прозрачность работы системы и позволяет директору принимать обоснованные решения на основе полной истории выполнения проекта.
