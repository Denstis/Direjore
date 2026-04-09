#!/usr/bin/env python3
"""Тестовый файл для проверки исправления зацикливания агентов."""

import json
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / "conductor_app" / "src"))

from director.protocol import DirectorResponse, DirectorActionType, DelegateAction

def test_director_response_with_allowed_tools():
    """Проверка что DirectorResponse поддерживает поле allowed_tools."""
    print("Тест 1: Проверка DirectorResponse с allowed_tools...")
    
    response = DirectorResponse(
        action=DirectorActionType.DELEGATE,
        role="coder",
        task="Создать Hello World файл",
        tools=["write_file", "read_file"],
        allowed_tools=["write_file", "read_file", "edit_file"],
        context_keys=[]
    )
    
    assert response.allowed_tools == ["write_file", "read_file", "edit_file"]
    print(f"✓ allowed_tools корректно установлено: {response.allowed_tools}")
    
    # Проверка сериализации
    json_str = response.model_dump_json()
    parsed = DirectorResponse.model_validate_json(json_str)
    assert parsed.allowed_tools == response.allowed_tools
    print(f"✓ Сериализация/десериализация прошла успешно")
    
    return True

def test_delegate_action_with_allowed_tools():
    """Проверка что DelegateAction поддерживает поле allowed_tools."""
    print("\nТест 2: Проверка DelegateAction с allowed_tools...")
    
    action = DelegateAction(
        role="tester",
        task="Запустить тесты",
        tools=["execute_code"],
        allowed_tools=["execute_code", "read_file"],
    )
    
    assert action.allowed_tools == ["execute_code", "read_file"]
    print(f"✓ allowed_tools корректно установлено: {action.allowed_tools}")
    
    return True

def test_yaml_configs_updated():
    """Проверка что YAML конфиги обновлены."""
    print("\nТест 3: Проверка YAML конфигов...")
    
    roles_dir = Path(__file__).parent / "conductor_app" / "config" / "roles"
    
    for role_file in ["director.yaml", "coder.yaml", "researcher.yaml"]:
        role_path = roles_dir / role_file
        if not role_path.exists():
            print(f"✗ Файл {role_file} не найден")
            return False
            
        content = role_path.read_text()
        
        # Проверка наличия запрета на markdown блоки
        if "NEVER output JSON inside markdown code blocks" not in content:
            print(f"✗ В {role_file} отсутствует запрет на markdown блоки")
            return False
            
        print(f"✓ {role_file} содержит запрет на markdown блоки")
    
    return True

def main():
    """Запуск всех тестов."""
    print("=" * 60)
    print("ТЕСТ ИСПРАВЛЕНИЯ ЗАЦИКЛИВАНИЯ АГЕНТОВ")
    print("=" * 60)
    
    all_passed = True
    
    try:
        all_passed &= test_director_response_with_allowed_tools()
    except Exception as e:
        print(f"✗ Тест 1 провален: {e}")
        all_passed = False
    
    try:
        all_passed &= test_delegate_action_with_allowed_tools()
    except Exception as e:
        print(f"✗ Тест 2 провален: {e}")
        all_passed = False
    
    try:
        all_passed &= test_yaml_configs_updated()
    except Exception as e:
        print(f"✗ Тест 3 провален: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("\nИсправления:")
        print("1. Добавлено поле allowed_tools в DirectorResponse и DelegateAction")
        print("2. Обновлены системные промпты (director, coder, researcher)")
        print("3. Добавлен запрет на вывод JSON в markdown блоках")
        print("4. Conductor объединяет tools и allowed_tools при делегировании")
        return 0
    else:
        print("✗ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1

if __name__ == "__main__":
    sys.exit(main())
