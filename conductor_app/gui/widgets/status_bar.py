"""
StatusBar — строка состояния приложения.

Отображает: подключение к LM Studio, текущую модель, токены, статус.
"""

import tkinter as tk
from tkinter import ttk


class StatusBar:
    """Строка состояния с индикаторами."""

    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent)
        
        # Левая часть: Статус подключения
        self.connection_label = ttk.Label(
            self.frame,
            text="🔴 LM Studio: не подключено",
            foreground="#cc0000",
            font=("Segoe UI", 9)
        )
        self.connection_label.pack(side=tk.LEFT, padx=10)
        
        # Центральная часть: Текущая модель
        self.model_label = ttk.Label(
            self.frame,
            text="Модель: —",
            font=("Segoe UI", 9)
        )
        self.model_label.pack(side=tk.LEFT, padx=10)
        
        # Токены
        self.tokens_label = ttk.Label(
            self.frame,
            text="Токены: 0/0",
            font=("Segoe UI", 9)
        )
        self.tokens_label.pack(side=tk.LEFT, padx=10)
        
        # Правая часть: Статус
        self.status_label = ttk.Label(
            self.frame,
            text="✅ Готов",
            foreground="#008800",
            font=("Segoe UI", 9)
        )
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
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
