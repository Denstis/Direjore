"""
ProjectPanel — панель проекта на CustomTkinter.

Отображение стадии, информации о проекте, дерево файлов.
"""

import json
import logging
from pathlib import Path
from typing import Optional

import customtkinter as ctk

logger = logging.getLogger(__name__)


class ProjectPanel(ctk.CTkScrollableFrame):
    """Панель проекта."""

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main_window = main_window
        
        self._create_widgets()

    def _create_widgets(self):
        """Создание виджетов."""
        # Заголовок
        header_label = ctk.CTkLabel(
            self, 
            text="📁 ПРОЕКТ", 
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header_label.pack(pady=10)
        
        # Информация о проекте
        info_frame = ctk.CTkFrame(self)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(info_frame, text="ID проекта:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.project_id_label = ctk.CTkLabel(info_frame, text="-")
        self.project_id_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(info_frame, text="Стадия:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.stage_label = ctk.CTkLabel(info_frame, text="⚪ idle", text_color="gray")
        self.stage_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(info_frame, text="Путь:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.path_label = ctk.CTkLabel(info_frame, text="-", wraplength=200)
        self.path_label.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Стадии (визуальные индикаторы)
        stages_frame = ctk.CTkFrame(self)
        stages_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(stages_frame, text="Стадии проекта:", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.stage_indicators = {}
        stage_names = [
            ("idle", "⚪"),
            ("planning", "🟡"),
            ("executing", "🔵"),
            ("waiting_user", "🟠"),
            ("review", "🟣"),
            ("done", "🟢"),
            ("error", "🔴"),
        ]
        
        for stage_name, icon in stage_names:
            frame = ctk.CTkFrame(stages_frame, fg_color="transparent")
            frame.pack(fill="x", pady=2)
            
            indicator = ctk.CTkLabel(frame, text=f"{icon} {stage_name}", text_color="gray" if stage_name != "idle" else "white")
            indicator.pack(side="left")
            self.stage_indicators[stage_name] = indicator
        
        # Дерево файлов
        files_frame = ctk.CTkFrame(self)
        files_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(files_frame, text="📂 Файлы проекта:", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.files_scroll = ctk.CTkScrollableFrame(files_frame, height=200)
        self.files_scroll.pack(fill="both", expand=True)
        
        # Кнопки действий
        actions_frame = ctk.CTkFrame(self)
        actions_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(actions_frame, text="🔄 Обновить", command=self.refresh, width=120).pack(side="left", padx=5)
        ctk.CTkButton(actions_frame, text="📤 Экспорт", command=self._export_project, width=120).pack(side="right", padx=5)

    def update_stage(self, stage: str) -> None:
        """Обновление стадии проекта."""
        stage_display = {
            "idle": "⚪ idle",
            "planning": "🟡 planning",
            "executing": "🔵 executing",
            "waiting_user": "🟠 waiting",
            "review": "🟣 review",
            "done": "🟢 done",
            "error": "🔴 error",
        }
        
        display_text = stage_display.get(stage, f"⚪ {stage}")
        self.stage_label.configure(text=display_text)
        
        # Обновление индикаторов
        for s, indicator in self.stage_indicators.items():
            if s == stage:
                indicator.configure(text_color="white")
            else:
                indicator.configure(text_color="gray")

    def refresh(self) -> None:
        """Обновление панели проекта."""
        if self.main_window.current_project_id:
            self.project_id_label.configure(text=self.main_window.current_project_id)
            self.path_label.configure(text=str(self.main_window.current_project_path))
            
            # Обновление дерева файлов
            self._refresh_files()
        else:
            self.project_id_label.configure(text="-")
            self.path_label.configure(text="-")

    def _refresh_files(self):
        """Обновление списка файлов проекта."""
        # Очистка
        for widget in self.files_scroll.winfo_children():
            widget.destroy()
        
        if not self.main_window.current_project_path:
            return
        
        # Сканирование файлов
        project_path = self.main_window.current_project_path
        
        if project_path.exists():
            for item in sorted(project_path.rglob("*")):
                if item.is_file() and not item.name.startswith("."):
                    try:
                        rel_path = item.relative_to(project_path)
                        rel_str = str(rel_path)
                        
                        # Пропуск логов и временных файлов
                        if "logs" in rel_str or ".tmp" in rel_str:
                            continue
                        
                        file_icon = "📄"
                        if item.suffix in [".py", ".js", ".ts"]:
                            file_icon = "🐍" if item.suffix == ".py" else "📜"
                        elif item.suffix in [".json", ".yaml", ".yml"]:
                            file_icon = "⚙️"
                        elif item.suffix in [".md", ".txt"]:
                            file_icon = "📝"
                        
                        file_label = ctk.CTkLabel(
                            self.files_scroll,
                            text=f"{file_icon} {rel_str}",
                            anchor="w",
                            wraplength=200
                        )
                        file_label.pack(fill="x", pady=1, padx=5)
                    except Exception as e:
                        logger.debug(f"Ошибка отображения файла {item}: {e}")

    def _export_project(self):
        """Экспорт проекта."""
        if self.main_window.current_project_path:
            self.main_window._export_project()
