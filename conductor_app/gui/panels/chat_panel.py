"""
ChatPanel — панель диалога с агентом.

История сообщений с цветовой разметкой, ввод текста, контекстное меню.
"""

import json
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Callable, List, Optional


class CodeEditorWithMenu(scrolledtext.ScrolledText):
    """Текстовый редактор с контекстным меню."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_context_menu()
        
        # Настройка шрифтов
        self.config(
            font=("Consolas", 10),
            wrap=tk.WORD,
            undo=True,
            autoseparators=True,
            maxundo=-1,
        )
        
    def _create_context_menu(self):
        """Создание контекстного меню."""
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Вырезать", command=self._cut)
        self.menu.add_command(label="Копировать", command=self._copy)
        self.menu.add_command(label="Вставить", command=self._paste)
        self.menu.add_separator()
        self.menu.add_command(label="Найти", command=self._find)
        self.menu.add_command(label="Заменить", command=self._replace)
        self.menu.add_separator()
        self.menu.add_command(label="Выделить всё", command=self._select_all)
        
        # Привязка к правой кнопке мыши
        self.bind("<Button-3>", self._show_context_menu)
        
        # Горячие клавиши
        self.bind("<Control-f>", lambda e: self._find())
        self.bind("<Control-h>", lambda e: self._replace())
        self.bind("<Control-a>", lambda e: self._select_all())

    def _show_context_menu(self, event):
        """Показ контекстного меню."""
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()

    def _cut(self):
        """Вырезать."""
        try:
            text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
            self.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            pass

    def _copy(self):
        """Копировать."""
        try:
            text = self.selection_get()
            self.clipboard_clear()
            self.clipboard_append(text)
        except tk.TclError:
            pass

    def _paste(self):
        """Вставить."""
        try:
            text = self.clipboard_get()
            self.insert(tk.INSERT, text)
        except tk.TclError:
            pass

    def _find(self):
        """Найти текст."""
        dialog = FindDialog(self)
        self.wait_window(dialog.top)

    def _replace(self):
        """Найти и заменить."""
        dialog = ReplaceDialog(self)
        self.wait_window(dialog.top)

    def _select_all(self):
        """Выделить всё."""
        self.tag_add(tk.SEL, "1.0", tk.END)
        self.mark_set(tk.INSERT, "1.0")
        self.see(tk.INSERT)
        return 'break'


class FindDialog(tk.Toplevel):
    """Диалог поиска."""

    def __init__(self, editor: CodeEditorWithMenu):
        super().__init__(editor)
        self.editor = editor
        self.title("Найти")
        self.geometry("300x120")
        self.resizable(False, False)
        
        tk.Label(self, text="Найти:").pack(pady=5)
        self.entry = tk.Entry(self, width=40)
        self.entry.pack(pady=5)
        self.entry.focus_set()
        
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Найти", command=self._find).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.destroy).pack(side=tk.LEFT, padx=5)
        
        self.bind("<Return>", lambda e: self._find())
        
    def _find(self):
        """Поиск текста."""
        search_term = self.entry.get()
        if not search_term:
            return
            
        # Снятие предыдущих выделений
        self.editor.tag_remove("found", "1.0", tk.END)
        
        start = "1.0"
        found_count = 0
        while True:
            pos = self.editor.search(search_term, start, stopindex=tk.END)
            if not pos:
                break
            end_pos = f"{pos}+{len(search_term)}c"
            self.editor.tag_add("found", pos, end_pos)
            self.editor.tag_config("found", background="yellow")
            start = end_pos
            found_count += 1
            
        if found_count == 0:
            messagebox.showinfo("Поиск", "Текст не найден")
        else:
            self.editor.see(pos)


class ReplaceDialog(tk.Toplevel):
    """Диалог замены."""

    def __init__(self, editor: CodeEditorWithMenu):
        super().__init__(editor)
        self.editor = editor
        self.title("Найти и заменить")
        self.geometry("350x180")
        self.resizable(False, False)
        
        tk.Label(self, text="Найти:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.find_entry = tk.Entry(self, width=40)
        self.find_entry.grid(row=0, column=1, pady=5)
        
        tk.Label(self, text="Заменить на:").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.replace_entry = tk.Entry(self, width=40)
        self.replace_entry.grid(row=1, column=1, pady=5)
        
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="Заменить", command=self._replace).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Заменить все", command=self._replace_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Отмена", command=self.destroy).pack(side=tk.LEFT, padx=5)
        
        self.find_entry.focus_set()
        self.bind("<Return>", lambda e: self._replace())
        
    def _replace(self):
        """Заменить одно вхождение."""
        search_term = self.find_entry.get()
        replace_term = self.replace_entry.get()
        
        try:
            sel_start = self.editor.index(tk.SEL_FIRST)
            sel_end = self.editor.index(tk.SEL_LAST)
            selected_text = self.editor.get(sel_start, sel_end)
            
            if selected_text == search_term:
                self.editor.delete(sel_start, sel_end)
                self.editor.insert(sel_start, replace_term)
        except tk.TclError:
            messagebox.showwarning("Замена", "Выделите текст для замены")
            
    def _replace_all(self):
        """Заменить все вхождения."""
        search_term = self.find_entry.get()
        replace_term = self.replace_entry.get()
        
        if not search_term:
            return
            
        count = 0
        start = "1.0"
        while True:
            pos = self.editor.search(search_term, start, stopindex=tk.END)
            if not pos:
                break
            end_pos = f"{pos}+{len(search_term)}c"
            self.editor.delete(pos, end_pos)
            self.editor.insert(pos, replace_term)
            start = f"{pos}+{len(replace_term)}c"
            count += 1
            
        messagebox.showinfo("Замена", f"Заменено {count} вхождений")


class ChatPanel:
    """Панель диалога с агентом."""

    def __init__(self, parent, main_window):
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        
        self._create_widgets()
        self._setup_tags()
        
    def _create_widgets(self):
        """Создание виджетов."""
        # Заголовок
        header_frame = ttk.Frame(self.frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="💬 ДИАЛОГ С АГЕНТОМ", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        # История сообщений
        history_frame = ttk.LabelFrame(self.frame, text="История")
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.history_text = CodeEditorWithMenu(
            history_frame,
            height=20,
            state=tk.DISABLED,
            bg="#f8f8f8",
        )
        self.history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Поле ввода
        input_frame = ttk.Frame(self.frame)
        input_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.input_text = CodeEditorWithMenu(
            input_frame,
            height=4,
            bg="white",
        )
        self.input_text.pack(fill=tk.X, pady=(0, 5))
        self.input_text.bind("<Return>", self._on_enter_pressed)
        self.input_text.bind("<Shift-Return>", lambda e: None)  # Перенос строки
        
        # Кнопки управления
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill=tk.X)
        
        self.stop_button = ttk.Button(btn_frame, text="🛑 Стоп", command=self._stop_execution)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.send_button = ttk.Button(btn_frame, text="➤ Отправить", command=self._send_message)
        self.send_button.pack(side=tk.RIGHT)
        
        # Прогресс
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
        )
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
    def _setup_tags(self):
        """Настройка тегов для цветовой разметки."""
        self.history_text.tag_config("user", foreground="#0066cc", lmargin1=10, lmargin2=10)
        self.history_text.tag_config("assistant", foreground="#008800", lmargin1=10, lmargin2=10)
        self.history_text.tag_config("system", foreground="#666666", lmargin1=10, lmargin2=10, font=("Consolas", 9))
        self.history_text.tag_config("error", foreground="#cc0000", lmargin1=10, lmargin2=10)
        self.history_text.tag_config("tool", foreground="#996600", lmargin1=10, lmargin2=10, font=("Consolas", 9))
        self.history_text.tag_config("timestamp", foreground="#999999", font=("Segoe UI", 8))
        
    def add_message(self, role: str, content: str) -> None:
        """Добавление сообщения в историю."""
        self.history_text.config(state=tk.NORMAL)
        
        timestamp = f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] "
        
        role_icons = {
            "user": "👤 Вы:",
            "assistant": "🤖 Агент:",
            "system": "⚙️ Система:",
            "error": "❌ Ошибка:",
            "tool": "🔧 Инструмент:",
        }
        
        icon = role_icons.get(role, "")
        
        # Вставка timestamp
        self.history_text.insert(tk.END, timestamp, "timestamp")
        self.history_text.insert(tk.END, "\n")
        
        # Вставка роли и контента
        self.history_text.insert(tk.END, f"{icon} ", role)
        
        # Форматирование JSON
        if isinstance(content, dict):
            formatted = json.dumps(content, ensure_ascii=False, indent=2)
            self.history_text.insert(tk.END, formatted, role)
        else:
            self.history_text.insert(tk.END, content, role)
            
        self.history_text.insert(tk.END, "\n\n")
        
        self.history_text.config(state=tk.DISABLED)
        self.history_text.see(tk.END)
        
    def show_question(self, question: str, options: List[str]) -> None:
        """Показ вопроса пользователю."""
        self.add_message("system", f"❓ {question}")
        
        if options:
            for i, option in enumerate(options, 1):
                self.add_message("system", f"  {i}. {option}")
                
    def clear_history(self) -> None:
        """Очистка истории."""
        self.history_text.config(state=tk.NORMAL)
        self.history_text.delete("1.0", tk.END)
        self.history_text.config(state=tk.DISABLED)
        
    def _send_message(self) -> None:
        """Отправка сообщения."""
        message = self.input_text.get("1.0", tk.END).strip()
        if not message:
            return
            
        # Отправка через main window
        self.main_window.send_message(message)
        
        # Очистка поля ввода
        self.input_text.delete("1.0", tk.END)
        
    def _on_enter_pressed(self, event) -> str:
        """Обработка Enter."""
        if not event.state & 0x1:  # Без Shift
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
        self.progress_var.set(value)
        
    def reset_progress(self) -> None:
        """Сброс прогресса."""
        self.progress_var.set(0)
