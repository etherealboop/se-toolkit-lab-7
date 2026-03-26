# Lab 7 — Build a Client with an AI Coding Agent

[Sync your fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/syncing-a-fork#syncing-a-fork-branch-from-the-command-line) regularly — the lab gets updated.

## Product brief

> Build a Telegram bot that lets users interact with the LMS backend through chat. Users should be able to check system health, browse labs and scores, and ask questions in plain language. The bot should use an LLM to understand what the user wants and fetch the right data. Deploy it alongside the existing backend on the VM.

This is what a customer might tell you. Your job is to turn it into a working product using an AI coding agent (Qwen Code) as your development partner.

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌──────────────┐     ┌──────────────────────────────────┐   │
│  │  Telegram    │────▶│  Your Bot                        │   │
│  │  User        │◀────│  (aiogram / python-telegram-bot) │   │
│  └──────────────┘     └──────┬───────────────────────────┘   │
│                              │                               │
│                              │ slash commands + plain text    │
│                              ├───────▶ /start, /help         │
│                              ├───────▶ /health, /labs        │
│                              ├───────▶ intent router ──▶ LLM │
│                              │                    │          │
│                              │                    ▼          │
│  ┌──────────────┐     ┌──────┴───────┐    tools/actions      │
│  │  Docker      │     │  LMS Backend │◀───── GET /items      │
│  │  Compose     │     │  (FastAPI)   │◀───── GET /analytics  │
│  │              │     │  + PostgreSQL│◀───── POST /sync      │
│  └──────────────┘     └──────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

## Requirements

### P0 — Must have

1. Testable handler architecture — handlers work without Telegram
2. CLI test mode: `cd bot && uv run bot.py --test "/command"` prints response to stdout
3. `/start` — welcome message
4. `/help` — lists all available commands
5. `/health` — calls backend, reports up/down status
6. `/labs` — lists available labs
7. `/scores <lab>` — per-task pass rates
8. Error handling — backend down produces a friendly message, not a crash

### P1 — Should have

1. Natural language intent routing — plain text interpreted by LLM
2. All 9 backend endpoints wrapped as LLM tools
3. Inline keyboard buttons for common actions
4. Multi-step reasoning (LLM chains multiple API calls)

### P2 — Nice to have

1. Rich formatting (tables, charts as images)
2. Response caching
3. Conversation context (multi-turn)

### P3 — Deployment

1. Bot containerized with Dockerfile
2. Added as service in `docker-compose.yml`
3. Deployed and running on VM
4. README documents deployment

## Learning advice

Notice the progression above: **product brief** (vague customer ask) → **prioritized requirements** (structured) → **task specifications** (precise deliverables + acceptance criteria). This is how engineering work flows.

You are not following step-by-step instructions — you are building a product with an AI coding agent. The learning comes from planning, building, testing, and debugging iteratively.

## Learning outcomes

By the end of this lab, you should be able to say:

1. I turned a vague product brief into a working Telegram bot.
2. I can ask it questions in plain language and it fetches the right data.
3. I used an AI coding agent to plan and build the whole thing.

## Tasks

### Prerequisites

1. Complete the [lab setup](./lab/setup/setup-simple.md#lab-setup)

> **Note**: First time in this course? Do the [full setup](./lab/setup/setup-full.md#lab-setup) instead.

### Required

1. [Plan and Scaffold](./lab/tasks/required/task-1.md) — P0: project structure + `--test` mode
2. [Backend Integration](./lab/tasks/required/task-2.md) — P0: slash commands + real data
3. [Intent-Based Natural Language Routing](./lab/tasks/required/task-3.md) — P1: LLM tool use
4. [Containerize and Document](./lab/tasks/required/task-4.md) — P3: containerize + deploy

## Deploy

This section explains how to deploy the bot alongside the backend using Docker.

### Prerequisites

1. **VM access** — You should have SSH access to your VM
2. **Bot token** — Get from [@BotFather](https://t.me/BotFather) on Telegram
3. **LLM API key** — Set up Qwen Code API proxy on your VM (see setup step 1.9)
4. **Environment file** — `.env.docker.secret` with all required values

### Environment variables

Edit `.env.docker.secret` on your VM and set:

```bash
# Bot token from @BotFather
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyz

# LLM API (Qwen Code)
LLM_API_KEY=your-qwen-api-key
LLM_API_MODEL=qwen3-coder-flash

# LMS API (already set from backend setup)
LMS_API_KEY=my-secret-api-key
```

The bot uses these additional env vars (configured automatically in docker-compose.yml):

- `LMS_API_URL=http://backend:8000` — Backend service name inside Docker network
- `LLM_API_BASE_URL=http://host.docker.internal:42005/v1` — Qwen proxy on host

### Deploy commands

On your VM:

```bash
cd ~/se-toolkit-lab-7

# Stop the background bot process (if running from Task 2/3)
pkill -f "bot.py" 2>/dev/null

# Build and start all services
docker compose --env-file .env.docker.secret up --build -d

# Check status
docker compose --env-file .env.docker.secret ps
```

You should see:

```
NAME                STATUS
se-toolkit-lab-7-backend-1    Up
se-toolkit-lab-7-bot-1        Up
se-toolkit-lab-7-postgres-1   Up (healthy)
se-toolkit-lab-7-caddy-1      Up
```

### Verify deployment

1. **Check bot is running:**

   ```bash
   docker compose --env-file .env.docker.secret logs bot --tail 20
   ```

   Look for: "Bot started. Polling..."

2. **Check backend is healthy:**

   ```bash
   curl -sf http://localhost:42002/docs
   ```

   Should return Swagger UI HTML.

3. **Test in Telegram:**
   - `/start` — Welcome message
   - `/health` — Backend status
   - "what labs are available?" — Natural language query
   - "show me scores for lab 4" — LLM-powered data fetch

### Troubleshooting

| Symptom | Solution |
|---------|----------|
| Bot container restarting | Check logs: `docker compose logs bot` |
| LLM queries fail | Ensure Qwen proxy is running: `cd ~/qwen-code-oai-proxy && docker compose ps` |
| Backend connection error | Check `LMS_API_URL` uses `http://backend:8000` not `localhost` |
| BOT_TOKEN error | Verify token in `.env.docker.secret` |

### Update deployment

After pushing code changes:

```bash
cd ~/se-toolkit-lab-7
git pull
docker compose --env-file .env.docker.secret up --build -d
```
