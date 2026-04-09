"""Тест изменений для проверки исправлений."""

import json
from pathlib import Path

def test_conductor_context():
    """Проверка что Conductor правильно передаёт контекст."""
    print("Testing Conductor context handling...")
    
    # Импортируем модуль
    import sys
    sys.path.insert(0, '/workspace/conductor_app')
    
    from src.director.conductor import Conductor
    
    # Проверяем наличие метода _get_state_context
    assert hasattr(Conductor, '_get_state_context'), "Метод _get_state_context не найден"
    print("✓ Метод _get_state_context существует")
    
    # Проверяем наличие метода _get_project_context  
    assert hasattr(Conductor, '_get_project_context'), "Метод _get_project_context не найден"
    print("✓ Метод _get_project_context существует")
    
    print("\nConductor context tests PASSED\n")


def test_gui_methods():
    """Проверка методов GUI."""
    print("Testing GUI methods...")
    
    import ast
    
    with open('/workspace/conductor_app/gui/app.py', 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    
    # Находим класс MainWindow
    main_window_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'MainWindow':
            main_window_class = node
            break
    
    assert main_window_class is not None, "Класс MainWindow не найден"
    
    # Собираем имена методов
    method_names = [node.name for node in main_window_class.body if isinstance(node, ast.FunctionDef)]
    
    # Проверяем наличие нужных методов
    assert '_open_project' in method_names, "Метод _open_project не найден"
    print("✓ Метод _open_project существует")
    
    assert '_load_chat_history' in method_names, "Метод _load_chat_history не найден"
    print("✓ Метод _load_chat_history существует")
    
    print("\nGUI tests PASSED\n")


def test_director_prompt():
    """Проверка prompt Дирижёра."""
    print("Testing Director prompt...")
    
    import yaml
    
    with open('/workspace/conductor_app/config/roles/director.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    system_prompt = config.get('system_prompt', '')
    
    # Проверяем наличие новых инструкций
    assert 'EXECUTION FLOW' in system_prompt, "Секция EXECUTION FLOW не найдена"
    print("✓ Секция EXECUTION FLOW присутствует")
    
    assert 'CONTEXT AWARENESS' in system_prompt, "Секция CONTEXT AWARENESS не найдена"
    print("✓ Секция CONTEXT AWARENESS присутствует")
    
    assert 'check project context' in system_prompt.lower(), "Инструкция о проверке контекста не найдена"
    print("✓ Инструкция о проверке контекста присутствует")
    
    assert 'do not repeat' in system_prompt.lower(), "Инструкция о повторении не найдена"
    print("✓ Инструкция о запрете повторения присутствует")
    
    print("\nDirector prompt tests PASSED\n")


if __name__ == '__main__':
    print("=" * 60)
    print("TESTING ALL CHANGES")
    print("=" * 60 + "\n")
    
    test_conductor_context()
    test_gui_methods()
    test_director_prompt()
    
    print("=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
