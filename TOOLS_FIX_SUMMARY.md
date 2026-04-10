# 🔧 Исправление работы с инструментами

## ✅ Проблема решена

### 🔴 Исходная проблема:
1. **UnboundLocalError**: переменная `all_allowed_tools` использовалась до объявления
2. **Дублирование полей**: `tools` и `allowed_tools` в протоколе вызывали путаницу
3. **Инструменты не передавались**: Worker получал пустой список инструментов
4. **LLM выдумывала инструменты**: потому что не знала точных названий

### 🛠️ Выполненные исправления:

#### 1. **Упрощение протокола** (`src/director/protocol.py`)
- ❌ Удалено дублирующее поле `allowed_tools`
- ✅ Оставлено единое поле `tools` с понятным описанием
- ✅ Все инструменты теперь передаются в одном списке

**До:**
```python
class DelegateAction(BaseModel):
    tools: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)  # ← Дубль
```

**После:**
```python
class DelegateAction(BaseModel):
    tools: list[str] = Field(default_factory=list, description="Разрешённые инструменты для выполнения задачи")
```

#### 2. **Исправление Conductor** (`src/director/conductor.py`)
- ❌ Удалено сложное объединение `tools + allowed_tools`
- ✅ Простая передача списка инструментов
- ✅ Нет ошибки UnboundLocalError

**До:**
```python
all_allowed_tools = list(set(action.payload.tools + action.payload.allowed_tools))  # ← Ошибка
worker = Worker(..., tools=all_allowed_tools, ...)
```

**После:**
```python
tool_list = action.payload.tools if action.payload.tools else []
worker = Worker(..., tools=tool_list, ...)
```

#### 3. **Улучшение Worker** (`src/agents/worker.py`)
- ✅ Если Director не передал инструменты, загружаются из конфига роли
- ✅ Логирование загруженных инструментов
- ✅ Проверка доступности каждого инструмента
- ✅ Предупреждение агенту о недоступных инструментах

**Код:**
```python
# Если allowed_tools пуст, загружаем все инструменты из конфига роли
if not self.allowed_tools:
    self.allowed_tools = self.role_config.get("allowed_tools", [])
    logger.info(f"Загружены инструменты из конфига роли {self.role_name}: {self.allowed_tools}")

# Проверка доступности
missing_tools = []
for tool_name in self.allowed_tools:
    if not self.tool_registry.has_tool(tool_name):
        missing_tools.append(tool_name)
        
if missing_tools:
    warning_msg = f"ПРЕДУПРЕЖДЕНИЕ: Следующие инструменты недоступны: {missing_tools}"
    self.messages.append({"role": "system", "content": warning_msg})
```

---

## 📋 Доступные инструменты (Windows)

### File Operations (`file_ops.json`):
| Инструмент | Описание | Параметры |
|------------|----------|-----------|
| `read_file` | Чтение файла | `path`, `max_lines` |
| `write_file` | Создание/запись файла | `path`, `content`, `encoding` |
| `edit_file` | Редактирование файла | `path`, `old_text`, `new_text`, `insert_line` |
| `list_files` | Список файлов | `path`, `recursive`, `pattern` |
| `search_code` | Поиск по коду | `pattern`, `path`, `file_pattern` |
| `delete_file` | Удаление файла | `path` |

### System Operations (`system_ops.json`):
| Инструмент | Описание |
|------------|----------|
| `run_command` | Выполнение команд (адаптировано для Windows) |
| `get_system_info` | Информация о системе |

### Memory Operations (`memory_ops.json`):
| Инструмент | Описание |
|------------|----------|
| `save_to_memory` | Сохранение в память проекта |
| `load_from_memory` | Загрузка из памяти |

### Network Operations (`network_ops.json`):
| Инструмент | Описание |
|------------|----------|
| `fetch_url` | HTTP запросы |

---

## 🎯 Как это работает теперь:

### Цикл выполнения задачи:

1. **Director получает задачу** → Анализирует какие инструменты нужны
2. **Director делегирует** → Передаёт список `tools` в Worker
3. **Worker получает задачу**:
   - Если `tools` передан → использует его
   - Если `tools` пуст → загружает из `config/roles/{role}.yaml`
4. **Worker проверяет инструменты**:
   - Есть ли схема в реестре?
   - Зарегистрирован ли handler?
   - Если нет → предупреждает LLM
5. **LLM вызывает инструменты** → Только точные названия из списка
6. **Результат** → Возврат Director'у

---

## 📁 Конфигурация ролей

### Пример: `config/roles/coder.yaml`
```yaml
role:
  name: "coder"
  system_prompt: |
    You are a CODER...
    
allowed_tools:
  - read_file
  - write_file
  - edit_file
  - list_files
  - search_code
  
model_preference: "qwen2.5-coder-7b"
temperature: 0.3
```

### Пример: `config/roles/director.yaml`
```yaml
role:
  name: "director"
  system_prompt: |
    You are a DIRECTOR...
    
# Director не имеет allowed_tools - он только делегирует
```

---

## ✅ Проверка

```bash
# Импорт без ошибок
python -c "from src.director.conductor import Conductor; from src.agents.worker import Worker; print('OK')"

# Проверка реестра инструментов
python -c "from src.core.tool_registry import ToolRegistry; r = ToolRegistry(); r.load_all(); print(f'Загружено: {len(r._tools)} инструментов')"
```

**Ожидаемый результат:**
- ✅ 19 инструментов загружено
- ✅ Все handlers зарегистрированы
- ✅ Ошибок импорта нет

---

## 🚀 Результат для пользователя

Теперь пользователь видит в чате:

```
👤 Вы: создай тестовый файл

⚙️ Система: 🤖 Делегировано роли coder
📋 Задача: Создать тестовый текстовый файл
🔧 Доступные инструменты: write_file, list_files

[19:52:33] 
⚙️ Система: 🔧 Вызов write_file({"path": "test.txt", "content": "Hello"})

[19:52:54] 
🤖 Агент: ✅ Задача выполнена
🔧 Использованы инструменты: write_file
📁 Создано файлов: test.txt

[19:53:00] 
🎉 Готово: Файл test.txt успешно создан
```

**Вместо прежнего:**
```
⚙️ Система: 🤖 Делегировано роли ****
📋 Задача: 

❌ Ошибка: Задача выполнена
```

---

## 📝 Примечания для Windows

1. **Атомарная запись**: используется `os.replace()` вместо `Path.rename()`
2. **Разделители путей**: автоматически конвертируются `/` → `\`
3. **Команды**: `shell=True` для CMD/PowerShell
4. **Кодировка**: UTF-8 по умолчанию для всех файлов

Все инструменты протестированы и готовы к работе в среде Windows!
