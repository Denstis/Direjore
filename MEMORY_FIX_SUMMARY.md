# Исправление работы с памятью агентов

## Проблема
Агенты не использовали память проекта при выполнении задач, что приводило к:
- Повторению уже выполненной работы
- Отсутствию контекста о текущем состоянии проекта
- Зацикливанию дирижёра

## Решение

### 1. Исправлена регистрация memory handlers (`src/agents/tools/memory_ops.py`)

**До:**
```python
def register_memory_handlers(tool_registry, project_path: Path) -> None:
    handlers = {
        "read_project_memory": partial(read_project_memory, project_path),
        ...
    }
```

**После:**
```python
def register_memory_handlers(tool_registry, memory_manager: "MemoryManager") -> None:
    handlers = {
        "read_project_memory": partial(memory_manager.project_read),
        "write_project_memory": partial(memory_manager.project_write),
        ...
    }
```

Теперь handlers используют единый MemoryManager вместо прямых функций с project_path.

### 2. Добавлен метод `_get_memory_context` в Worker (`src/agents/worker.py`)

Новый метод загружает всю память проекта и добавляет её в контекст сообщения агенту:

```python
async def _get_memory_context(self) -> dict:
    """Получить полный контекст из памяти проекта для агента."""
    memory_file = self.conductor.project_path / "memory" / "project.json"
    if not memory_file.exists():
        return {}
    
    with open(memory_file, "r", encoding="utf-8") as f:
        all_data = json.load(f)
    
    logger.debug(f"Загружена память проекта: {len(all_data)} ключей")
    return all_data
```

### 3. Обновлён цикл выполнения агента

В методе `execute()` теперь память загружается перед началом работы:

```python
# ДОБАВЛЕНИЕ КОНТЕКСТА ПАМЯТИ - КРИТИЧЕСКИ ВАЖНО
memory_context = await self._get_memory_context()

self.messages = [
    {"role": "system", "content": system_prompt},
]

# Добавляем контекст памяти если он есть
if memory_context:
    logger.info(f"Добавлен контекст памяти для агента: {len(json.dumps(memory_context))} байт")
    self.messages.append(
        {"role": "user", "content": f"Контекст из памяти проекта:\n{json.dumps(memory_context, ensure_ascii=False, indent=2)}"}
    )

# Добавляем задачу
self.messages.append({"role": "user", "content": f"Задача: {self.task}"})
```

### 4. Обновлены роли (config/roles/)

#### Director (`director.yaml`)
Добавлены секции:
- **EXECUTION FLOW**: Инструкция проверять контекст перед началом работы
- **CONTEXT AWARENESS**: Запрет на повторение выполненной работы

#### Coder (`coder.yaml`)
Добавлены секции:
- **MEMORY AWARENESS**: Использование контекста памяти
- Улучшены инструкции по созданию и проверке файлов

## Тестирование

Создан тест `/workspace/test_memory_integration.py`:

```bash
python /workspace/test_memory_integration.py
```

Результат:
```
✅ Запись в память проекта успешна
✅ Чтение из памяти проекта: test_value
✅ Handlers зарегистрированы
✅ Handler для read_project_memory найден
✅ Вызов handler вернул: test_value
✅ Все данные памяти: {'test_key': 'test_value', 'completed_steps': ['step1', 'step2']}

🎉 Все тесты интеграции памяти пройдены!
```

## Изменённые файлы

1. `conductor_app/src/agents/tools/memory_ops.py` - Исправлена регистрация handlers
2. `conductor_app/src/agents/worker.py` - Добавлено чтение памяти и передача в контекст
3. `conductor_app/config/roles/director.yaml` - Добавлены инструкции о работе с памятью
4. `conductor_app/config/roles/coder.yaml` - Добавлены инструкции о работе с памятью

## Как это работает

1. При инициализации проекта создаётся `MemoryManager`
2. Handlers регистрируются через `MemoryManager` вместо прямых функций
3. При запуске агента `Worker._get_memory_context()` читает `memory/project.json`
4. Контекст памяти добавляется в первое сообщение агенту как системный контекст
5. Агент видит что уже сделано и может продолжать работу

## Пример использования

```python
# Дирижёр записывает в память
await memory_manager.project_write("completed_steps", ["setup", "config"])

# Агент получает контекст автоматически
# В messages будет:
# {"role": "user", "content": "Контекст из памяти проекта:\n{\"completed_steps\": [\"setup\", \"config\"]}"}

# Агент понимает что setup и config уже сделаны и продолжает дальше
```
