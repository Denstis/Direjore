"""
ChatPanel — панель диалога с агентом на CustomTkinter.

История сообщений с цветовой разметкой, ввод текста, спойлеры.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

import customtkinter as ctk

from gui_new.app import ChatMessageFrame

logger = logging.getLogger(__name__)


class ChatPanel(ctk.CTkScrollableFrame):
    """Панель диалога с агентом."""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        self.messages = []
        
        self._create_widgets()

    def _create_widgets(self):
        """Создание виджетов."""
        # Контейнер для сообщений
        self.messages_container = ctk.CTkFrame(self, fg_color="transparent")
        self.messages_container.pack(fill="both", expand=True, pady=5)
        
        # Поле ввода
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", pady=(5, 0))
        
        self.input_text = ctk.CTkTextbox(input_frame, height=80)
        self.input_text.pack(fill="x", pady=(0, 5))
        self.input_text.bind("<Return>", self._on_enter_pressed)
        
        # Кнопки управления
        btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        self.stop_button = ctk.CTkButton(
            btn_frame, 
            text="🛑 Стоп", 
            command=self._stop_execution,
            fg_color="#DC3545",
            width=100
        )
        self.stop_button.pack(side="left", padx=(0, 5))
        
        # Spacer
        ctk.CTkFrame(btn_frame, width=20, fg_color="transparent").pack(side="left", fill="x", expand=True)
        
        self.send_button = ctk.CTkButton(
            btn_frame, 
            text="➤ Отправить", 
            command=self._send_message,
            width=120
        )
        self.send_button.pack(side="right")
        
        # Прогресс
        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate")
        self.progress_bar.pack(fill="x", pady=(10, 0))
        self.progress_bar.set(0)

    def add_message(self, role: str, content: str, collapsible: bool = False) -> None:
        """Добавление сообщения в историю."""
        timestamp = f"[{datetime.now().strftime('%H:%M:%S')}]"
        
        message_frame = ChatMessageFrame(self.messages_container, role, content, timestamp)
        message_frame.pack(fill="x", padx=5, pady=5, anchor="w")
        
        self.messages.append(message_frame)
        
        # Автопрокрутка вниз
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Прокрутка вниз."""
        self.after(100, lambda: self._see_end())

    def _see_end(self):
        """Прокрутка к концу."""
        try:
            self._scrollbar.set(1.0, 1.0)
        except Exception:
            pass

    def show_question(self, question: str, options: List[str]) -> None:
        """Показ вопроса пользователю."""
        timestamp = f"[{datetime.now().strftime('%H:%M:%S')}]"
        
        # Создаем фрейм вопроса
        question_frame = ctk.CTkFrame(self.messages_container, fg_color="#2a2a2a")
        question_frame.pack(fill="x", padx=5, pady=5, anchor="w")
        
        # Timestamp
        ts_label = ctk.CTkLabel(question_frame, text=timestamp, font=ctk.CTkFont(size=9), text_color="gray")
        ts_label.pack(anchor="w", padx=5, pady=(5, 0))
        
        # Question
        q_label = ctk.CTkLabel(
            question_frame, 
            text=f"⚙️ Система: ❓ {question}", 
            wraplength=800, 
            justify="left",
            font=ctk.CTkFont(size=12)
        )
        q_label.pack(anchor="w", padx=5, pady=5)
        
        # Options
        if options:
            options_frame = ctk.CTkFrame(question_frame, fg_color="transparent")
            options_frame.pack(fill="x", padx=5, pady=5)
            
            for i, option in enumerate(options, 1):
                opt_btn = ctk.CTkButton(
                    options_frame,
                    text=f"{i}. {option}",
                    command=lambda idx=i-1: self._select_option(idx, options),
                    anchor="w",
                    width=750
                )
                opt_btn.pack(fill="x", pady=2)
        
        self.messages.append(question_frame)
        self._scroll_to_bottom()

    def _select_option(self, index: int, options: List[str]):
        """Выбор опции пользователем."""
        if 0 <= index < len(options):
            selected = options[index]
            self.add_message("user", f"Выбрано: {selected}")
            self.main_window.send_message(selected)

    def clear_history(self) -> None:
        """Очистка истории."""
        for widget in self.messages_container.winfo_children():
            widget.destroy()
        self.messages = []

    def _send_message(self) -> None:
        """Отправка сообщения."""
        message = self.input_text.get("1.0", "end").strip()
        if not message:
            return
            
        self.main_window.send_message(message)
        self.input_text.delete("1.0", "end")

    def _on_enter_pressed(self, event) -> str:
        """Обработка Enter."""
        if not (event.state & 0x1):  # Без Shift
            self._send_message()
            return 'break'
        return ''

    def _stop_execution(self) -> None:
        """Остановка выполнения."""
        if self.main_window.conductor:
            self.main_window.conductor.cancel_flag = True
            self.add_message("system", "🛑 Выполнение прервано пользователем")

    def set_progress(self, value: float) -> None:
        """Установка прогресса."""
        self.progress_bar.set(value)

    def reset_progress(self) -> None:
        """Сброс прогресса."""
        self.progress_bar.set(0)
