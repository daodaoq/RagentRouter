# RAgent Router

AI Cost Optimization & Smart Routing Layer for Claude Code.

**RAgent Router** sits between Claude Code and AI providers, automatically selecting the best model for each request based on configurable rules — reducing costs without changing your workflow.

## Features (MVP v0.1)

- ✅ **Anthropic API Compatible** — Drop-in replacement via `POST /v1/messages`
- ✅ **Provider Adapter** — Supports Claude + DeepSeek (mock mode for demo)
- ✅ **Rule Router** — Keyword-based automatic model selection
- ✅ **Usage Analytics** — Track requests, tokens, and costs
- ✅ **Desktop Dashboard** — Native Electron app with system tray

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### Launch Desktop App

```bash
cd frontend
npm install
npm start
```

This will:
1. Auto-start the Python backend on port 8000
2. Launch the Electron desktop window
3. Show a **🟢 green dot** in the title bar when backend is online

The app minimizes to the **system tray** when closed. Right-click the tray icon to quit.

### API Testing

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Then:

```bash
# Simple question → DeepSeek (cheaper)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Explain Redis"}],
    "max_tokens": 1024
  }'

# Architecture task → Claude (higher quality)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Design a distributed task system"}],
    "max_tokens": 1024
  }'
```

### Build Windows Installer

```bash
cd frontend
npm run dist
# Output: frontend/release/RAgent Router Setup.exe
```

## Desktop App Features

| Feature | Description |
|---------|-------------|
| Custom Title Bar | Frameless window with app-branded controls |
| System Tray | Minimize to tray, right-click for quick actions |
| Backend Manager | Auto-start/stop Python backend |
| Status Bar | Real-time backend status & stats |
| Window Persistence | Remembers position and size |
| Single Instance | Only one window at a time |
| Settings | Configurable port, tray behavior |

## Architecture

```
┌──────────────────────────────────────┐
│           Electron Desktop           │
│  ┌────────┐ ┌──────┐ ┌───────────┐  │
│  │TitleBar│ │ Tray │ │ Backend   │  │
│  │        │ │      │ │ Manager   │  │
│  └────────┘ └──────┘ └─────┬─────┘  │
│                            │ spawn  │
│  ┌────────────────────┐ ┌──▼──────┐ │
│  │ React Dashboard    │ │ Python  │ │
│  │ (Renderer)         │ │ FastAPI │ │
│  └────────────────────┘ └─────────┘ │
└──────────────────────────────────────┘
```

## Routing Rules

| Name | Keywords | Target | Priority |
|------|----------|--------|----------|
| Architecture & Design | architecture, design, refactor, 架构, 设计 | Claude | 100 |
| Bug Fix | bug, fix, debug, error, 修复, 调试 | Claude | 90 |
| Code Generation | generate, create, implement, 生成, 创建 | Claude | 80 |
| Simple Questions | explain, what is, how to, 解释 | DeepSeek | 70 |
| Documentation | document, readme, doc, 文档 | DeepSeek | 60 |

Unmatched requests default to DeepSeek (most cost-efficient).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Desktop | Electron + React + TypeScript + Vite |
| UI | Ant Design + Recharts + Custom CSS |
| State | Zustand |
| Backend | Python + FastAPI |
| Database | SQLite |

## Roadmap

- **V0.2** — Cost Router: complexity-based auto-selection
- **V0.3** — Coding Router: task-type classification
- **V0.4** — Routing Explain: transparent decision logging
- **V0.5** — Semantic Cache: deduplicate similar requests
- **V1.0** — Learning Router: ML-based model selection
