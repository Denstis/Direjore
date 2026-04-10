"""
ConfigPanel — панель конфигурации на CustomTkinter.

Табы: Модели, Роли, Инструменты, Память, Логи.
"""

import json
import logging
from pathlib import Path
from typing import Optional, List

import customtkinter as ctk
import yaml

logger = logging.getLogger(__name__)


class ConfigPanel(ctk.CTkFrame):
    """Панель конфигурации."""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        
        self._create_widgets()

    def _create_widgets(self):
        """Создание виджетов."""
        # Заголовок
        header_label = ctk.CTkLabel(
            self, 
            text="⚙️ КОНФИГУРАЦИЯ", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header_label.pack(pady=10)
        
        # Notebook для табов
        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Табы
        self.tab_models = self.notebook.add("📦 Модели")
        self.tab_roles = self.notebook.add("👥 Роли")
        self.tab_tools = self.notebook.add("🛠 Инструменты")
        self.tab_memory = self.notebook.add("🧠 Память")
        self.tab_logs = self.notebook.add("📜 Логи")
        
        self._setup_models_tab()
        self._setup_roles_tab()
        self._setup_tools_tab()
        self._setup_memory_tab()
        self._setup_logs_tab()
        
        # Кнопка Применить
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=5, pady=(0, 5))
        
        ctk.CTkButton(btn_frame, text="💾 Применить", command=self._apply_changes).pack(side="right")

    def _setup_models_tab(self):
        """Настройка таба Модели."""
        # Список моделей
        list_frame = ctk.CTkFrame(self.tab_models)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(list_frame, text="Доступные модели:", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        # Scrollable frame для списка
        self.models_scroll = ctk.CTkScrollableFrame(list_frame, height=200)
        self.models_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.model_labels = []
        
        # Конфигурация по умолчанию
        config_frame = ctk.CTkFrame(self.tab_models)
        config_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(config_frame, text="Модель для Director:").pack(pady=5)
        self.director_model_var = ctk.StringVar(value="")
        self.director_model_combo = ctk.CTkComboBox(config_frame, variable=self.director_model_var, width=280)
        self.director_model_combo.pack(pady=5)
        
        ctk.CTkLabel(config_frame, text="Модель для Worker:").pack(pady=5)
        self.worker_model_var = ctk.StringVar(value="")
        self.worker_model_combo = ctk.CTkComboBox(config_frame, variable=self.worker_model_var, width=280)
        self.worker_model_combo.pack(pady=5)
        
        # Кнопка обновления
        ctk.CTkButton(self.tab_models, text="🔄 Обновить список", command=self.refresh_models).pack(pady=5)

    def _setup_roles_tab(self):
        """Настройка таба Роли."""
        # Список ролей
        list_frame = ctk.CTkFrame(self.tab_roles)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(list_frame, text="Роли:", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.roles_scroll = ctk.CTkScrollableFrame(list_frame, height=150)
        self.roles_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.role_buttons = []
        self._refresh_roles()
        
        # Редактор YAML
        editor_frame = ctk.CTkFrame(self.tab_roles)
        editor_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(editor_frame, text="Редактор YAML:").pack(pady=5)
        self.role_editor = ctk.CTkTextbox(editor_frame, height=150)
        self.role_editor.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Кнопки управления
        btn_frame = ctk.CTkFrame(self.tab_roles)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(btn_frame, text="📂 Открыть", command=self._open_role, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Сохранить", command=self._save_role, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="✅ Валидировать", command=self._validate_role, width=100).pack(side="left", padx=5)

    def _setup_tools_tab(self):
        """Настройка таба Инструменты."""
        # Список инструментов
        list_frame = ctk.CTkFrame(self.tab_tools)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(list_frame, text="Инструменты:", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.tools_scroll = ctk.CTkScrollableFrame(list_frame, height=150)
        self.tools_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tool_buttons = []
        self._refresh_tools()
        
        # Редактор JSON
        editor_frame = ctk.CTkFrame(self.tab_tools)
        editor_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(editor_frame, text="Редактор JSON:").pack(pady=5)
        self.tool_editor = ctk.CTkTextbox(editor_frame, height=150)
        self.tool_editor.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Кнопки управления
        btn_frame = ctk.CTkFrame(self.tab_tools)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(btn_frame, text="📂 Открыть", command=self._open_tool, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 Сохранить", command=self._save_tool, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="✅ Валидировать", command=self._validate_tool, width=100).pack(side="left", padx=5)

    def _setup_memory_tab(self):
        """Настройка таба Память."""
        # Выбор типа памяти
        type_frame = ctk.CTkFrame(self.tab_memory)
        type_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(type_frame, text="Тип памяти:").pack(side="left", padx=5)
        self.memory_type_var = ctk.StringVar(value="project")
        
        ctk.CTkRadioButton(type_frame, text="Проект", variable=self.memory_type_var, value="project", command=self._load_memory).pack(side="left", padx=5)
        ctk.CTkRadioButton(type_frame, text="Пользователь", variable=self.memory_type_var, value="user", command=self._load_memory).pack(side="left", padx=5)
        
        # Просмотрщик памяти
        view_frame = ctk.CTkFrame(self.tab_memory)
        view_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(view_frame, text="Содержимое:").pack(pady=5)
        self.memory_viewer = ctk.CTkTextbox(view_frame, height=300)
        self.memory_viewer.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Кнопки управления
        btn_frame = ctk.CTkFrame(self.tab_memory)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(btn_frame, text="🔄 Обновить", command=self._load_memory, width=100).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🗑 Очистить", command=self._clear_memory, width=100).pack(side="left", padx=5)

    def _setup_logs_tab(self):
        """Настройка таба Логи."""
        # Выбор лога
        log_frame = ctk.CTkFrame(self.tab_logs)
        log_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(log_frame, text="Лог:").pack(side="left", padx=5)
        self.log_type_var = ctk.StringVar(value="chat_history")
        
        self.log_combo = ctk.CTkComboBox(log_frame, variable=self.log_type_var, values=["chat_history", "api_calls", "errors", "director", "worker"])
        self.log_combo.pack(side="left", padx=5)
        
        ctk.CTkButton(log_frame, text="🔄 Обновить", command=self._load_log, width=100).pack(side="left", padx=5)
        ctk.CTkButton(log_frame, text="🗑 Очистить", command=self._clear_log, width=100).pack(side="left", padx=5)
        
        # Автоматическое обновление
        self.auto_refresh_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(log_frame, text="Автообновление", variable=self.auto_refresh_var, command=self._toggle_auto_refresh).pack(side="left", padx=10)
        
        # Просмотрщик логов
        view_frame = ctk.CTkFrame(self.tab_logs)
        view_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(view_frame, text="Содержимое лога:").pack(pady=5)
        self.log_viewer = ctk.CTkTextbox(view_frame, height=300)
        self.log_viewer.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Автообновление
        self.auto_refresh_id = None

    def refresh_models(self):
        """Обновление списка моделей."""
        # Очистка
        for widget in self.models_scroll.winfo_children():
            widget.destroy()
        self.model_labels = []
        
        if self.main_window.model_registry:
            models = self.main_window.model_registry.list_models()
            
            for model in models:
                model_id = model.id
                context = model.context_window
                tools = "✅" if model.supports_tools else "❌"
                
                model_frame = ctk.CTkFrame(self.models_scroll)
                model_frame.pack(fill="x", pady=2, padx=5)
                
                ctk.CTkLabel(model_frame, text=f"📦 {model_id}", wraplength=250, justify="left").pack(side="left", padx=5)
                ctk.CTkLabel(model_frame, text=f"{context}k {tools}", width=80).pack(side="right", padx=5)
                
                self.model_labels.append(model_frame)
            
            # Обновление combobox
            model_ids = [m.id for m in models]
            current_director = self.director_model_var.get()
            current_worker = self.worker_model_var.get()
            
            self.director_model_combo.configure(values=model_ids)
            self.worker_model_combo.configure(values=model_ids)
            
            if not current_director and model_ids:
                self.director_model_var.set(model_ids[0])
            if not current_worker and model_ids:
                self.worker_model_var.set(model_ids[0])
        else:
            ctk.CTkLabel(self.models_scroll, text="Нет подключенных моделей").pack(pady=10)

    def set_model_options(self, model_ids: List[str]):
        """Установка опций моделей в combobox."""
        self.director_model_combo.configure(values=model_ids)
        self.worker_model_combo.configure(values=model_ids)
        
        if model_ids:
            if not self.director_model_var.get():
                self.director_model_var.set(model_ids[0])
            if not self.worker_model_var.get():
                self.worker_model_var.set(model_ids[0])

    def _refresh_roles(self):
        """Обновление списка ролей."""
        for widget in self.roles_scroll.winfo_children():
            widget.destroy()
        self.role_buttons = []
        
        roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
        if roles_dir.exists():
            for yaml_file in sorted(roles_dir.glob("*.yaml")):
                role_name = yaml_file.stem
                
                btn = ctk.CTkButton(
                    self.roles_scroll,
                    text=f"👤 {role_name}",
                    command=lambda rn=role_name: self._load_role(rn),
                    anchor="w"
                )
                btn.pack(fill="x", pady=2, padx=5)
                self.role_buttons.append(btn)

    def _refresh_tools(self):
        """Обновление списка инструментов."""
        for widget in self.tools_scroll.winfo_children():
            widget.destroy()
        self.tool_buttons = []
        
        tools_dir = Path(__file__).parent.parent.parent / "config" / "tools"
        if tools_dir.exists():
            for json_file in sorted(tools_dir.glob("*.json")):
                tool_name = json_file.stem
                
                btn = ctk.CTkButton(
                    self.tools_scroll,
                    text=f"🛠 {tool_name}",
                    command=lambda tn=tool_name: self._load_tool(tn),
                    anchor="w"
                )
                btn.pack(fill="x", pady=2, padx=5)
                self.tool_buttons.append(btn)

    def _load_role(self, role_name: str):
        """Загрузка роли для редактирования."""
        roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
        role_file = roles_dir / f"{role_name}.yaml"
        
        if role_file.exists():
            with open(role_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.role_editor.delete("1.0", "end")
            self.role_editor.insert("1.0", content)

    def _load_tool(self, tool_name: str):
        """Загрузка инструмента для редактирования."""
        tools_dir = Path(__file__).parent.parent.parent / "config" / "tools"
        tool_file = tools_dir / f"{tool_name}.json"
        
        if tool_file.exists():
            with open(tool_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.tool_editor.delete("1.0", "end")
            self.tool_editor.insert("1.0", content)

    def _open_role(self):
        """Открытие файла роли."""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="Открыть роль",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.role_editor.delete("1.0", "end")
            self.role_editor.insert("1.0", content)

    def _save_role(self):
        """Сохранение роли."""
        ctk.messagebox.showinfo("Инфо", "Выберите роль из списка для сохранения")

    def _validate_role(self):
        """Валидация роли."""
        content = self.role_editor.get("1.0", "end")
        try:
            data = yaml.safe_load(content)
            required_fields = ["system_prompt", "allowed_tools"]
            missing = [f for f in required_fields if f not in (data or {})]

            if missing:
                ctk.messagebox.showwarning("Предупреждение", f"Отсутствуют поля: {missing}")
            else:
                ctk.messagebox.showinfo("Успех", "Роль валидна")
        except yaml.YAMLError as e:
            ctk.messagebox.showerror("Ошибка", f"Неверный YAML: {e}")

    def _open_tool(self):
        """Открытие файла инструмента."""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            title="Открыть инструмент",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
            self.tool_editor.delete("1.0", "end")
            self.tool_editor.insert("1.0", content)

    def _save_tool(self):
        """Сохранение инструмента."""
        ctk.messagebox.showinfo("Инфо", "Выберите инструмент из списка для сохранения")

    def _validate_tool(self):
        """Валидация инструмента."""
        content = self.tool_editor.get("1.0", "end")
        try:
            data = json.loads(content)
            if not isinstance(data, list):
                ctk.messagebox.showwarning("Предупреждение", "Ожидается список инструментов")
                return

            for tool in data:
                if "name" not in tool:
                    ctk.messagebox.showwarning("Предупреждение", "Инструмент без имени")
                    return

            ctk.messagebox.showinfo("Успех", "Схема инструмента валидна")
        except json.JSONDecodeError as e:
            ctk.messagebox.showerror("Ошибка", f"Неверный JSON: {e}")

    def _load_memory(self):
        """Загрузка памяти."""
        if not self.main_window.current_project_path:
            self.memory_viewer.delete("1.0", "end")
            self.memory_viewer.insert("1.0", "Нет активного проекта")
            return

        memory_type = self.memory_type_var.get()
        memory_file = self.main_window.current_project_path / "memory" / f"{memory_type}.json"

        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.memory_viewer.delete("1.0", "end")
            self.memory_viewer.insert("1.0", content)
        else:
            self.memory_viewer.delete("1.0", "end")
            self.memory_viewer.insert("1.0", "Память пуста")

    def _clear_memory(self):
        """Очистка памяти."""
        if ctk.messagebox.askyesno("Подтверждение", "Очистить память?"):
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
            global_log = Path(__file__).parent.parent.parent / "conductor.log"
            if global_log.exists():
                try:
                    with open(global_log, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    self.log_viewer.delete("1.0", "end")
                    self.log_viewer.insert("1.0", content)
                    self.log_viewer.see("end")
                    return
                except Exception:
                    pass
            self.log_viewer.delete("1.0", "end")
            self.log_viewer.insert("1.0", "Нет активного проекта")
            return

        log_type = self.log_type_var.get()
        log_file = self.main_window.current_project_path / "logs" / f"{log_type}.log"

        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                self.log_viewer.delete("1.0", "end")
                self.log_viewer.insert("1.0", content)
                self.log_viewer.see("end")
            except Exception as e:
                self.log_viewer.delete("1.0", "end")
                self.log_viewer.insert("1.0", f"Ошибка чтения лога: {e}")
        else:
            self.log_viewer.delete("1.0", "end")
            self.log_viewer.insert("1.0", "Лог пуст")

    def _clear_log(self):
        """Очистка лога."""
        if ctk.messagebox.askyesno("Подтверждение", "Очистить лог?"):
            if self.main_window.current_project_path:
                log_type = self.log_type_var.get()
                log_file = self.main_window.current_project_path / "logs" / f"{log_type}.log"
                if log_file.exists():
                    with open(log_file, "w", encoding="utf-8") as f:
                        pass
                self._load_log()

    def _toggle_auto_refresh(self):
        """Переключение автообновления логов."""
        if self.auto_refresh_var.get():
            self._schedule_auto_refresh()
        else:
            if self.auto_refresh_id:
                self.after_cancel(self.auto_refresh_id)
                self.auto_refresh_id = None

    def _schedule_auto_refresh(self):
        """Планирование автообновления."""
        if self.auto_refresh_var.get():
            self._load_log()
            self.auto_refresh_id = self.after(2000, self._schedule_auto_refresh)

    def _apply_changes(self):
        """Применение изменений."""
        director_model = self.director_model_var.get()
        worker_model = self.worker_model_var.get()

        # Обновление director.yaml с выбранной моделью
        if director_model:
            roles_dir = Path(__file__).parent.parent.parent / "config" / "roles"
            director_yaml = roles_dir / "director.yaml"
            if director_yaml.exists():
                with open(director_yaml, "r", encoding="utf-8") as f:
                    content = yaml.safe_load(f) or {}

                content["model_preference"] = director_model

                with open(director_yaml, "w", encoding="utf-8") as f:
                    yaml.dump(content, f, default_flow_style=False, allow_unicode=True)
                logger.info(f"Обновлена модель Director на {director_model}")

        ctk.messagebox.showinfo("Успех", f"Настройки применены\nDirector: {director_model}\nWorker: {worker_model}")
