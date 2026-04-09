# Исправление проблемы зацикливания агентов

## Причина проблемы
Модель возвращает JSON в виде обычного текста (`content`), вместо того чтобы использовать нативные `tool_calls`.
Оркестратор не может распознать команду, поэтому действие не выполняется, а вопрос не передается в GUI.

## Решение
Необходимо обновить системный промпт для ролей (DIRECTOR, CODER), добавив строгое требование использовать инструменты.

### Обновленный системный промпт (пример для DIRECTOR/CODER)

Добавьте этот блок в начало system message вашей модели:

```text
You are an AI assistant with access to specific tools. 
CRITICAL INSTRUCTION: 
- If you need to perform an action (create file, run code, ask user), you MUST use the provided tool functions.
- DO NOT output JSON or action plans inside your text message content.
- ONLY use the tool_call format to trigger actions.
- If you need information from the user, call the 'ask_user' tool immediately.
- If you need to write code, call the 'code_editor' or 'file_create' tool.
- Your text response should only be used for final explanations AFTER tools have been executed.

Available Tools:
- ask_user(question: str): Ask the user for clarification.
- code_editor(file_path: str, content: str): Create or modify a file.
- terminal_executor(command: str): Run a terminal command.
```

## Как это выглядит в коде (Python пример)

Если вы используете Python клиент (например, openai совместимый), убедитесь, что вы передаете `tools` в запросе и обрабатываете `tool_calls`:

```python
import json

# Пример правильной обработки ответа
response = client.chat.completions.create(
    model="qwen/qwen3.5-9b",
    messages=messages,
    tools=[  # Обязательно передайте описание инструментов
        {
            "type": "function",
            "function": {
                "name": "ask_user",
                "description": "Ask the user a question",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "The question to ask"}
                    },
                    "required": ["question"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delegate",
                "description": "Delegate task to another role",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "task": {"type": "string"}
                    },
                    "required": ["role", "task"]
                }
            }
        }
        # ... другие инструменты
    ],
    tool_choice="auto"  # Разрешить модели выбирать инструменты
)

message = response.choices[0].message

# ПРОВЕРКА: Есть ли вызовы инструментов?
if message.tool_calls:
    print("✅ Модель вызвала инструменты:")
    for tool in message.tool_calls:
        print(f" - {tool.function.name}: {tool.function.arguments}")
        # Здесь ваш код выполнения инструмента
else:
    print("⚠️ Модель вернула только текст (риск зацикливания):")
    print(message.content)
    # Если модель вернула текст вместо инструмента, возможно, стоит добавить retry 
    # или усилить системный промпт.
```

## Быстрый тест (Hello World)

Чтобы проверить, работает ли исправление, создайте простой скрипт `test_fix.py`:

```python
print("Hello, World!")
```

Запустите его в терминале:
```bash
python test_fix.py
```

Ожидаемый вывод:
```text
Hello, World!
```

Если после обновления промпта модель все еще не вызывает инструменты, попробуйте:
1. Уменьшить `temperature` до 0.1 - 0.3 (для более строгого следования инструкциям).
2. Добавить в конец промпта пример (few-shot prompting):
   ```text
   Example of correct output:
   User: Create a file.
   Assistant: [Calls tool: file_create(...)]
   
   Example of WRONG output:
   Assistant: {"action": "file_create", ...}  <-- Do not do this.
   ```
