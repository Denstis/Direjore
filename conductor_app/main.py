#!/usr/bin/env python3
"""
Точка входа приложения «Дирижёр».

Инициализация asyncio + Tkinter, запуск главного окна.
"""

import sys
from pathlib import Path

# Добавление корня проекта в path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from gui.app import MainWindow


def main():
    """Точка входа приложения."""
    import logging
    
    # Проверка флага debug
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    if debug_mode:
        log_level = logging.DEBUG
        print("🔍 Запуск в режиме отладки (debug mode)")
    else:
        log_level = logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(project_root / "conductor.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🎭 Запуск Дирижёра...")
    
    if debug_mode:
        logger.debug("Режим отладки включён")
        logger.debug(f"Аргументы командной строки: {sys.argv}")
        logger.debug(f"Корень проекта: {project_root}")
    
    try:
        app = MainWindow()
        
        if debug_mode:
            logger.debug("Главное окно создано")
        
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
