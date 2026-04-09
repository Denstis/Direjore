# 🎭 Conductor - Multi-Agent Development System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform: Windows/Linux/macOS](https://img.shields.io/badge/platform-Windows%2FLinux%2FmacOS-green.svg)](conductor_app/README.md)
[![LM Studio Compatible](https://img.shields.io/badge/LM_Studio-Compatible-orange.svg)](https://lmstudio.ai/)

**English** | [Русский](#русский)

## 📖 Overview

**Conductor** is a multi-agent development system that orchestrates AI agents to complete complex software development tasks. It uses local LLM models (via [LM Studio](https://lmstudio.ai)) to power specialized agent roles including Director, Coder, and Researcher.

### ✨ Key Features

- 🎭 **Role-Based Agents**: Specialized agents with distinct responsibilities and toolsets
- 🔧 **19 Built-in Tools**: File operations, system commands, Git, pip, web search, browser automation
- 🧠 **Scoped Memory**: Project, user, and role-specific memory isolation
- 🛡️ **Safety First**: Path isolation, command filtering, timeout protection
- 💻 **Cross-Platform**: Automatic OS detection and adaptation (Windows/Linux/macOS)
- 🖥️ **GUI Interface**: Real-time progress tracking with Tkinter
- 📝 **Strict JSON Protocol**: Pydantic validation for reliable LLM communication

## 🚀 Quick Start

### Prerequisites

1. **Install Python 3.10+** from [python.org](https://www.python.org)
   - ✅ Check "Add Python to PATH" during installation

2. **Install LM Studio** from [lmstudio.ai](https://lmstudio.ai)
   - Download and install a model (recommended: `Qwen2.5-7B-Instruct` or similar)
   - Start the server on `localhost:1234` with tool calling support enabled

### Installation & Launch

```bash
cd conductor_app
# On Windows
Run.bat

# On Linux/macOS
chmod +x Run.sh && ./Run.sh
```

The launcher will automatically:
- Create a virtual environment (if needed)
- Install all dependencies
- Launch the GUI application

### Updating from Git

```bash
cd conductor_app
# On Windows
Update.bat

# On Linux/macOS
git pull && pip install -r requirements.txt
```

## 🎭 Available Roles

| Role | Icon | Description |
|------|------|-------------|
| **Director** | 🎭 | Main orchestrator. Analyzes requests, creates plans, delegates tasks, monitors progress |
| **Coder** | 💻 | Writes, modifies, and refactors code. Manages project files |
| **Researcher** | 🔍 | Searches information, analyzes documentation, gathers requirements |

## 🛠️ Available Tools (19 total)

### File Operations (6)
`read_file`, `write_file`, `edit_file`, `list_files`, `search_code`, `delete_file`

### System Operations (4)
`run_command`, `pip_install`, `git_clone`, `git_command`

### Network Operations (3)
`fetch_url`, `search_web`, `browser_snapshot`

### Memory Operations (6)
`read_project_memory`, `write_project_memory`, `delete_project_memory`, `read_user_memory`, `read_role_memory`, `write_role_memory`

## 🏗️ Architecture

```
conductor_app/
├── main.py                    # Entry point (asyncio + Tkinter bridge)
├── Run.bat / Run.sh           # Platform launchers
├── config/
│   ├── roles/                 # Role definitions (YAML)
│   └── tools/                 # Tool schemas (JSON)
├── src/
│   ├── core/                  # LM client, registries, platform utils
│   ├── director/              # Orchestrator logic
│   ├── agents/                # Agent workers and tools
│   └── memory/                # Scoped memory management
├── gui/                       # Tkinter interface
└── projects/                  # Dynamic project storage
```

## 🛡️ Safety Features

- **Path Isolation**: Agents can only access `projects/{id}/workspace/`
- **Command Filtering**: Dangerous commands blocked (`sudo`, `rm -rf`, etc.)
- **Timeout Protection**: All commands have 30s default timeout
- **JSON Validation**: All LLM responses validated via Pydantic
- **Atomic Writes**: State saved atomically to prevent corruption

## 📊 Platform Support

| Platform | Status |
|----------|--------|
| **Windows** | ✅ Full support (cmd.exe) |
| **Linux** | ✅ Full support (bash) |
| **macOS** | ✅ Full support (bash/zsh) |

## 📦 Requirements

- Python 3.10+
- LM Studio with a loaded model
- Git (for version control tools)

## 📄 Documentation

- [Full README](conductor_app/README.md) - Detailed documentation
- [Technical Plan](conductor_app/TECHNICAL_PLAN.md) - Architecture and implementation details
- [Project State](PROJECT_STATE.md) - Current development status

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [LM Studio](https://lmstudio.ai) - Local LLM inference
- [Qwen Team](https://github.com/QwenLM) - Excellent open-source models
- [OpenAI](https://openai.com) - API compatibility standard

---

## 🇷🇺 Русский

**Дирижёр (Conductor)** — многоагентная система для координации AI-агентов при выполнении сложных задач разработки ПО.

### Быстрый старт
1. Установите Python 3.10+ и LM Studio
2. Загрузите модель (рекомендуется `Qwen2.5-7B-Instruct`)
3. Запустите сервер на `localhost:1234`
4. Выполните `Run.bat` (Windows) или `Run.sh` (Linux/macOS)

### Роли
- **Дирижёр** 🎭 - Планирует и делегирует задачи
- **Кодер** 💻 - Пишет и изменяет код
- **Исследователь** 🔍 - Ищет информацию

### Безопасность
- Изоляция путей к файлам
- Фильтрация опасных команд
- Валидация всех JSON-ответов

---

*Built with ❤️ for local AI development*
