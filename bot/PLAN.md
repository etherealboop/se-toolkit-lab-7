# Bot Development Plan

## Overview

This document outlines the implementation plan for the LMS Telegram bot across four tasks. The bot provides students with access to their lab scores, submission history, and analytics through a conversational interface.

## Task 1: Plan and Scaffold

**Goal:** Establish project structure and testable architecture.

- Create `bot/` directory with entry point (`bot.py`), handlers (`handlers/`), services (`services/`), and configuration (`config.py`)
- Implement `--test` mode that calls handlers directly without Telegram connection
- Define handler interface: async functions taking `user_id` and optional arguments, returning `str`
- Set up `pyproject.toml` with dependencies: `aiogram`, `httpx`, `python-dotenv`

**Key architectural decision:** Handlers are pure functions independent of Telegram. This enables testing via `--test` mode and keeps business logic separate from transport layer.

## Task 2: Backend Integration

**Goal:** Connect handlers to the LMS backend API.

- Create `services/lms_client.py` — HTTP client for backend requests
- Implement Bearer token authentication using `LMS_API_KEY` from environment
- Update handlers to fetch real data:
  - `/health` → `GET /health` on backend
  - `/labs` → `GET /labs` or `GET /items/`
  - `/scores <lab>` → `GET /scores?lab=<lab>`
- Handle errors: backend unavailable, invalid lab name, authentication failures

**Key pattern:** API client abstracts HTTP details. Handlers call `await lms_client.get_health()` not `await httpx.get(...)`.

## Task 3: Intent Routing with LLM

**Goal:** Enable natural language queries via LLM tool calling.

- Create `services/llm_client.py` — client for Qwen Code API
- Define tools for each handler: `get_health()`, `get_labs()`, `get_scores(lab)`
- Implement intent router: parse user message, let LLM choose tool, execute, return result
- Write tool descriptions carefully — LLM uses these to decide which tool to call
- Update `bot.py` to route non-command messages through LLM

**Key insight:** Description quality > prompt engineering. If LLM picks wrong tool, improve tool description, don't add regex fallbacks.

## Task 4: Deployment

**Goal:** Run bot on VM with Docker.

- Create `Dockerfile` for bot: Python base, `uv sync`, run `bot.py`
- Add bot service to `docker-compose.yml`
- Configure networking: bot connects to backend via service name (`backend`), not `localhost`
- Set up environment variables from `.env.bot.secret`
- Implement health check and restart policy

**Key concept:** Docker networking uses service names. Bot's `LMS_API_URL=http://backend:42002` not `localhost:42002`.

## File Structure

```
bot/
├── bot.py              # Entry point, --test mode, Telegram polling
├── config.py           # Environment variable loading
├── pyproject.toml      # Dependencies
├── handlers/
│   ├── __init__.py     # Command handlers (pure functions)
│   └── intent_router.py # LLM-based intent routing (Task 3)
├── services/
│   ├── lms_client.py   # Backend API client (Task 2)
│   └── llm_client.py   # LLM API client (Task 3)
└── PLAN.md             # This file
```

## Testing Strategy

1. **Test mode:** `uv run bot.py --test "/command"` — verifies handler output
2. **Unit tests:** Test handlers with mocked services (future enhancement)
3. **Integration tests:** Deploy to VM, test via Telegram (autochecker)
