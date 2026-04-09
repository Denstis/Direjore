# 📐 Conductor Technical Implementation Plan

> **Complete technical specification for AI agents and developers**. Contains architecture, component interaction, phased implementation plan, GUI specifications, and critical code quality requirements.

---

## 1. 📐 Project Structure

```
conductor_app/
├── main.py                          # Entry point, asyncio + Tkinter initialization
├── requirements.txt                 # openai, pydantic, requests, pyyaml, aiohttp, beautifulsoup4
├── config/
│   ├── settings.yaml               # Global settings (port, project_root, log_level)
│   ├── models.json                 # Model capabilities cache (context, tools, quant)
│   ├── roles/                      # YAML role templates
│   │   ├── director.yaml
│   │   ├── coder.yaml
│   │   └── researcher.yaml
│   └── tools/                      # JSON tool descriptions (schema only)
│       ├── file_ops.json
│       ├── system_ops.json
│       ├── network_ops.json
│       └── memory_ops.json
├── src/
│   ├── core/
│   │   ├── lm_client.py            # LM Studio wrapper (OpenAI + /api/v1/*)
│   │   ├── model_registry.py       # Load, filter, select model by role
│   │   ├── tool_registry.py        # Load schemas + map → handler
│   │   └── platform_utils.py       # Cross-platform utilities (OS detection, safe paths)
│   ├── director/
│   │   ├── conductor.py            # Main orchestrator (loop, plan, delegate)
│   │   ├── planner.py              # Generate/approve plan, decomposition
│   │   └── protocol.py             # Pydantic schemas for all LLM JSON responses
│   ├── agents/
│   │   ├── base.py                 # Base agent class (state, context, limits)
│   │   ├── worker.py               # Role execution loop + tool calling + callback
│   │   └── tools/
│   │       ├── file_ops.py         # File operation handlers
│   │       ├── system_ops.py       # System command handlers
│   │       ├── network_ops.py      # Network request handlers
│   │       └── memory_ops.py       # Memory operation handlers
│   └── memory/
│       ├── manager.py              # Unified API: project / user / role
│       └── storage.py              # File/JSON implementation (extensible to SQLite)
├── gui/
│   ├── app.py                      # Main window, bridge asyncio ↔ Tkinter
│   ├── panels/
│   │   ├── project_panel.py        # File tree, stage, progress
│   │   ├── chat_panel.py           # History, input, status
│   │   └── config_panel.py         # Tabs: Models, Roles, Tools, Memory
│   └── widgets/
│       ├── code_editor.py          # Text + context menu (cut/find/replace)
│       └── status_bar.py           # Tokens, model status, errors, progress
└── projects/                       # Dynamic project folders
    └── {project_id}/
        ├── state.json              # Current stage, plan, active role, steps
        ├── memory/                 # project.json, user.json, role_*.json
        ├── workspace/              # Files created by agents
        └── logs/                   # api_calls.log, errors.log
```

---

## 2. 🔗 Component Interaction Diagram

```
[User] → (GUI: Chat) → [Conductor]
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
[Analysis/Plan]        [Request Clarification]  [Approve Plan]
       │                      │                      │
       ▼                      ▼                      ▼
[Decomposition] ←──── [Wait for Input] ←──── [GUI: Confirmation]
       │
       ▼
[Select Role + Tools] → [Worker] → (tool calls) → [Tool Registry]
       │                            │
       ▼                            ▼
[Context: project+user mem]   [Execute → Result]
       │                            │
       ▼                            ▼
[Handoff JSON] ←────────────────── [Callback Director]
       │
       ▼
[Check Status] → success? → [Next Role] / error? → [Correction] / done → [Final]
       │
       ▼
[GUI: Update Stage/Progress/Logs] → [Save state.json]
```

**Key Protocols:**
1. `Director ↔ LLM`: Strict JSON via `Pydantic`. No free text for actions.
2. `Worker ↔ Tools`: Call only from allowed list. Validate arguments before execution.
3. `Memory`: Isolated by scope. `user` (read-only for agents), `project` (read/write director), `role` (temp).
4. `GUI ↔ Backend`: `asyncio.Queue` + `root.after()`. No blocking `time.sleep()` or direct API calls in main thread.

---

## 3. 📋 Phased Implementation Plan

### 🔹 Phase 1: Infrastructure and LM Studio
- [x] `src/core/lm_client.py`: Client with `tools`, `tool_choice` support, fallback to native `/api/v1/chat` for `context_length`.
- [x] `src/core/model_registry.py`: Auto-request model list, parse `context_window`, `tool_support`, manual overrides in `config/models.json`.
- [x] `src/core/tool_registry.py`: Load JSON schemas from `config/tools/`, map `name → async handler`, semantic search by `description`.
- [x] `src/core/platform_utils.py`: OS detection, safe path joining, shell selection.
- [ ] Test: `client.chat_completion(..., tools=...)` returns valid `tool_calls`.

### 🔹 Phase 2: Director and Protocols
- [x] `src/director/protocol.py`: Pydantic models: `DelegateAction`, `QueryToolsAction`, `FinalAction`, `AskUserAction`, `RoleReport`.
- [x] `src/director/conductor.py`: Analysis → plan → request approval → delegation loop. Iteration limits, state logging.
- [x] `src/director/planner.py`: Step generation (max 7), complexity estimation, formatting for user.
- [ ] Test: Director stably parses JSON, no infinite loops, correctly handles `ask_user`.

### 🔹 Phase 3: Worker Agents and Memory
- [x] `src/agents/worker.py`: Loop `chat → tool_calls → execute → append → retry/final`. Forced `report_to_director` callback.
- [x] `src/agents/tools/*`: 19 tool handlers across 4 categories.
- [x] `src/memory/manager.py`: `project_read/write`, `user_get/set`, `role_write`. Context export by keys.
- [x] `src/memory/storage.py`: Save to `projects/{id}/memory/`. Atomic write + backup.
- [ ] Test: Role executes 2+ tools, saves artifact, returns valid report.

### 🔹 Phase 4: GUI (Tkinter)
- [x] `gui/app.py`: Bridge `asyncio` ↔ `Tkinter` (via `queue` + `after`).
- [⚠️] `gui/panels/project_panel.py`: `ttk.Treeview`, stage indicator, progress bar, read `state.json`.
- [⚠️] `gui/panels/chat_panel.py`: History with color coding, `CodeEditorWithMenu`, async send.
- [⚠️] `gui/panels/config_panel.py`: Tabs: Models (list + checkboxes), Roles (YAML editor), Tools (JSON validator), Memory (viewer).
- [⚠️] `gui/widgets/code_editor.py`: Text + context menu (cut/copy/paste/find/replace).
- [⚠️] `gui/widgets/status_bar.py`: Tokens, model status, errors, progress.
- [ ] Test: GUI doesn't block, stage updates in real-time, context menu works.

### 🔹 Phase 5: Integration and Debugging
- [ ] End-to-end test: "Create project → request → plan → approval → 2 roles → final".
- [ ] Error handling: timeouts, invalid JSON from LLM, missing tool, user interrupt.
- [ ] Logging: `projects/{id}/logs/`, rotation, raw request/response recording for debugging.
- [ ] Documentation: `README.md`, `config/` examples, LM Studio setup guide.

---

## 4. 🖥️ Detailed GUI Plan

### 🧱 Window Layout (`1400x900`, resizable)
```
┌─────────────────────────────────────────────────────────────┐
│  🎭 Conductor  [File] [View] [Tools] [Help]                  │
├──────────────┬──────────────────────────────┬───────────────┤
│ 📁 PROJECT   │ 💬 AGENT DIALOG              │ ⚙️ CONFIG     │
│              │                              │               │
│ 📊 Stage:    │ [Message History]            │ [Tabs]        │
│ [🟡 Planning]│ 👤 You: Create a bot         │ 📦 Models     │
│ ███████░░░ 3/5│ 🤖 Agent: Approve plan...   │ 👥 Roles      │
│              │                              │ 🛠 Tools      │
│ 📂 workspace/│ [Input Field with Highlight] │ 🧠 Memory     │
│  ├─ main.py  │ ┌────────────────────────┐   │ 📜 Logs       │
│  └─ README.md│ │ [Text...]              │   │               │
│              │ │ [Context Menu on Right]│   │               │
│ [🔄 Refresh] │ └────────────────────────┘   │ [Apply]       │
│ [📤 Export]  │ [⏹ Stop] [➤ Send]           │               │
├──────────────┴──────────────────────────────┴───────────────┤
│ 📡 Status: LM Studio: qwen2.5-7b | Tokens: 1.2k/8k | ✅ Ready│
└─────────────────────────────────────────────────────────────┘
```

### 🧩 Components and Responsibilities
| Component | Technology | Key Functions |
|-----------|------------|---------------|
| `MainWindow` | `tk.Tk` + `ttk.PanedWindow` | Initialization, layout, async bridge, menu |
| `ProjectPanel` | `ttk.Treeview`, `ttk.Progressbar` | Structure display, read `state.json`, ZIP export |
| `ChatPanel` | `ScrolledText` + `CodeEditorWithMenu` | History, role color coding, input, context menu |
| `ConfigPanel` | `ttk.Notebook` | YAML/JSON editor, schema validation, model switching, memory viewer |
| `StatusBar` | `ttk.Label` | Model, context usage, status, errors |
| `AsyncBridge` | `queue.Queue` + `root.after(50, poll)` | Safe delivery of agent responses to GUI without blocking |

### 🔄 GUI Lifecycle
1. `main.py` → initializes `asyncio` loop in separate thread.
2. User opens project → GUI loads `state.json`, file tree, memory.
3. Input message → placed in `asyncio.Queue` → `Conductor.process_request()`.
4. Intermediate statuses (`ask_user`, `delegate`, `tool_call`) → sent to `gui_queue` → `ChatPanel` updates.
5. Final → `state.json` updated, progress bar completes, input unlocked.

---

## 5. ⚙️ Critical Requirements for Developer Agents

| Requirement | Why Important | How to Implement |
|-------------|---------------|------------------|
| **Strict JSON Parsing** | Local LLMs often break format | Always use `Pydantic.model_validate_json()`. Fallback: regex extraction + retry with corrected prompt |
| **No GUI Blocking** | `mainloop()` + `await` = deadlock | Use `asyncio.run_coroutine_threadsafe()` + `tkinter` `after()` for queue polling |
| **Tool Isolation** | `read/write/bash` can break system | Path whitelist (`workspace/`), forbid `..`, `sudo`, `rm -rf`, 30s timeout |
| **Schema Validation** | `tool_call` with invalid args → crash | `Pydantic` on arguments before call. Error → return `{"error": "..."}` in `tool` response |
| **State Persistence** | Restart shouldn't lose context | Update `state.json` after each step. Atomic write (`temp → rename`) |
| **Logging** | LLM debugging impossible without logs | Record `request`, `raw_response`, `parsed_action`, `tool_result` in `projects/{id}/logs/` |
| **Interrupt Handling** | User must have control | `🛑 Stop` button sets `cancel_flag`. Agent checks flag between steps, saves partial state |

---

## 6. 📚 Reference: APIs, Tools, Roles, and Context

> ⚠️ **Critical Note**: Local LLMs have **no built-in API for "role switching"**. Roles, context, and tools are managed **exclusively at the code level** via system prompts, message history, and JSON validation.

### 🔌 LM Studio Server API

| Resource | Link | What to Look For | Project Note |
|----------|------|------------------|--------------|
| **OpenAI-Compatible API** | https://lmstudio.ai/docs/api/openai-compatibility | `/v1/chat/completions`, `/v1/models` | Main endpoint for `tools`, `tool_choice`, `temperature`. Works via `openai` Python SDK. |
| **Native API (advanced params)** | https://lmstudio.ai/docs/api/native-api | `/api/v1/chat`, `/api/v1/models`, `context_length`, `gpu_layers` | Use only if need to override `context_window`. **Not compatible with `tools`** in same request. |
| **Streaming & SSE** | https://lmstudio.ai/docs/api/streaming | `stream: true`, parse `data: ` | For GUI: update status in real-time, but parse `tool_calls` only in final chunk. |

### 🛠 Qwen Tools / Function Calling

| Resource | Link | What to Look For | Project Note |
|----------|------|------------------|--------------|
| **Function Calling Guide** | https://help.aliyun.com/zh/model-studio/developer-reference/function-calling | `tools`, `tool_calls`, `tool` role format | Reference spec for all Qwen models. |
| **JSON Schema Guidelines** | https://help.aliyun.com/zh/model-studio/developer-reference/json-schema-guidelines | `type`, `properties`, `required`, `description` | **Without `description` model won't understand when to call tool.** Minimize nesting. |

### 🎭 Role and Context Management

| Aspect | Documentation / Pattern | Project Implementation |
|--------|------------------------|------------------------|
| **Role Switching** | System prompts | Replace `system` message before request. Don't mix roles without explicit `</role>` marker. |
| **Project Context** | Scoped context | Store in `project_memory`. Export only relevant keys. Use `compaction` after 50% window fill. |
| **Role Memory Isolation** | Architectural pattern: `Scoped Context` | Each role gets `system` prompt + sliced context. Don't pass other roles' `tool` responses without filtering. |
| **Prevent Role Drift** | Role-Consistency Prompting | In role `system` prompt explicitly state: `You are ONLY <role>. Don't analyze tasks, don't plan, don't call Director directly.` |

---

## 7. 📊 Integration Map for Development Phases

| Project Phase | Links to Study | Check Before Coding |
|---------------|----------------|---------------------|
| **Phase 1: Infrastructure** | LM Studio OpenAI API, Native API, Qwen Context Length | `client.models.list()` returns correct `id`. `chat.completions` with `tools` doesn't crash on GGUF. |
| **Phase 2: Director** | Qwen Function Calling, JSON Schema Guidelines, Pydantic Validation | All `DelegateAction` parse without errors. Loop doesn't infinite-loop on `ask_user`. |
| **Phase 3: Agents** | Qwen-Agent, Role-Consistency Prompting, Scoped Context | Role executes only allowed tools. `callback` to Director always in valid JSON. |
| **Phase 4: GUI** | LM Studio Streaming, Tkinter async bridge | `after()` doesn't block `mainloop()`. Status updates without `Thread` race conditions. |
| **Phase 5: Memory** | Context Management, Compaction patterns | `state.json` updates atomically. Context doesn't exceed 70% model window. |

---

## 8. ⚠️ Critical Pre-Launch Checks

| Check | Method | Success Criteria |
|-------|--------|------------------|
| **Tool Calling on Local Model** | Send request with 2 tools, ask to call both | Model returns `tool_calls` as array, not text. Arguments valid. |
| **Role Switching Without Drift** | Give role task outside its competence | Role responds within prompt scope or requests Director, doesn't take another role. |
| **Context Not Truncated** | Load 50k tokens history + system prompt + tools | Model doesn't return `context_length_exceeded`, `tool_calls` generated. |
| **GUI Doesn't Block** | Send request, simultaneously change ConfigPanel tabs | All elements respond, progress updates, no `Not Responding`. |
| **LLM JSON Validation** | Intentionally break schema in request | System returns `{"error": "..."}` in `tool` response, doesn't crash with `ValueError`. |

---

*This document is ready for handoff to AI agents or developers. All specifications are complete and actionable.*
