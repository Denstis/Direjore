"""
Главное окно приложения на CustomTkinter: bridge asyncio ↔ GUI.

Использует queue.Queue + after() для безопасной доставки событий.
Современный UI с поддержкой тем, спойлеров, интерактивного общения.
"""

import asyncio
import json
import logging
import queue
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import customtkinter as ctk
import yaml

from src.core.lm_client import LMStudioClient
from src.core.model_registry import ModelRegistry
from src.core.tool_registry import ToolRegistry
from src.director.conductor import Conductor
from src.memory.manager import MemoryManager

logger = logging.getLogger(__name__)


class AsyncBridge:
    """Мост между asyncio и GUI."""

    def __init__(self, app):
        self.app = app
        self.gui_queue: queue.Queue = queue.Queue()
        self.asyncio_loop: Optional[asyncio.AbstractEventLoop] = None
        self.asyncio_thread: Optional[threading.Thread] = None

    def start_asyncio(self) -> None:
        """Запуск asyncio loop в отдельном потоке."""
        def run_loop():
            self.asyncio_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.asyncio_loop)
            self.asyncio_loop.run_forever()

        self.asyncio_thread = threading.Thread(target=run_loop, daemon=True)
        self.asyncio_thread.start()
        logger.info("Asyncio loop запущен в фоне")

    def run_coroutine(self, coro):
        """Выполнение coroutine в asyncio loop."""
        if not self.asyncio_loop:
            raise RuntimeError("Asyncio loop не запущен")
        return asyncio.run_coroutine_threadsafe(coro, self.asyncio_loop)

    def poll_gui_queue(self) -> None:
        """Опрос очереди GUI (вызывается через after)."""
        try:
            while True:
                event = self.gui_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
            
        # Продолжение опроса
        self.app.after(50, self.poll_gui_queue)

    def _handle_event(self, event: dict) -> None:
        """Обработка события из очереди."""
        event_type = event.get("type")
        
        logger.debug(f"Обработка события GUI: {event_type}, данные: {event}")

        if event_type == "stage_changed":
            self.app.on_stage_changed(event)
        elif event_type == "ask_user":
            logger.info(f"Событие ask_user получено: question={event.get('question', 'N/A')[:50] if event.get('question') else 'пустой'}")
            self.app.on_ask_user(event)
        elif event_type == "delegated":
            self.app.on_delegated(event)
        elif event_type == "tool_call":
            self.app.on_tool_call(event)
        elif event_type == "tool_result":
            self.app.on_tool_result(event)
        elif event_type == "agent_done":
            self.app.on_agent_done(event)
        elif event_type == "final":
            self.app.on_final(event)
        elif event_type == "error":
            self.app.on_error(event)


class SettingsDialog(ctk.CTkToplevel):
    """Диалог настроек со всеми параметрами модели и запросов."""

    def __init__(self, parent, settings: dict, on_save: callable):
        super().__init__(parent)
        self.title("⚙️ Настройки")
        self.geometry("800x700")
        self.resizable(True, True)
        
        self.settings = settings
        self.on_save = on_save
        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        self._create_widgets()

    def _create_widgets(self):
        """Создание виджетов настроек."""
        # Notebook для табов
        self.notebook = ctk.CTkTabview(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Табы
        self.tab_lmstudio = self.notebook.add("LM Studio")
        self.tab_model = self.notebook.add("Параметры модели")
        self.tab_request = self.notebook.add("Параметры запроса")
        self.tab_limits = self.notebook.add("Лимиты")
        self.tab_project = self.notebook.add("Проект")
        
        self._setup_lmstudio_tab()
        self._setup_model_tab()
        self._setup_request_tab()
        self._setup_limits_tab()
        self._setup_project_tab()
        
        # Кнопки
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(btn_frame, text="💾 Сохранить", command=self._save_settings).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="❌ Отмена", command=self.destroy, fg_color="gray").pack(side="right", padx=5)

    def _setup_lmstudio_tab(self):
        """Настройка таба LM Studio."""
        lmstudio_config = self.settings.get("lmstudio", {})
        
        ctk.CTkLabel(self.tab_lmstudio, text="🔗 Подключение к LM Studio", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        # Base URL
        url_frame = ctk.CTkFrame(self.tab_lmstudio)
        url_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(url_frame, text="Base URL:", width=150, anchor="w").pack(side="left", padx=5)
        self.base_url_entry = ctk.CTkEntry(url_frame, width=400)
        self.base_url_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.base_url_entry.insert(0, lmstudio_config.get("base_url", "http://localhost:1234"))
        
        # API Key
        key_frame = ctk.CTkFrame(self.tab_lmstudio)
        key_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(key_frame, text="API Key:", width=150, anchor="w").pack(side="left", padx=5)
        self.api_key_entry = ctk.CTkEntry(key_frame, width=400)
        self.api_key_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.api_key_entry.insert(0, lmstudio_config.get("api_key", "lm-studio"))

    def _setup_model_tab(self):
        """Настройка таба параметров модели."""
        defaults = self.settings.get("defaults", {})
        
        ctk.CTkLabel(self.tab_model, text="🧠 Параметры модели", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        # Temperature
        temp_frame = ctk.CTkFrame(self.tab_model)
        temp_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(temp_frame, text="Temperature:", width=150, anchor="w").pack(side="left", padx=5)
        self.temperature_slider = ctk.CTkSlider(temp_frame, from_=0, to=2, number_of_steps=40, width=300)
        self.temperature_slider.pack(side="left", padx=5)
        self.temperature_slider.set(defaults.get("temperature", 0.7))
        self.temp_value_label = ctk.CTkLabel(temp_frame, text=f"{defaults.get('temperature', 0.7):.2f}", width=50)
        self.temp_value_label.pack(side="left", padx=5)
        self.temperature_slider.configure(command=lambda v: self.temp_value_label.configure(text=f"{v:.2f}"))
        
        # Top P
        topp_frame = ctk.CTkFrame(self.tab_model)
        topp_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(topp_frame, text="Top P:", width=150, anchor="w").pack(side="left", padx=5)
        self.top_p_slider = ctk.CTkSlider(topp_frame, from_=0, to=1, number_of_steps=20, width=300)
        self.top_p_slider.pack(side="left", padx=5)
        self.top_p_slider.set(defaults.get("top_p", 0.9))
        self.topp_value_label = ctk.CTkLabel(topp_frame, text=f"{defaults.get('top_p', 0.9):.2f}", width=50)
        self.topp_value_label.pack(side="left", padx=5)
        self.top_p_slider.configure(command=lambda v: self.topp_value_label.configure(text=f"{v:.2f}"))
        
        # Max Tokens
        tokens_frame = ctk.CTkFrame(self.tab_model)
        tokens_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(tokens_frame, text="Max Tokens:", width=150, anchor="w").pack(side="left", padx=5)
        self.max_tokens_entry = ctk.CTkEntry(tokens_frame, width=100)
        self.max_tokens_entry.pack(side="left", padx=5)
        self.max_tokens_entry.insert(0, str(defaults.get("max_tokens", 4096)))
        
        # Model Selection
        model_frame = ctk.CTkFrame(self.tab_model)
        model_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(model_frame, text="Model for Director:", width=150, anchor="w").pack(side="left", padx=5)
        self.director_model_var = ctk.StringVar(value=self.settings.get("defaults", {}).get("director_model", ""))
        self.director_model_combo = ctk.CTkComboBox(model_frame, variable=self.director_model_var, width=300)
        self.director_model_combo.pack(side="left", padx=5)
        self.director_model_combo.set(self.settings.get("defaults", {}).get("director_model", ""))
        
        worker_frame = ctk.CTkFrame(self.tab_model)
        worker_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(worker_frame, text="Model for Worker:", width=150, anchor="w").pack(side="left", padx=5)
        self.worker_model_var = ctk.StringVar(value=self.settings.get("defaults", {}).get("worker_model", ""))
        self.worker_model_combo = ctk.CTkComboBox(worker_frame, variable=self.worker_model_var, width=300)
        self.worker_model_combo.pack(side="left", padx=5)
        self.worker_model_combo.set(self.settings.get("defaults", {}).get("worker_model", ""))

    def _setup_request_tab(self):
        """Настройка таба параметров запроса."""
        timeouts = self.settings.get("timeouts", {})
        defaults = self.settings.get("defaults", {})
        
        ctk.CTkLabel(self.tab_request, text="📡 Параметры запроса", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        # Timeout
        timeout_frame = ctk.CTkFrame(self.tab_request)
        timeout_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(timeout_frame, text="LLM Request Timeout (sec):", width=200, anchor="w").pack(side="left", padx=5)
        self.llm_timeout_entry = ctk.CTkEntry(timeout_frame, width=100)
        self.llm_timeout_entry.pack(side="left", padx=5)
        self.llm_timeout_entry.insert(0, str(timeouts.get("llm_request", 120)))
        
        tool_timeout_frame = ctk.CTkFrame(self.tab_request)
        tool_timeout_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(tool_timeout_frame, text="Tool Execution Timeout (sec):", width=200, anchor="w").pack(side="left", padx=5)
        self.tool_timeout_entry = ctk.CTkEntry(tool_timeout_frame, width=100)
        self.tool_timeout_entry.pack(side="left", padx=5)
        self.tool_timeout_entry.insert(0, str(timeouts.get("tool_execution", 30)))
        
        # Parallel Tool Calls
        parallel_frame = ctk.CTkFrame(self.tab_request)
        parallel_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(parallel_frame, text="Parallel Tool Calls:", width=200, anchor="w").pack(side="left", padx=5)
        self.parallel_tools_var = ctk.BooleanVar(value=defaults.get("parallel_tool_calls", False))
        self.parallel_tools_switch = ctk.CTkSwitch(parallel_frame, variable=self.parallel_tools_var)
        self.parallel_tools_switch.pack(side="left", padx=5)
        
        # Stream
        stream_frame = ctk.CTkFrame(self.tab_request)
        stream_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(stream_frame, text="Stream Response:", width=200, anchor="w").pack(side="left", padx=5)
        self.stream_var = ctk.BooleanVar(value=defaults.get("stream", True))
        self.stream_switch = ctk.CTkSwitch(stream_frame, variable=self.stream_var)
        self.stream_switch.pack(side="left", padx=5)

    def _setup_limits_tab(self):
        """Настройка таба лимитов."""
        limits = self.settings.get("limits", {})
        
        ctk.CTkLabel(self.tab_limits, text="📊 Лимиты", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        # Max Iterations
        iter_frame = ctk.CTkFrame(self.tab_limits)
        iter_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(iter_frame, text="Max Iterations:", width=200, anchor="w").pack(side="left", padx=5)
        self.max_iterations_entry = ctk.CTkEntry(iter_frame, width=100)
        self.max_iterations_entry.pack(side="left", padx=5)
        self.max_iterations_entry.insert(0, str(limits.get("max_iterations", 10)))
        
        # Max Plan Steps
        steps_frame = ctk.CTkFrame(self.tab_limits)
        steps_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(steps_frame, text="Max Plan Steps:", width=200, anchor="w").pack(side="left", padx=5)
        self.max_plan_steps_entry = ctk.CTkEntry(steps_frame, width=100)
        self.max_plan_steps_entry.pack(side="left", padx=5)
        self.max_plan_steps_entry.insert(0, str(limits.get("max_plan_steps", 7)))
        
        # Max Context Tokens
        context_frame = ctk.CTkFrame(self.tab_limits)
        context_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(context_frame, text="Max Context Tokens:", width=200, anchor="w").pack(side="left", padx=5)
        self.max_context_entry = ctk.CTkEntry(context_frame, width=100)
        self.max_context_entry.pack(side="left", padx=5)
        self.max_context_entry.insert(0, str(limits.get("max_context_tokens", 28000)))

    def _setup_project_tab(self):
        """Настройка таба проекта."""
        ctk.CTkLabel(self.tab_project, text="📁 Настройки проекта", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        # Project Root
        root_frame = ctk.CTkFrame(self.tab_project)
        root_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(root_frame, text="Project Root:", width=150, anchor="w").pack(side="left", padx=5)
        self.project_root_entry = ctk.CTkEntry(root_frame, width=400)
        self.project_root_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.project_root_entry.insert(0, self.settings.get("project_root", "./projects"))
        
        browse_btn = ctk.CTkButton(root_frame, text="...", width=30, command=self._browse_project_root)
        browse_btn.pack(side="left", padx=5)
        
        # Log Level
        log_frame = ctk.CTkFrame(self.tab_project)
        log_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(log_frame, text="Log Level:", width=150, anchor="w").pack(side="left", padx=5)
        self.log_level_var = ctk.StringVar(value=self.settings.get("log_level", "INFO"))
        self.log_level_combo = ctk.CTkComboBox(log_frame, variable=self.log_level_var, values=["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.pack(side="left", padx=5)

    def _browse_project_root(self):
        """Выбор корневой директории проектов."""
        from tkinter import filedialog
        directory = filedialog.askdirectory(initialdir=Path.cwd())
        if directory:
            self.project_root_entry.delete(0, "end")
            self.project_root_entry.insert(0, directory)

    def _save_settings(self):
        """Сохранение настроек."""
        new_settings = {
            "lmstudio": {
                "base_url": self.base_url_entry.get(),
                "api_key": self.api_key_entry.get(),
            },
            "defaults": {
                "temperature": self.temperature_slider.get(),
                "top_p": self.top_p_slider.get(),
                "max_tokens": int(self.max_tokens_entry.get()) if self.max_tokens_entry.get().isdigit() else 4096,
                "director_model": self.director_model_var.get(),
                "worker_model": self.worker_model_var.get(),
                "parallel_tool_calls": self.parallel_tools_var.get(),
                "stream": self.stream_var.get(),
            },
            "timeouts": {
                "llm_request": int(self.llm_timeout_entry.get()) if self.llm_timeout_entry.get().isdigit() else 120,
                "tool_execution": int(self.tool_timeout_entry.get()) if self.tool_timeout_entry.get().isdigit() else 30,
            },
            "limits": {
                "max_iterations": int(self.max_iterations_entry.get()) if self.max_iterations_entry.get().isdigit() else 10,
                "max_plan_steps": int(self.max_plan_steps_entry.get()) if self.max_plan_steps_entry.get().isdigit() else 7,
                "max_context_tokens": int(self.max_context_entry.get()) if self.max_context_entry.get().isdigit() else 28000,
            },
            "project_root": self.project_root_entry.get(),
            "log_level": self.log_level_var.get(),
        }
        
        self.on_save(new_settings)
        self.destroy()


class ChatMessageFrame(ctk.CTkFrame):
    """Фрейм сообщения чата с поддержкой спойлеров."""

    def __init__(self, parent, role: str, content: str, timestamp: str):
        super().__init__(parent)
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.is_collapsed = False
        
        self._create_widgets()

    def _create_widgets(self):
        """Создание виджетов сообщения."""
        # Timestamp
        ts_label = ctk.CTkLabel(self, text=self.timestamp, font=ctk.CTkFont(size=9), text_color="gray")
        ts_label.pack(anchor="w", padx=5, pady=(5, 0))
        
        # Role icon and header
        role_icons = {
            "user": ("👤 Вы:", "#2D7FF9"),
            "assistant": ("🤖 Агент:", "#28A745"),
            "system": ("⚙️ Система:", "#6C757D"),
            "error": ("❌ Ошибка:", "#DC3545"),
            "tool": ("🔧 Инструмент:", "#FFC107"),
        }
        
        icon_text, color = role_icons.get(self.role, ("📝", "#6C757D"))
        
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=5, pady=0)
        
        role_label = ctk.CTkLabel(header_frame, text=icon_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=color)
        role_label.pack(side="left")
        
        # Content with spoiler support
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="x", padx=5, pady=5, anchor="w")
        
        if isinstance(self.content, dict):
            content_str = json.dumps(self.content, ensure_ascii=False, indent=2)
        else:
            content_str = str(self.content)
        
        # Check if collapsible (multi-line content from agent_done)
        if self.role == "assistant" and "\n" in content_str and len(content_str) > 200:
            lines = content_str.split("\n", 1)
            header_line = lines[0]
            body = lines[1] if len(lines) > 1 else ""
            
            # Header line
            ctk.CTkLabel(self.content_frame, text=header_line, wraplength=800, justify="left").pack(anchor="w")
            
            # Spoiler toggle button
            self.spoiler_btn = ctk.CTkButton(
                self.content_frame, 
                text="▼ Показать подробности", 
                width=150,
                height=25,
                fg_color="#e0e0e0",
                text_color="black",
                command=self._toggle_spoiler
            )
            self.spoiler_btn.pack(anchor="w", pady=(5, 0))
            
            # Hidden content frame
            self.spoiler_content = ctk.CTkFrame(self, fg_color="#f5f5f5")
            self.body_label = ctk.CTkLabel(self.spoiler_content, text=body, wraplength=800, justify="left")
            self.body_label.pack(padx=10, pady=10, anchor="w")
            
            self.is_collapsed = True
        else:
            ctk.CTkLabel(self.content_frame, text=content_str, wraplength=800, justify="left").pack(anchor="w")


class MainWindow(ctk.CTk):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        
        # Настройка темы
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.title("🎭 Дирижёр — Multi-Agent System")
        self.geometry("1600x1000")
        
        # Инициализация компонентов
        self.async_bridge = AsyncBridge(self)
        self.client: Optional[LMStudioClient] = None
        self.model_registry: Optional[ModelRegistry] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.conductor: Optional[Conductor] = None
        self.memory_manager: Optional[MemoryManager] = None
        
        # Текущий проект
        self.current_project_id: Optional[str] = None
        self.current_project_path: Optional[Path] = None
        
        # Загрузка настроек
        self.settings = self._load_settings()
        
        # Построение UI
        self._create_menu()
        self._create_layout()
        
        # Старт asyncio
        self.async_bridge.start_asyncio()
        self.async_bridge.poll_gui_queue()

    def _load_settings(self) -> dict:
        """Загрузка настроек из config/settings.yaml."""
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        
        if not settings_path.exists():
            return {}
            
        with open(settings_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _create_menu(self) -> None:
        """Создание меню."""
        self.menu_frame = ctk.CTkFrame(self, height=50)
        self.menu_frame.pack(fill="x", side="top")
        
        # Logo/Title
        title_label = ctk.CTkLabel(self.menu_frame, text="🎭 Дирижёр", font=ctk.CTkFont(size=18, weight="bold"))
        title_label.pack(side="left", padx=20, pady=10)
        
        # Menu buttons
        ctk.CTkButton(self.menu_frame, text="📁 Новый проект", command=self._new_project, width=120).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(self.menu_frame, text="📂 Открыть проект", command=self._open_project, width=120).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(self.menu_frame, text="💾 Переименовать", command=self._rename_project, width=120).pack(side="left", padx=5, pady=10)
        ctk.CTkButton(self.menu_frame, text="📤 Экспорт", command=self._export_project, width=100).pack(side="left", padx=5, pady=10)
        
        # Spacer
        ctk.CTkFrame(self.menu_frame, width=50, fg_color="transparent").pack(side="left", fill="x", expand=True)
        
        # Settings button
        ctk.CTkButton(self.menu_frame, text="⚙️ Настройки", command=self._show_settings, width=100).pack(side="right", padx=5, pady=10)
        
        # Connection status
        self.connection_label = ctk.CTkLabel(self.menu_frame, text="🔴 Не подключено", text_color="red")
        self.connection_label.pack(side="right", padx=10, pady=10)

    def _create_layout(self) -> None:
        """Создание основной раскладки."""
        # Главный PanedWindow-подобный контейнер
        main_container = ctk.CTkFrame(self)
        main_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Левая панель: Проект
        left_frame = ctk.CTkFrame(main_container, width=250)
        left_frame.pack(side="left", fill="y", padx=(0, 5))
        left_frame.pack_propagate(False)
        
        self.project_panel = ProjectPanel(left_frame, self)
        self.project_panel.pack(fill="both", expand=True)
        
        # Центральная панель: Чат
        center_frame = ctk.CTkFrame(main_container)
        center_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        self.chat_panel = ChatPanel(center_frame, self)
        self.chat_panel.pack(fill="both", expand=True)
        
        # Правая панель: Конфиг
        right_frame = ctk.CTkFrame(main_container, width=350)
        right_frame.pack(side="right", fill="y", padx=(5, 0))
        right_frame.pack_propagate(False)
        
        self.config_panel = ConfigPanel(right_frame, self)
        self.config_panel.pack(fill="both", expand=True)
        
        # Status bar
        self.status_bar = ctk.CTkFrame(self, height=30)
        self.status_bar.pack(fill="x", side="bottom")
        
        self.status_label = ctk.CTkLabel(self.status_bar, text="Готов", font=ctk.CTkFont(size=10))
        self.status_label.pack(side="left", padx=10)
        
        self.iteration_label = ctk.CTkLabel(self.status_bar, text="Итерация: 0", font=ctk.CTkFont(size=10))
        self.iteration_label.pack(side="right", padx=10)

    # =============================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # =============================================================================

    def on_stage_changed(self, event: dict) -> None:
        """Изменение стадии проекта."""
        stage = event.get('stage', 'unknown')
        self.project_panel.update_stage(stage)
        self.status_label.configure(text=f"Стадия: {stage}")

    def on_ask_user(self, event: dict) -> None:
        """Запрос уточнения у пользователя."""
        try:
            question = event.get('question', '')
            options = event.get('options', [])
            
            logger.info(f"Получен вопрос от пользователя: {question[:50] if question else 'пустой'}...")
            
            self.chat_panel.show_question(question, options)
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса пользователю: {e}", exc_info=True)
            self.chat_panel.add_message("error", f"❌ Ошибка обработки вопроса: {e}")

    def on_delegated(self, event: dict) -> None:
        """Делегирование задачи."""
        role = event.get('role', '')
        task = event.get('task', '')
        tools = event.get('tools', [])
        
        message = f"🤖 Делегировано роли **{role}**\n\n📋 Задача: {task}"
        
        if tools:
            tools_str = ', '.join(tools)
            message += f"\n\n🔧 Доступные инструменты: {tools_str}"
        
        self.chat_panel.add_message("system", message)

    def on_tool_call(self, event: dict) -> None:
        """Вызов инструмента."""
        tool = event.get('tool', '')
        arguments = event.get('arguments', {})
        
        args_str = ', '.join(f"{k}={v}" for k, v in arguments.items()) if arguments else 'без параметров'
        message = f"🔧 Вызов инструмента **{tool}**\n\nПараметры: {args_str}"
        self.chat_panel.add_message("tool", message)

    def on_tool_result(self, event: dict) -> None:
        """Результат инструмента."""
        tool = event.get('tool', '')
        success = event.get('success', False)
        self.status_label.configure(text=f"{'✅' if success else '❌'} {tool}")

    def on_agent_done(self, event: dict) -> None:
        """Агент завершил задачу."""
        data = event.get('report', {})
        success = event.get('success', False)
        
        summary = data.get('summary', 'Задача выполнена')
        files_created = data.get('files_created', [])
        files_modified = data.get('files_modified', [])
        errors = data.get('errors', [])
        tool_calls = data.get('tool_calls', [])
        
        message_parts = [f"✅ Задача выполнена" if success else f"⚠️ Задача выполнена с ошибками"]
        
        if tool_calls:
            tools_used = [tc.get('tool_name', '') for tc in tool_calls if isinstance(tc, dict)]
            if tools_used:
                message_parts.append(f"\n\n🔧 Использованы инструменты: {', '.join(tools_used)}")
        
        if files_created:
            files_list = ', '.join(files_created)
            message_parts.append(f"\n📁 Создано файлов: {files_list}")
            
        if files_modified:
            files_list = ', '.join(files_modified)
            message_parts.append(f"\n✏️ Изменено файлов: {files_list}")
            
        if errors:
            errors_list = '\n'.join(f"  • {e}" for e in errors)
            message_parts.append(f"\n⚠️ Ошибки:\n{errors_list}")
        
        full_message = ''.join(message_parts)
        self.chat_panel.add_message("assistant" if success else "error", full_message, collapsible=True)

    def on_final(self, event: dict) -> None:
        """Завершение задачи."""
        result = event.get('result', '')
        self.chat_panel.add_message("assistant", f"🎉 Готово: {result}")
        self.status_label.configure(text="✅ Готов")

    def on_error(self, event: dict) -> None:
        """Ошибка."""
        message = event.get('message', 'Неизвестная ошибка')
        self.chat_panel.add_message("error", f"❌ Ошибка: {message}")
        self.status_label.configure(text=f"❌ Ошибка: {message}")

    # =============================================================================
    # КОМАНДЫ МЕНЮ
    # =============================================================================

    def _new_project(self) -> None:
        """Создание нового проекта с уникальным именем."""
        dialog = ctk.CTkInputDialog(
            text="Введите ID проекта (или оставьте пустым для автогенерации):",
            title="Новый проект"
        )
        project_id = dialog.get_input()
        
        if not project_id or not project_id.strip():
            project_id = f"project_{uuid.uuid4().hex[:8]}"
        else:
            project_id = project_id.strip()
        
        if project_id:
            self.chat_panel.clear_history()
            self._initialize_project(project_id)

    def _open_project(self) -> None:
        """Открытие существующего проекта."""
        projects_root = Path(self.settings.get("project_root", "./projects"))
        
        if not projects_root.exists():
            projects_root.mkdir(parents=True, exist_ok=True)
            
        existing_projects = []
        for project_dir in projects_root.iterdir():
            if project_dir.is_dir():
                state_file = project_dir / "state.json"
                if state_file.exists():
                    try:
                        with open(state_file, "r", encoding="utf-8") as f:
                            state_data = json.load(f)
                        created_at = state_data.get("created_at", "Неизвестно")[:10]
                        stage = state_data.get("stage", "unknown")
                        existing_projects.append({
                            "id": project_dir.name,
                            "created": created_at,
                            "stage": stage
                        })
                    except Exception:
                        existing_projects.append({
                            "id": project_dir.name,
                            "created": "Неизвестно",
                            "stage": "unknown"
                        })
        
        if not existing_projects:
            ctk.messagebox.showwarning("Проекты", "Нет существующих проектов")
            return
        
        # Диалог выбора проекта
        dialog = ctk.CTkToplevel(self)
        dialog.title("Открыть проект")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Выберите проект:", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        listbox_frame = ctk.CTkScrollableFrame(dialog, height=250)
        listbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        selected_project = {"id": None}
        
        def select_project(proj_id):
            selected_project["id"] = proj_id
            dialog.destroy()
        
        for proj in existing_projects:
            stage_icons = {
                "idle": "⚪",
                "planning": "🟡",
                "executing": "🔵",
                "waiting_user": "🟠",
                "review": "🟣",
                "done": "🟢",
                "error": "🔴",
            }
            icon = stage_icons.get(proj["stage"], "⚪")
            
            btn = ctk.CTkButton(
                listbox_frame, 
                text=f"{icon} {proj['id']} ({proj['created']})",
                command=lambda pid=proj["id"]: select_project(pid),
                anchor="w"
            )
            btn.pack(fill="x", pady=2)
        
        ctk.CTkButton(dialog, text="Отмена", command=dialog.destroy).pack(pady=10)
        
        self.wait_window(dialog)
        
        if selected_project["id"]:
            self.chat_panel.clear_history()
            self._initialize_project(selected_project["id"])

    def _rename_project(self) -> None:
        """Переименование текущего проекта."""
        if not self.current_project_id:
            ctk.messagebox.showwarning("Предупреждение", "Нет активного проекта")
            return
        
        dialog = ctk.CTkInputDialog(
            text=f"Новое имя для проекта '{self.current_project_id}':",
            title="Переименовать проект"
        )
        new_name = dialog.get_input()
        
        if new_name and new_name.strip():
            new_name = new_name.strip()
            old_path = self.current_project_path
            new_path = old_path.parent / new_name
            
            if new_path.exists():
                ctk.messagebox.showerror("Ошибка", f"Проект с именем '{new_name}' уже существует")
                return
            
            try:
                old_path.rename(new_path)
                self.current_project_id = new_name
                self.current_project_path = new_path
                self.status_label.configure(text=f"Проект: {new_name}")
                ctk.messagebox.showinfo("Успех", f"Проект переименован в '{new_name}'")
            except Exception as e:
                ctk.messagebox.showerror("Ошибка", f"Не удалось переименовать: {e}")

    def _export_project(self) -> None:
        """Экспорт проекта в ZIP."""
        if self.current_project_path:
            import shutil
            from tkinter import filedialog
            
            zip_path = filedialog.asksaveasfilename(
                defaultextension=".zip",
                initialfile=f"{self.current_project_id}.zip"
            )
            if zip_path:
                try:
                    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', self.current_project_path)
                    ctk.messagebox.showinfo("Успех", f"Проект экспортирован в {zip_path}")
                except Exception as e:
                    ctk.messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")
        else:
            ctk.messagebox.showwarning("Предупреждение", "Нет активного проекта для экспорта")

    def _show_settings(self) -> None:
        """Показ настроек."""
        settings_dialog = SettingsDialog(self, self.settings, self._save_settings_callback)
        settings_dialog.transient(self)
        settings_dialog.grab_set()

    def _save_settings_callback(self, new_settings: dict):
        """Callback для сохранения настроек."""
        self.settings = new_settings
        
        # Сохранение в файл
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(settings_path, "w", encoding="utf-8") as f:
            yaml.dump(new_settings, f, default_flow_style=False, allow_unicode=True)
        
        ctk.messagebox.showinfo("Успех", "Настройки сохранены")
        
        # Обновление моделей в конфиг панели
        self.config_panel.refresh_models()

    # =============================================================================
    # ИНИЦИАЛИЗАЦИЯ ПРОЕКТА
    # =============================================================================

    def _initialize_project(self, project_id: str) -> None:
        """Инициализация проекта."""
        logger.info(f"Инициализация проекта: {project_id}")

        self.current_project_id = project_id
        projects_root = Path(self.settings.get("project_root", "./projects"))
        self.current_project_path = projects_root / project_id

        if not self.client:
            logger.info("Инициализация LM Studio клиента")
            lmstudio_config = self.settings.get("lmstudio", {})
            self.client = LMStudioClient(
                base_url=lmstudio_config.get("base_url", "http://localhost:1234"),
                api_key=lmstudio_config.get("api_key", "lm-studio"),
            )
            self.model_registry = ModelRegistry(self.client)
            self.tool_registry = ToolRegistry()
            logger.info("Загрузка всех инструментов")
            self.tool_registry.load_all()

            async def check_lmstudio_and_load_models():
                try:
                    logger.info("Проверка подключения к LM Studio...")
                    models = await self.client.list_models()
                    if models:
                        logger.info(f"LM Studio подключено, найдено {len(models)} моделей")
                        self.connection_label.configure(text="🟢 Подключено", text_color="green")
                        await self.model_registry.load()
                        self.config_panel.refresh_models()
                        
                        # Обновление combobox моделей
                        model_ids = [m.id for m in models]
                        self.config_panel.set_model_options(model_ids)
                    else:
                        logger.warning("LM Studio подключено, но модели не найдены")
                        self.connection_label.configure(text="🟡 Нет моделей", text_color="orange")
                except Exception as e:
                    logger.error(f"Ошибка подключения к LM Studio: {e}")
                    self.connection_label.configure(text="🔴 Ошибка", text_color="red")

            self.async_bridge.run_coroutine(check_lmstudio_and_load_models())

        logger.info(f"Создание Conductor для проекта {project_id}")
        self.conductor = Conductor(
            client=self.client,
            model_registry=self.model_registry,
            tool_registry=self.tool_registry,
            project_id=project_id,
            project_root=projects_root,
        )

        self.memory_manager = MemoryManager(self.current_project_path)

        self._register_tool_handlers()

        async def init():
            await self.conductor.initialize()

        future = self.async_bridge.run_coroutine(init())

        self.status_label.configure(text=f"Проект: {project_id}")
        self.project_panel.refresh()

    def _register_tool_handlers(self) -> None:
        """Регистрация handlers инструментов."""
        from src.agents.tools.file_ops import register_file_handlers
        from src.agents.tools.system_ops import register_system_handlers
        from src.agents.tools.network_ops import register_network_handlers
        from src.agents.tools.memory_ops import register_memory_handlers

        register_file_handlers(self.tool_registry, self.current_project_path)
        register_system_handlers(self.tool_registry, self.current_project_path)
        register_network_handlers(self.tool_registry, self.current_project_path)
        register_memory_handlers(self.tool_registry, self.memory_manager)

    def send_message(self, message: str) -> None:
        """Отправка сообщения пользователем."""
        logger.info(f"Отправка сообщения пользователем: {message[:50]}...")

        self.chat_panel.add_message("user", message)

        async def process():
            logger.debug(f"Начало обработки запроса Conductor")
            async for event in self.conductor.process_request(message):
                logger.debug(f"Получено событие от Conductor: {event.get('type')}")
                self.async_bridge.gui_queue.put(event)

        future = self.async_bridge.run_coroutine(process())

    def _load_chat_history(self, project_id: str) -> None:
        """Загрузка истории чата из лога проекта."""
        log_file = self.current_project_path / "logs" / "chat_history.log"

        if not log_file.exists():
            logger.debug(f"История чата не найдена для проекта {project_id}")
            return

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("["):
                        try:
                            bracket_end = line.index("]")
                            rest = line[bracket_end+1:].strip()

                            if ": " in rest:
                                role_part, content = rest.split(": ", 1)
                                role_map = {
                                    "USER": "user",
                                    "ASSISTANT": "assistant",
                                    "SYSTEM": "system",
                                    "ERROR": "error",
                                }
                                role = role_map.get(role_part.upper(), "system")
                                self.chat_panel.add_message(role, content)
                        except (ValueError, IndexError):
                            continue

            logger.info(f"Загружена история чата для проекта {project_id}")
        except Exception as e:
            logger.error(f"Ошибка загрузки истории чата: {e}")


# Import panels
from gui_new.project_panel import ProjectPanel
from gui_new.chat_panel import ChatPanel
from gui_new.config_panel import ConfigPanel


def main():
    """Точка входа приложения."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
