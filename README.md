# Pincer

An AI assistant for the Raspberry Pi 4, forked from MolluskAI. Pincer extends the original with broader file access, dynamic subagents, and an intelligent orchestrator.

---

## Features

- **AI assistant** accessible via terminal, Telegram, and voice
- **File read / modify / write / delete** — the AI can work with any project file, not just skills and tasks
- **Self-repair** — run a broken task, capture the error, and ask the AI to fix it
- **Scheduled tasks** — Python scripts that run automatically without using AI credits
- **Skill templates** — markdown files that shape how the AI responds
- **Dynamic subagents** — add a directory to `agents/` and it's immediately available
- **Intelligent orchestrator** — routes questions to the right specialist agents
- **Vector memory** — all conversations are stored and semantically searchable
- **Automatic backups** — every file write or delete saves a timestamped copy to `data/backups/`
- **Voice input** via Telegram (faster-whisper)
- **Web search** via DuckDuckGo (no API key needed)
- **PDF ingestion** — send a PDF via Telegram or use `ingest pdf: <path>`
- **Email gateway** — optional IMAP/SMTP integration (disabled by default)

---

## Requirements

- Raspberry Pi 4 (ARM64), Raspberry Pi OS
- Python 3.10+
- An [OpenRouter](https://openrouter.ai) API key
- Optionally: a Telegram bot token from [@BotFather](https://t.me/BotFather)

---

## Installation

```bash
# Clone or copy the pincer/ directory to your Pi, then:
cd ~/pincer

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# For voice message support (optional):
sudo apt install ffmpeg
```

---

## First Run

```bash
cd ~/pincer
source venv/bin/activate
python agent.py
```

On first run, a setup wizard appears (GUI on desktop, terminal prompts over SSH). Enter your OpenRouter API key and optionally a Telegram bot token.

---

## Running Modes

```bash
# Interactive terminal (default)
python agent.py

# Headless — Telegram only, no terminal
python agent.py --no-terminal

# Attach a second terminal to a running headless instance
python agent.py --terminal
```

---

## Running as a System Service

Create `~/.config/systemd/user/pincer.service`:

```ini
[Unit]
Description=Pincer Agent
After=network.target

[Service]
WorkingDirectory=/home/historian/pincer
ExecStart=/home/historian/pincer/venv/bin/python agent.py --no-terminal
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

Then enable and start it:

```bash
systemctl --user enable pincer
systemctl --user start pincer
```

> **Note:** If MolluskAI is also running as a service, Pincer needs its own Telegram bot token to avoid conflicts. Create a new bot via [@BotFather](https://t.me/BotFather) and update `TELEGRAM_TOKEN` in `~/pincer/.env`.

---

## Commands

```
help / ?             Show all commands
setup                Re-run the setup wizard

skills               List skill files
tasks                List task files and their status
agents               List loaded subagents

orchestrate: <q>     Route question through intelligent orchestrator
ensemble: <q>        Send question to all agents and synthesise results

run task: <name>     Run a task immediately
repair task: <name>  Run task, capture errors, ask AI to fix it
enable task: <name>  Enable a task
disable task: <name> Disable a task
create agent: <name> Create a new subagent with AI assistance

model                Show current model
model: <model-id>    Switch model instantly (saved to .env)

todo: <item>         Add to to-do list
done: <item or N>    Mark item done
remove: <item or N>  Remove item
recall: todo         Show open to-do items
recall: todo all     Show full to-do history

notes                List note projects
note: <project> | <idea>   Save a note
recall: <project>    Retrieve notes
recall: <project> | <theme>  Search notes by theme

search: <query>      Search memory
ingest: <url>        Fetch and store a web page
ingest pdf: <path>   Extract and store text from a PDF

backups              List available file backups
restore: <filename>  Restore a file from backup

exit / quit          Exit (terminal mode only)
```

---

## AI File Directives

The AI can use these directives to interact with the filesystem. All write, modify, and delete operations require user confirmation before executing.

| Directive | Effect |
|---|---|
| `[READ_FILE: path]` | Read any project file |
| `[MODIFY_FILE: path]...[/MODIFY_FILE]` | Create or overwrite a file |
| `[DELETE_FILE: path]` | Delete a file (backup saved first) |
| `[RUN_FILE: path]` | Run a Python script and return its output |
| `[WEB_SEARCH: query]` | Search the web |
| `[SAVE_SKILL: name.md]` | Save a skill template |
| `[SAVE_TASK: name.py]` | Save a scheduled task |

Protected files that the AI cannot access: `.env`, `config.py`, `data/memory.db`.

---

## Project Structure

```
pincer/
  agent.py              Main entry point and message dispatcher
  agents.py             Dynamic subagent loader
  orchestrator.py       Multi-agent routing and synthesis
  config.py             .env loader
  llm.py                OpenRouter API integration
  memory.py             SQLite vector memory store
  scheduler.py          Task runner and scheduler
  telegram_bot.py       Telegram + voice gateway
  transcribe.py         Whisper speech-to-text
  email_bot.py          IMAP/SMTP email gateway (disabled by default)
  notify.py             Shared notification utility for tasks
  web_search.py         DuckDuckGo search
  onboarding.py         First-run setup wizard

  IDENTITY.MD           Main agent persona
  ROLE.MD               Main agent role
  RULES.MD              Behavioural rules (AI-editable)

  agents/               Subagent definitions
    example_analyst/
      IDENTITY.MD       Agent persona
      ROLE.MD           Agent role
      agent.cfg         model=..., enabled=true/false
    example_critic/
      ...

  orchestrator_agent/   Orchestrator persona
    IDENTITY.MD
    ROLE.MD
    SYNTHESISER.MD
    agent.cfg

  skills/               Markdown prompt templates (loaded into system prompt)
  tasks/                Python automation scripts
  data/
    memory.db           Vector memory database
    usage.log           API token usage log
    backups/            Timestamped file backups
  .env                  API keys and secrets (never commit this)
  requirements.txt
```

---

## Adding a Subagent

Create a new directory under `agents/` with three files:

```
agents/my_agent/
  IDENTITY.MD   — the agent's persona (2–3 sentences)
  ROLE.MD       — the agent's role (1–2 sentences)
  agent.cfg     — model and enabled flag
```

`agent.cfg` format:
```
model=google/gemini-2.0-flash-001
enabled=true
```

The agent is discovered automatically on the next `orchestrate:` or `ensemble:` call. No restart required.

Or ask Pincer to do it for you:
```
create agent: researcher
```

---

## Adding a Task

Ask Pincer to write one:
```
Write a task that checks CPU temperature every 30 minutes and sends it via Telegram
```

Pincer will propose the task code with a preview and ask for confirmation before saving. Tasks default to `ENABLED: false` — enable with:
```
enable task: <name>
```

Tasks that fail three times consecutively are automatically disabled to prevent loops.

---

## Memory

All conversations are stored in `data/memory.db` using local embeddings (`BAAI/bge-small-en-v1.5` via fastembed). The AI retrieves semantically relevant past context on every message.

Fallback chain if dependencies are unavailable:
1. sqlite-vec KNN search (fastest)
2. numpy cosine similarity
3. SQLite FTS5 full-text search

---

## Configuration

All settings live in `.env`. Key variables:

```env
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=google/gemini-2.0-flash-001

TELEGRAM_TOKEN=your-bot-token
TELEGRAM_ALLOWED_USERS=123456789
TELEGRAM_CHAT_ID=123456789

# Email gateway (optional — leave blank to disable)
EMAIL_IMAP_HOST=
EMAIL_SMTP_HOST=
```

Switch model at runtime without restarting:
```
model: anthropic/claude-3-5-haiku
```

---

## Relationship to MolluskAI

Pincer is a fork of MolluskAI. The core architecture (agent loop, memory, scheduler, Telegram, email) is carried over directly. The main additions are:

- Broader file access scope (project-wide with a blocklist, not a narrow whitelist)
- `[MODIFY_FILE:]` and `[DELETE_FILE:]` directives
- `[RUN_FILE:]` for executing scripts in the agentic loop
- `repair task:` command for self-repair workflows
- Automatic file backups on every write or delete
- Dynamic subagent discovery from `agents/*/`
- Intelligent orchestrator that routes questions selectively
- `create agent:` command
- `restore:` command for rolling back file changes

Both agents can run simultaneously as long as they use different Telegram bot tokens.
