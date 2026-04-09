"""
Project Panel — отображение структуры проекта, стадии, прогресса.
"""

import json
import tkinter as tk
from pathlib import Path
from typing import Optional

from tkinter import ttk


class ProjectPanel:
    """Панель проекта с деревом файлов и индикаторами."""

    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent)
        
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Создание виджетов панели."""
        # Заголовок
        header_frame = ttk.Frame(self.frame)
        header_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(
            header_frame,
            text="📁 ПРОЕКТ",
            font=("Segoe UI", 12, "bold"),
        ).pack(side=tk.LEFT)
        
        # Стадия
        stage_frame = ttk.LabelFrame(self.frame, text="Стадия", padding=5)
        stage_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stage_label = ttk.Label(
            stage_frame,
            text="⚪ Не выбран",
            font=("Segoe UI", 10),
        )
        self.stage_label.pack(anchor=tk.W)
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(
            stage_frame,
            mode="determinate",
        )
        self.progress.pack(fill=tk.X, pady=(5, 0))
        
        self.progress_label = ttk.Label(
            stage_frame,
            text="0/0 шагов",
            font=("Segoe UI", 8),
        )
        self.progress_label.pack(anchor=tk.E)
        
        # Дерево файлов
        tree_frame = ttk.LabelFrame(self.frame, text="workspace/", padding=5)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview с scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=tree_scroll.set,
            selectmode="browse",
        )
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)
        
        # Кнопки действий
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(
            btn_frame,
            text="🔄 Обновить",
            command=self.refresh,
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            btn_frame,
            text="📤 Экспорт",
            command=self._export_project,
        ).pack(side=tk.LEFT, padx=2)

    def update_stage(self, stage: str) -> None:
        """Обновление индикатора стадии."""
        stage_icons = {
            "idle": "⚪",
            "planning": "🟡",
            "executing": "🔵",
            "waiting_user": "🟠",
            "review": "🟣",
            "done": "🟢",
            "error": "🔴",
        }
        
        stage_names = {
            "idle": "Ожидание",
            "planning": "Планирование",
            "executing": "Выполнение",
            "waiting_user": "Ожидание пользователя",
            "review": "Проверка",
            "done": "Завершено",
            "error": "Ошибка",
        }
        
        icon = stage_icons.get(stage, "⚪")
        name = stage_names.get(stage, stage)
        
        self.stage_label.config(text=f"{icon} {name}")

    def update_progress(self, current: int, total: int) -> None:
        """Обновление прогресс-бара."""
        if total > 0:
            value = (current / total) * 100
        else:
            value = 0
            
        self.progress.configure(value=value)
        self.progress_label.config(text=f"{current}/{total} шагов")

    def refresh(self) -> None:
        """Обновление дерева файлов."""
        # Очистка дерева
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        if not self.app.current_project_path:
            return
            
        workspace_path = self.app.current_project_path / "workspace"
        if not workspace_path.exists():
            return
            
        # Построение дерева
        self._build_tree(workspace_path, "")

    def _build_tree(self, path: Path, parent_id: str) -> None:
        """Рекурсивное построение дерева."""
        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
            
            for item in items:
                icon = "📁" if item.is_dir() else "📄"
                item_id = self.tree.insert(
                    parent_id,
                    "end",
                    text=f"{icon} {item.name}",
                    values=[str(item)],
                )
                
                if item.is_dir():
                    self._build_tree(item, item_id)
                    
        except Exception as e:
            pass

    def _export_project(self) -> None:
        """Экспорт проекта в ZIP."""
        # TODO: Реализация экспорта
        pass

    def load_state(self) -> None:
        """Загрузка состояния из state.json."""
        if not self.app.current_project_path:
            return
            
        state_file = self.app.current_project_path / "state.json"
        if not state_file.exists():
            return
            
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                
            stage = state.get("stage", "idle")
            self.update_stage(stage)
            
            plan = state.get("current_plan")
            if plan:
                steps = plan.get("total_steps", 0)
                current_step = state.get("current_step", 0)
                self.update_progress(current_step, steps)
                
        except Exception as e:
            pass
