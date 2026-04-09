"""
StatusBar — строка состояния приложения.

Отображает: модель, использование токенов, статус, ошибки, прогресс.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional


class StatusBar:
    """Строка состояния."""

    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Создание виджетов."""
        # Левая часть: Статус подключения
        self.connection_label = ttk.Label(
            self.frame,
            text="🔴 LM Studio: не подключено",
            foreground="#cc0000",
        )
        self.connection_label.pack(side=tk.LEFT, padx=10)
        
        # Центральная часть: Текущая модель
        self.model_label = ttk.Label(
            self.frame,
            text="Модель: -",
        )
        self.model_label.pack(side=tk.LEFT, padx=10)
        
        # Токены
        self.tokens_label = ttk.Label(
            self.frame,
            text="Токены: 0/0",
        )
        self.tokens_label.pack(side=tk.LEFT, padx=10)
        
        # Правая часть: Статус
        self.status_label = ttk.Label(
            self.frame,
            text="✅ Готов",
            foreground="#008800",
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Индикатор активности
        self.activity_indicator = ttk.Label(self.frame, text="")
        self.activity_indicator.pack(side=tk.RIGHT, padx=5)
        
    def set_connection_status(self, connected: bool, url: str = "") -> None:
        """Установка статуса подключения."""
        if connected:
            self.connection_label.config(
                text=f"🟢 LM Studio: {url}",
                foreground="#008800",
            )
        else:
            self.connection_label.config(
                text="🔴 LM Studio: не подключено",
                foreground="#cc0000",
            )
            
    def set_model(self, model_name: str) -> None:
        """Установка текущей модели."""
        self.model_label.config(text=f"Модель: {model_name}")
        
    def set_tokens(self, used: int, total: int) -> None:
        """Установка использования токенов."""
        self.tokens_label.config(text=f"Токены: {used:,}/{total:,}")
        
    def set_status(self, status: str, is_error: bool = False) -> None:
        """Установка статуса."""
        if is_error:
            self.status_label.config(text=f"❌ {status}", foreground="#cc0000")
        else:
            self.status_label.config(text=f"✅ {status}", foreground="#008800")
            
    def set_activity(self, activity: str) -> None:
        """Установка индикатора активности."""
        self.activity_indicator.config(text=activity)
        
    def clear_activity(self) -> None:
        """Очистка индикатора активности."""
        self.activity_indicator.config(text="")
