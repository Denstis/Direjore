"""Тест интеграции памяти с агентами."""

import sys
from pathlib import Path

# Добавляем conductor_app в path
sys.path.insert(0, str(Path(__file__).parent / 'conductor_app'))

from src.memory.manager import MemoryManager
from src.agents.tools.memory_ops import register_memory_handlers
from src.core.tool_registry import ToolRegistry
from tempfile import TemporaryDirectory
import asyncio

async def test_memory_integration():
    """Проверка что memory handlers корректно зарегистрированы и работают."""
    
    with TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Создаём MemoryManager
        memory_manager = MemoryManager(project_path)
        
        # Записываем тестовые данные в память проекта
        await memory_manager.project_write("test_key", "test_value")
        await memory_manager.project_write("completed_steps", ["step1", "step2"])
        
        print("✅ Запись в память проекта успешна")
        
        # Читаем обратно
        value = await memory_manager.project_read("test_key")
        assert value == "test_value", f"Ожидалось 'test_value', получено {value}"
        print(f"✅ Чтение из памяти проекта: {value}")
        
        # Создаём ToolRegistry и регистрируем handlers
        tool_registry = ToolRegistry()
        tool_registry.load_all()
        
        register_memory_handlers(tool_registry, memory_manager)
        
        print("✅ Handlers зарегистрированы")
        
        # Проверяем что handler зарегистрирован
        handler = tool_registry.get_handler("read_project_memory")
        assert handler is not None, "Handler для read_project_memory не найден"
        print("✅ Handler для read_project_memory найден")
        
        # Вызываем handler через registry
        result = await handler(key="test_key")
        assert result == "test_value", f"Ожидалось 'test_value', получено {result}"
        print(f"✅ Вызов handler вернул: {result}")
        
        # Проверяем чтение всех данных
        all_data = await memory_manager.project_read()
        print(f"✅ Все данные памяти: {all_data}")
        
        print("\n🎉 Все тесты интеграции памяти пройдены!")

if __name__ == "__main__":
    asyncio.run(test_memory_integration())
