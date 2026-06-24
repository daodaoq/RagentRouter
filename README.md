# RAgent Router

AI Cost Optimization & Smart Routing Layer for Claude Code.

**RAgent Router** sits between Claude Code and AI providers, automatically selecting the best model for each request based on configurable rules — reducing costs without changing your workflow.

## Features (MVP v0.1)

- ✅ **Anthropic API Compatible** — Drop-in replacement via `POST /v1/messages`
- ✅ **Provider Adapter** — Supports Claude + DeepSeek (mock mode for demo)
- ✅ **Rule Router** — Keyword-based automatic model selection
- ✅ **Usage Analytics** — Track requests, tokens, and costs
- ✅ **Dashboard** — Real-time cost overview, charts, and route history

## Quick Start

### Option 1: One-click Start (Windows)

```bash
start.bat
```

Opens two windows:
- **Backend** → http://localhost:8000
- **Frontend** → http://localhost:5173

### Option 2: Manual Run

#### Prerequisites
- Python 3.10+
- Node.js 18+

#### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
# → http://localhost:8000
```

#### Frontend (Browser)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

#### Frontend (Electron Desktop)

```bash
cd frontend
npm install
npm run electron:dev
# → Launches Electron window
```

### Option 3: Docker Compose

> ⚠️ **国内用户**需要先配置 Docker 镜像加速器，否则拉取镜像会失败。
> 推荐使用 [DaoCloud 镜像](https://docs.daocloud.io/community/mirror/) 或阿里云镜像。

```bash
docker-compose up
```

Then open:
- **Dashboard**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs
# → Launches Electron window
```

## Test the Router

Send a test request to see routing in action:

```bash
# Simple question → routed to DeepSeek (cheaper)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Explain Redis transactions"}],
    "max_tokens": 1024
  }'

# Architecture task → routed to Claude (higher quality)
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Design a distributed task scheduling system"}],
    "max_tokens": 1024
  }'
```

## Architecture

```
Claude Code → CC Switch → RAgent Router → Claude / DeepSeek
                                │
                          ┌─────┴──────┐
                          │  Dashboard  │
                          │  (Electron) │
                          └────────────┘
```

## Tech Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Frontend | Electron + React + TypeScript + Vite    |
| UI       | Ant Design + Recharts                   |
| State    | Zustand                                 |
| Backend  | Python + FastAPI                        |
| Database | SQLite (PostgreSQL in production)       |
| Cache    | In-memory (Redis in production)         |
| Deploy   | Docker Compose                          |

## Routing Rules

Rules are defined by keywords and checked in priority order:

| Name | Keywords | Target | Priority |
|------|----------|--------|----------|
| Architecture & Design | architecture, design, refactor, 架构, 设计 | Claude | 100 |
| Bug Fix | bug, fix, debug, error, 修复, 调试 | Claude | 90 |
| Code Generation | generate, create, implement, 生成, 创建 | Claude | 80 |
| Simple Questions | explain, what is, how to, 解释 | DeepSeek | 70 |
| Documentation | document, readme, doc, 文档 | DeepSeek | 60 |

Unmatched requests default to DeepSeek (most cost-efficient).

## Roadmap

- **V0.2** — Cost Router: complexity-based auto-selection
- **V0.3** — Coding Router: task-type classification
- **V0.4** — Routing Explain: transparent decision logging
- **V0.5** — Semantic Cache: deduplicate similar requests
- **V1.0** — Learning Router: ML-based model selection
