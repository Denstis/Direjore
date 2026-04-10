"""
Главное окно приложения: bridge asyncio ↔ Tkinter.

Использует queue.Queue + root.after() для безопасной доставки событий.
"""

import asyncio
import json
import logging
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any, Callable, Optional

import yaml

from src.core.lm_client import LMStudioClient
from src.core.model_registry import ModelRegistry
from src.core.tool_registry import ToolRegistry
from src.director.conductor import Conductor
from src.memory.manager import MemoryManager

# Import GUI panels
from gui.panels.project_panel import ProjectPanel
from gui.panels.chat_panel import ChatPanel
from gui.panels.config_panel import ConfigPanel
from gui.widgets.status_bar import StatusBar

logger = logging.getLogger(__name__)


class AsyncBridge:
    """Мост между asyncio и Tkinter."""

    def __init__(self, root: tk.Tk):
        self.root = root
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
        """Опрос очереди GUI (вызывается через root.after)."""
        try:
            while True:
                event = self.gui_queue.get_nowait()
                self._handle_event(event)
        except queue.Empty:
            pass
            
        # Продолжение опроса
        self.root.after(50, self.poll_gui_queue)

    def _handle_event(self, event: dict) -> None:
        """Обработка события из очереди."""
        event_type = event.get("type")
        
        logger.debug(f"Обработка события GUI: {event_type}, данные: {event}")

        if event_type == "stage_changed":
            self.root.event_generate("<<StageChanged>>", data=event)
        elif event_type == "ask_user":
            logger.info(f"Событие ask_user получено: question={event.get('question', 'N/A')[:50] if event.get('question') else 'пустой'}")
            self.root.event_generate("<<AskUser>>", data=event)
        elif event_type == "delegated":
            self.root.event_generate("<<Delegated>>", data=event)
        elif event_type == "tool_call":
            self.root.event_generate("<<ToolCall>>", data=event)
        elif event_type == "tool_result":
            self.root.event_generate("<<ToolResult>>", data=event)
        elif event_type == "agent_done":
            self.root.event_generate("<<AgentDone>>", data=event)
        elif event_type == "final":
            self.root.event_generate("<<Final>>", data=event)
        elif event_type == "error":
            self.root.event_generate("<<Error>>", data=event)


class MainWindow(tk.Tk):
    """Главное окно приложения."""

    def __init__(self):
        super().__init__()
        
        self.title("🎭 Дирижёр — Multi-Agent System")
        self.geometry("1400x900")
        
        # Настройка стилей (не применяется к Menu в ttkbootstrap)
        # self.option_add("*Font", "Segoe UI 10")
        
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
        self._create_bindings()
        
        # Старт asyncio
        self.async_bridge.start_asyncio()
        self.async_bridge.poll_gui_queue()

    def _load_settings(self) -> dict:
        """Загрузка настроек из config/settings.yaml."""
        settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
        
        if not settings_path.exists():
            return {}
            
        with open(settings_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _create_menu(self) -> None:
        """Создание меню."""
        menubar = tk.Menu(self)
        
        # Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Новый проект", command=self._new_project)
        file_menu.add_command(label="Открыть проект", command=self._open_project)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт проекта", command=self._export_project)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit)
        menubar.add_cascade(label="Файл", menu=file_menu)
        
        # Вид
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Обновить", command=self._refresh_view)
        menubar.add_cascade(label="Вид", menu=view_menu)
        
        # Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Настройки", command=self._show_settings)
        menubar.add_cascade(label="Инструменты", menu=tools_menu)
        
        # Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self._about)
        menubar.add_cascade(label="Справка", menu=help_menu)
        
        self.config(menu=menubar)

    def _create_layout(self) -> None:
        """Создание основной раскладки."""
        # Главный PanedWindow
        main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель: Проект
        self.project_panel = ProjectPanel(main_paned, self)
        main_paned.add(self.project_panel.frame, width=300)
        
        # Центральная панель: Чат
        self.chat_panel = ChatPanel(main_paned, self)
        main_paned.add(self.chat_panel.frame, width=700)
        
        # Правая панель: Конфиг
        self.config_panel = ConfigPanel(main_paned, self)
        main_paned.add(self.config_panel.frame, width=400)
        
        # Status bar
        self.status_bar = StatusBar(self)
        self.status_bar.frame.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_bindings(self) -> None:
        """Привязка событий."""
        self.bind("<<StageChanged>>", self._on_stage_changed)
        self.bind("<<AskUser>>", self._on_ask_user)
        self.bind("<<Delegated>>", self._on_delegated)
        self.bind("<<ToolCall>>", self._on_tool_call)
        self.bind("<<ToolResult>>", self._on_tool_result)
        self.bind("<<AgentDone>>", self._on_agent_done)
        self.bind("<<Final>>", self._on_final)
        self.bind("<<Error>>", self._on_error)

    # =============================================================================
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # =============================================================================

    def _on_stage_changed(self, event) -> None:
        """Изменение стадии проекта."""
        data = getattr(event, 'data', {})
        stage = data.get('stage', 'unknown')
        self.project_panel.update_stage(stage)
        self.status_bar.set_status(f"Стадия: {stage}")

    def _on_ask_user(self, event) -> None:
        """Запрос уточнения у пользователя."""
        try:
            # Попытка получить данные из атрибута data
            data = getattr(event, 'data', {})
            if not data:
                # Альтернативная попытка получить данные
                data = {}
            question = data.get('question', '')
            options = data.get('options', [])
            
            logger.info(f"Получен вопрос от пользователя: {question[:50] if question else 'пустой'}...")
            logger.debug(f"Опции: {options}")
            
            self.chat_panel.show_question(question, options)
        except Exception as e:
            logger.error(f"Ошибка при обработке вопроса пользователю: {e}", exc_info=True)
            self.chat_panel.add_message("error", f"❌ Ошибка обработки вопроса: {e}")

    def _on_delegated(self, event) -> None:
        """Делегирование задачи."""
        data = getattr(event, 'data', {})
        role = data.get('role', '')
        task = data.get('task', '')
        
        # Формируем понятное сообщение
        message = f"🤖 Делегировано роли **{role}**\n\n📋 Задача: {task}"
        self.chat_panel.add_message("system", message)

    def _on_tool_call(self, event) -> None:
        """Вызов инструмента."""
        data = getattr(event, 'data', {})
        tool = data.get('tool', '')
        arguments = data.get('arguments', {})
        
        # Формируем читаемое сообщение
        args_str = ', '.join(f"{k}={v}" for k, v in arguments.items()) if arguments else 'без параметров'
        message = f"🔧 Вызов инструмента **{tool}**\n\nПараметры: {args_str}"
        self.chat_panel.add_message("tool", message)

    def _on_tool_result(self, event) -> None:
        """Результат инструмента."""
        data = getattr(event, 'data', {})
        tool = data.get('tool', '')
        success = data.get('success', False)
        self.status_bar.set_status(f"{'✅' if success else '❌'} {tool}")

    def _on_agent_done(self, event) -> None:
        """Агент завершил задачу."""
        data = getattr(event, 'data', {})
        success = data.get('success', False)
        report = data.get('report', {})
        
        # Формируем подробное сообщение для пользователя
        summary = report.get('summary', 'Задача выполнена')
        files_created = report.get('files_created', [])
        files_modified = report.get('files_modified', [])
        errors = report.get('errors', [])
        
        # Строим подробный текст
        message_parts = [summary]
        
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
        self.chat_panel.add_message("assistant" if success else "error", full_message)

    def _on_final(self, event) -> None:
        """Завершение задачи."""
        data = getattr(event, 'data', {})
        result = data.get('result', '')
        self.chat_panel.add_message("assistant", f"🎉 Готово: {result}")
        self.status_bar.set_status("✅ Готов")

    def _on_error(self, event) -> None:
        """Ошибка."""
        data = getattr(event, 'data', {})
        message = data.get('message', 'Неизвестная ошибка')
        self.chat_panel.add_message("error", f"❌ Ошибка: {message}")
        self.status_bar.set_status(f"❌ Ошибка: {message}")

    # =============================================================================
    # КОМАНДЫ МЕНЮ
    # =============================================================================

    def _new_project(self) -> None:
        """Создание нового проекта."""
        # Диалог создания проекта
        dialog = tk.Toplevel(self)
        dialog.title("Новый проект")
        dialog.geometry("400x200")
        
        tk.Label(dialog, text="ID проекта:").pack(pady=10)
        entry = tk.Entry(dialog, width=40)
        entry.pack()
        
        def create():
            project_id = entry.get().strip()
            if project_id:
                # Сброс чата перед инициализацией нового проекта
                self.chat_panel.clear_history()
                self._initialize_project(project_id)
                dialog.destroy()
                
        tk.Button(dialog, text="Создать", command=create).pack(pady=10)

    def _open_project(self) -> None:
        """Открытие существующего проекта."""
        # Получение списка проектов из директории projects
        projects_root = Path(self.settings.get("project_root", "./projects"))
        
        if not projects_root.exists():
            messagebox.showwarning("Проекты", "Директория проектов не найдена")
            return
            
        # Поиск существующих проектов (папки с state.json)
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
            messagebox.showinfo("Проекты", "Нет существующих проектов")
            return
        
        # Диалог выбора проекта
        dialog = tk.Toplevel(self)
        dialog.title("Открыть проект")
        dialog.geometry("500x300")
        
        tk.Label(dialog, text="Выберите проект:", font=("Segoe UI", 11, "bold")).pack(pady=10)
        
        # Список проектов
        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        listbox = tk.Listbox(listbox_frame, height=10, font=("Consolas", 10))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        # Заполнение списка
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
            listbox.insert(tk.END, f"{icon} {proj['id']} ({proj['created']})")
        
        def open_selected():
            selection = listbox.curselection()
            if selection:
                idx = selection[0]
                project_id = existing_projects[idx]["id"]
                # Сброс чата перед открытием проекта
                self.chat_panel.clear_history()
                self._initialize_project(project_id)
                # Загрузка истории чата из лога проекта если существует
                self._load_chat_history(project_id)
                dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Открыть", command=open_selected).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        # Двойной клик для открытия
        listbox.bind("<Double-Button-1>", lambda e: open_selected())

    def _export_project(self) -> None:
        """Экспорт проекта в ZIP."""
        # TODO: Экспорт
        pass

    def _refresh_view(self) -> None:
        """Обновление вида."""
        if self.current_project_id:
            self.project_panel.refresh()

    def _show_settings(self) -> None:
        """Показ настроек."""
        self.config_panel.show_settings_tab()

    def _about(self) -> None:
        """О программе."""
        tk.messagebox.showinfo(
            "О программе",
            "🎭 Дирижёр\nMulti-Agent System\n\nВерсия 0.1.0"
        )

    # =============================================================================
    # ИНИЦИАЛИЗАЦИЯ ПРОЕКТА
    # =============================================================================

    def _initialize_project(self, project_id: str) -> None:
        """Инициализация проекта."""
        logger.info(f"Инициализация проекта: {project_id}")
        
        self.current_project_id = project_id
        projects_root = Path(self.settings.get("project_root", "./projects"))
        self.current_project_path = projects_root / project_id
        
        # Инициализация компонентов если ещё не созданы
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
            
            # Проверка подключения к LM Studio и загрузка моделей
            async def check_lmstudio_and_load_models():
                try:
                    logger.info("Проверка подключения к LM Studio...")
                    models = await self.client.list_models()
                    if models:
                        logger.info(f"LM Studio подключено, найдено {len(models)} моделей")
                        self.status_bar.set_connection_status(True, lmstudio_config.get("base_url", "http://localhost:1234"))
                        # Загрузка моделей в реестр
                        await self.model_registry.load()
                        # Обновление списка моделей в UI
                        self.config_panel._refresh_models()
                    else:
                        logger.warning("LM Studio подключено, но модели не найдены")
                        self.status_bar.set_connection_status(False)
                except Exception as e:
                    logger.error(f"Ошибка подключения к LM Studio: {e}")
                    self.status_bar.set_connection_status(False)
            
            self.async_bridge.run_coroutine(check_lmstudio_and_load_models())
            
        # Создание Conductor
        logger.info(f"Создание Conductor для проекта {project_id}")
        self.conductor = Conductor(
            client=self.client,
            model_registry=self.model_registry,
            tool_registry=self.tool_registry,
            project_id=project_id,
            project_root=projects_root,
        )
        
        # Memory manager
        self.memory_manager = MemoryManager(self.current_project_path)
        
        # Регистрация хендлеров инструментов (после создания memory_manager)
        self._register_tool_handlers()
        
        # Инициализация Conductor
        async def init():
            await self.conductor.initialize()
            
        future = self.async_bridge.run_coroutine(init())
        future.add_done_callback(lambda f: self.project_panel.refresh())
        
        self.status_bar.set_status(f"Проект: {project_id}")

    def _register_tool_handlers(self) -> None:
        """Регистрация handlers инструментов."""
        from src.agents.tools.file_ops import register_file_handlers
        from src.agents.tools.memory_ops import register_memory_handlers
        
        register_file_handlers(self.tool_registry, self.current_project_path)
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
                    
                    # Парсинг строки лога: [timestamp] role: content
                    if line.startswith("["):
                        # Извлечение роли и контента
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
