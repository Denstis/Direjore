"""
ConfigPanel — панель конфигурации с табами.

Табы: Модели, Роли, Инструменты, Память, Логи.
"""

import json
import logging
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from pathlib import Path
from typing import Optional
import yaml

logger = logging.getLogger(__name__)


class ConfigPanel:
    """Панель конфигурации."""

    def __init__(self, parent, main_window):
        self.main_window = main_window
        self.frame = ttk.Frame(parent)
        
        self._create_widgets()
        
    def _create_widgets(self):
        """Создание виджетов."""
        # Заголовок
        header_frame = ttk.Frame(self.frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(header_frame, text="⚙️ КОНФИГУРАЦИЯ", font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT)
        
        # Notebook для табов
        self.notebook = ttk.Notebook(self.frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Таб Модели
        self.models_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.models_tab, text="📦 Модели")
        self._setup_models_tab()
        
        # Таб Роли
        self.roles_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.roles_tab, text="👥 Роли")
        self._setup_roles_tab()
        
        # Таб Инструменты
        self.tools_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tools_tab, text="🛠 Инструменты")
        self._setup_tools_tab()
        
        # Таб Память
        self.memory_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.memory_tab, text="🧠 Память")
        self._setup_memory_tab()
        
        # Таб Логи
        self.logs_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.logs_tab, text="📜 Логи")
        self._setup_logs_tab()
        
        # Кнопка Применить
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.apply_button = ttk.Button(btn_frame, text="💾 Применить", command=self._apply_changes)
        self.apply_button.pack(side=tk.RIGHT)
        
    def _setup_models_tab(self):
        """Настройка таба Модели."""
        # Список моделей
        list_frame = ttk.LabelFrame(self.models_tab, text="Доступные модели")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview для моделей
        columns = ("name", "context", "tools", "quant")
        self.models_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        self.models_tree.heading("name", text="Модель")
        self.models_tree.heading("context", text="Контекст")
        self.models_tree.heading("tools", text="Tools")
        self.models_tree.heading("quant", text="Квантование")
        
        self.models_tree.column("name", width=200)
        self.models_tree.column("context", width=80)
        self.models_tree.column("tools", width=60)
        self.models_tree.column("quant", width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.models_tree.yview)
        self.models_tree.configure(yscrollcommand=scrollbar.set)
        
        self.models_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопки управления моделями
        model_btn_frame = ttk.Frame(self.models_tab)
        model_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(model_btn_frame, text="🔄 Обновить список", command=self._refresh_models).pack(side=tk.LEFT, padx=5)
        
        # Конфигурация по умолчанию
        config_frame = ttk.LabelFrame(self.models_tab, text="Модель по умолчанию")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(config_frame, text="Для Director:").grid(row=0, column=0, padx=5, pady=5)
        self.director_model_var = tk.StringVar()
        self.director_model_combo = ttk.Combobox(config_frame, textvariable=self.director_model_var, width=40)
        self.director_model_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(config_frame, text="Для Worker:").grid(row=1, column=0, padx=5, pady=5)
        self.worker_model_var = tk.StringVar()
        self.worker_model_combo = ttk.Combobox(config_frame, textvariable=self.worker_model_var, width=40)
        self.worker_model_combo.grid(row=1, column=1, padx=5, pady=5)
        
    def _setup_roles_tab(self):
        """Настройка таба Роли."""
        # Список ролей
        list_frame = ttk.LabelFrame(self.roles_tab, text="Роли")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.roles_listbox = tk.Listbox(list_frame, width=50)
        self.roles_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        roles_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.roles_listbox.yview)
        self.roles_listbox.configure(yscrollcommand=roles_scrollbar.set)
        roles_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загрузка списка ролей
        self._refresh_roles()
        
        # Редактор YAML
        editor_frame = ttk.LabelFrame(self.roles_tab, text="Редактор YAML")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.role_editor = scrolledtext.ScrolledText(editor_frame, height=15, font=("Consolas", 10))
        self.role_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления ролями
        role_btn_frame = ttk.Frame(self.roles_tab)
        role_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(role_btn_frame, text="📂 Открыть", command=self._open_role).pack(side=tk.LEFT, padx=5)
        ttk.Button(role_btn_frame, text="💾 Сохранить", command=self._save_role).pack(side=tk.LEFT, padx=5)
        ttk.Button(role_btn_frame, text="✅ Валидировать", command=self._validate_role).pack(side=tk.LEFT, padx=5)
        
        # Привязка выбора роли
        self.roles_listbox.bind("<<ListboxSelect>>", self._on_role_select)
        
    def _setup_tools_tab(self):
        """Настройка таба Инструменты."""
        # Список инструментов
        list_frame = ttk.LabelFrame(self.tools_tab, text="Инструменты")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tools_listbox = tk.Listbox(list_frame, width=50)
        self.tools_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tools_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tools_listbox.yview)
        self.tools_listbox.configure(yscrollcommand=tools_scrollbar.set)
        tools_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загрузка списка инструментов
        self._refresh_tools()
        
        # Редактор JSON
        editor_frame = ttk.LabelFrame(self.tools_tab, text="Редактор JSON")
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tool_editor = scrolledtext.ScrolledText(editor_frame, height=15, font=("Consolas", 10))
        self.tool_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления инструментами
        tool_btn_frame = ttk.Frame(self.tools_tab)
        tool_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(tool_btn_frame, text="📂 Открыть", command=self._open_tool).pack(side=tk.LEFT, padx=5)
        ttk.Button(tool_btn_frame, text="💾 Сохранить", command=self._save_tool).pack(side=tk.LEFT, padx=5)
        ttk.Button(tool_btn_frame, text="✅ Валидировать схему", command=self._validate_tool).pack(side=tk.LEFT, padx=5)
        
        # Привязка выбора инструмента
        self.tools_listbox.bind("<<ListboxSelect>>", self._on_tool_select)
        
    def _setup_memory_tab(self):
        """Настройка таба Память."""
        # Выбор типа памяти
        type_frame = ttk.Frame(self.memory_tab)
        type_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(type_frame, text="Тип памяти:").pack(side=tk.LEFT, padx=5)
        self.memory_type_var = tk.StringVar(value="project")
        
        ttk.Radiobutton(type_frame, text="Проект", variable=self.memory_type_var, value="project", command=self._load_memory).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Пользователь", variable=self.memory_type_var, value="user", command=self._load_memory).pack(side=tk.LEFT, padx=5)
        
        # Просмотрщик памяти
        view_frame = ttk.LabelFrame(self.memory_tab, text="Содержимое")
        view_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.memory_viewer = scrolledtext.ScrolledText(view_frame, height=20, font=("Consolas", 10))
        self.memory_viewer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопки управления памятью
        memory_btn_frame = ttk.Frame(self.memory_tab)
        memory_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(memory_btn_frame, text="🔄 Обновить", command=self._load_memory).pack(side=tk.LEFT, padx=5)
        ttk.Button(memory_btn_frame, text="📤 Экспорт", command=self._export_memory).pack(side=tk.LEFT, padx=5)
        ttk.Button(memory_btn_frame, text="🗑 Очистить", command=self._clear_memory).pack(side=tk.LEFT, padx=5)
        
    def _setup_logs_tab(self):
        """Настройка таба Логи."""
        # Выбор лога
        log_frame = ttk.Frame(self.logs_tab)
        log_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(log_frame, text="Лог:").pack(side=tk.LEFT, padx=5)
        self.log_type_var = tk.StringVar(value="chat_history")
        
        self.log_combo = ttk.Combobox(log_frame, textvariable=self.log_type_var, values=["chat_history", "api_calls", "errors", "director", "worker"])
        self.log_combo.pack(side=tk.LEFT, padx=5)
        self.log_combo.bind("<<ComboboxSelected>>", lambda e: self._load_log())
        
        ttk.Button(log_frame, text="🔄 Обновить", command=self._load_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_frame, text="🗑 Очистить", command=self._clear_log).pack(side=tk.LEFT, padx=5)
        
        # Автоматическое обновление логов
        self.auto_refresh_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(log_frame, text="Автообновление", variable=self.auto_refresh_var, command=self._toggle_auto_refresh).pack(side=tk.LEFT, padx=10)
        
        # Просмотрщик логов
        view_frame = ttk.LabelFrame(self.logs_tab, text="Содержимое лога")
        view_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.log_viewer = scrolledtext.ScrolledText(view_frame, height=25, font=("Consolas", 9))
        self.log_viewer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Кнопка прокрутки вниз
        ttk.Button(view_frame, text="⬇ Вниз", command=lambda: self.log_viewer.see(tk.END)).pack(anchor=tk.E, pady=(5, 0))
        
        # Запуск автообновления если включено
        self.auto_refresh_id = None
        
    def _toggle_auto_refresh(self):
        """Переключение автообновления логов."""
        if self.auto_refresh_var.get():
            self._schedule_auto_refresh()
        else:
            if self.auto_refresh_id:
                self.frame.after_cancel(self.auto_refresh_id)
                self.auto_refresh_id = None
                
    def _schedule_auto_refresh(self):
        """Планирование автообновления."""
        if self.auto_refresh_var.get():
            self._load_log()
            self.auto_refresh_id = self.frame.after(2000, self._schedule_auto_refresh)
        
    def _refresh_models(self):
        """Обновление списка моделей."""
        logger.info("Пользователь нажал кнопку обновления списка моделей")
        
        # Очистка treeview
        for item in self.models_tree.get_children():
            self.models_tree.delete(item)
            
        if self.main_window.model_registry:
            logger.debug("Получение списка моделей из реестра")
            models = self.main_window.model_registry.list_models()
            logger.info(f"Найдено {len(models)} моделей в реестре")
            
            for model in models:
                # ModelInfo - это dataclass, используем атрибуты напрямую
                model_id = model.id
                context = model.context_window
                tools = "✅" if model.supports_tools else "❌"
                quant = model.quantization or "N/A"
                
                logger.debug(f"Добавление модели в список: {model_id}, контекст={context}, tools={tools}")
                self.models_tree.insert("", tk.END, values=(model_id, f"{context}k", tools, quant))
                
                # Добавление в combobox
                current = self.director_model_combo.cget("values")
                if model_id not in current:
                    logger.debug(f"Добавление модели {model_id} в выпадающие списки")
                    self.director_model_combo.configure(values=list(current) + [model_id])
                    self.worker_model_combo.configure(values=list(current) + [model_id])
        else:
            logger.warning("ModelRegistry ещё не инициализирован")
            messagebox.showwarning("Предупреждение", "Сначала создайте или откройте проект")
                    
    def _refresh_roles(self):
        """Обновление списка ролей."""
        self.roles_listbox.delete(0, tk.END)
        
        roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
        if roles_dir.exists():
            for yaml_file in roles_dir.glob("*.yaml"):
                self.roles_listbox.insert(tk.END, yaml_file.stem)
                
    def _refresh_tools(self):
        """Обновление списка инструментов."""
        self.tools_listbox.delete(0, tk.END)
        
        tools_dir = Path(__file__).parent.parent.parent / "config" / "tools"
        if tools_dir.exists():
            for json_file in tools_dir.glob("*.json"):
                self.tools_listbox.insert(tk.END, json_file.stem)
                
    def _on_role_select(self, event):
        """Выбор роли для редактирования."""
        selection = self.roles_listbox.curselection()
        if not selection:
            return
            
        role_name = self.roles_listbox.get(selection[0])
        roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
        role_file = roles_dir / f"{role_name}.yaml"
        
        if role_file.exists():
            with open(role_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.role_editor.delete("1.0", tk.END)
            self.role_editor.insert("1.0", content)
            
    def _on_tool_select(self, event):
        """Выбор инструмента для редактирования."""
        selection = self.tools_listbox.curselection()
        if not selection:
            return
            
        tool_name = self.tools_listbox.get(selection[0])
        tools_dir = Path(__file__).parent.parent.parent / "config" / "tools"
        tool_file = tools_dir / f"{tool_name}.json"
        
        if tool_file.exists():
            with open(tool_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.tool_editor.delete("1.0", tk.END)
            self.tool_editor.insert("1.0", content)
            
    def _open_role(self):
        """Открытие файла роли."""
        filename = filedialog.askopenfilename(
            title="Открыть роль",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.role_editor.delete("1.0", tk.END)
            self.role_editor.insert("1.0", content)
            
    def _save_role(self):
        """Сохранение роли."""
        selection = self.roles_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите роль для сохранения")
            return
            
        role_name = self.roles_listbox.get(selection[0])
        roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
        role_file = roles_dir / f"{role_name}.yaml"
        
        content = self.role_editor.get("1.0", tk.END)
        with open(role_file, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Успех", f"Роль {role_name} сохранена")
        
    def _validate_role(self):
        """Валидация роли."""
        content = self.role_editor.get("1.0", tk.END)
        try:
            data = yaml.safe_load(content)
            required_fields = ["system_prompt", "allowed_tools"]
            missing = [f for f in required_fields if f not in data]
            
            if missing:
                messagebox.showwarning("Предупреждение", f"Отсутствуют поля: {missing}")
            else:
                messagebox.showinfo("Успех", "Роль валидна")
        except yaml.YAMLError as e:
            messagebox.showerror("Ошибка", f"Неверный YAML: {e}")
            
    def _open_tool(self):
        """Открытие файла инструмента."""
        filename = filedialog.askopenfilename(
            title="Открыть инструмент",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.tool_editor.delete("1.0", tk.END)
            self.tool_editor.insert("1.0", content)
            
    def _save_tool(self):
        """Сохранение инструмента."""
        selection = self.tools_listbox.curselection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите инструмент для сохранения")
            return
            
        tool_name = self.tools_listbox.get(selection[0])
        tools_dir = Path(__file__).parent.parent.parent / "config" / "tools"
        tool_file = tools_dir / f"{tool_name}.json"
        
        content = self.tool_editor.get("1.0", tk.END)
        with open(tool_file, "w", encoding="utf-8") as f:
            f.write(content)
        messagebox.showinfo("Успех", f"Инструмент {tool_name} сохранён")
        
    def _validate_tool(self):
        """Валидация инструмента."""
        content = self.tool_editor.get("1.0", tk.END)
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                messagebox.showwarning("Предупреждение", "Ожидается список инструментов")
                return
                
            for tool in data:
                if "name" not in tool:
                    messagebox.showwarning("Предупреждение", "Инструмент без имени")
                    return
                if "parameters" not in tool:
                    messagebox.showwarning("Предупреждение", f"Инструмент {tool.get('name')} без параметров")
                    return
                    
            messagebox.showinfo("Успех", "Схема инструмента валидна")
        except json.JSONDecodeError as e:
            messagebox.showerror("Ошибка", f"Неверный JSON: {e}")
            
    def _load_memory(self):
        """Загрузка памяти."""
        if not self.main_window.current_project_path:
            self.memory_viewer.delete("1.0", tk.END)
            self.memory_viewer.insert("1.0", "Нет активного проекта")
            return
            
        memory_type = self.memory_type_var.get()
        memory_file = self.main_window.current_project_path / "memory" / f"{memory_type}.json"
        
        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.memory_viewer.delete("1.0", tk.END)
            self.memory_viewer.insert("1.0", content)
        else:
            self.memory_viewer.delete("1.0", tk.END)
            self.memory_viewer.insert("1.0", "Память пуста")
            
    def _export_memory(self):
        """Экспорт памяти."""
        if not self.main_window.current_project_path:
            return
            
        memory_type = self.memory_type_var.get()
        memory_file = self.main_window.current_project_path / "memory" / f"{memory_type}.json"
        
        if memory_file.exists():
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                initialfile=f"{memory_type}_memory.json"
            )
            if filename:
                with open(memory_file, "r", encoding="utf-8") as f:
                    content = f.read()
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
                    
    def _clear_memory(self):
        """Очистка памяти."""
        if messagebox.askyesno("Подтверждение", "Очистить память?"):
            if self.main_window.current_project_path:
                memory_type = self.memory_type_var.get()
                memory_file = self.main_window.current_project_path / "memory" / f"{memory_type}.json"
                if memory_file.exists():
                    with open(memory_file, "w", encoding="utf-8") as f:
                        json.dump({}, f, indent=2)
                self._load_memory()
                
    def _load_log(self):
        """Загрузка лога."""
        if not self.main_window.current_project_path:
            # Попытка загрузки глобального лога
            global_log = Path(__file__).parent.parent.parent / "conductor.log"
            if global_log.exists():
                try:
                    with open(global_log, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    self.log_viewer.delete("1.0", tk.END)
                    self.log_viewer.insert("1.0", content)
                    self.log_viewer.see(tk.END)
                    return
                except Exception as e:
                    pass
            self.log_viewer.delete("1.0", tk.END)
            self.log_viewer.insert("1.0", "Нет активного проекта")
            return
            
        log_type = self.log_type_var.get()
        log_file = self.main_window.current_project_path / "logs" / f"{log_type}.log"
        
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.log_viewer.delete("1.0", tk.END)
                self.log_viewer.insert("1.0", content)
                self.log_viewer.see(tk.END)  # Прокрутка вниз
            except Exception as e:
                self.log_viewer.delete("1.0", tk.END)
                self.log_viewer.insert("1.0", f"Ошибка чтения лога: {e}")
        else:
            self.log_viewer.delete("1.0", tk.END)
            self.log_viewer.insert("1.0", "Лог пуст")
            
    def _clear_log(self):
        """Очистка лога."""
        if messagebox.askyesno("Подтверждение", "Очистить лог?"):
            if self.main_window.current_project_path:
                log_type = self.log_type_var.get()
                log_file = self.main_window.current_project_path / "logs" / f"{log_type}.log"
                if log_file.exists():
                    with open(log_file, "w", encoding="utf-8") as f:
                        pass
                self._load_log()
                
    def _apply_changes(self):
        """Применение изменений."""
        # Сохранение настроек моделей в models.json
        director_model = self.director_model_var.get()
        worker_model = self.worker_model_var.get()
        
        # Обновление director.yaml с выбранной моделью
        if director_model:
            roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
            director_yaml = roles_dir / "director.yaml"
            if director_yaml.exists():
                with open(director_yaml, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f) or {}
                
                if "model_preference" not in content:
                    content["model_preference"] = director_model
                else:
                    content["model_preference"] = director_model
                    
                with open(director_yaml, "w", encoding="utf-8") as f:
                    yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
                logger.info(f"Обновлена модель Director на {director_model}")
        
        messagebox.showinfo("Успех", f"Настройки применены\nDirector: {director_model}\nWorker: {worker_model}")
        
    def show_settings_tab(self):
        """Показ таба настроек."""
        self.notebook.select(0)  # Переключение на первый таб
