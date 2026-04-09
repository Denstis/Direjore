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
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(project_root / "conductor.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    
    logger = logging.getLogger(__name__)
    logger.info("🎭 Запуск Дирижёра...")
    
    try:
        app = MainWindow()
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
