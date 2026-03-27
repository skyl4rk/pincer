# Pincer

An AI assistant for the Raspberry Pi 4, forked from MolluskAI. Pincer extends the original with broader file access, dynamic subagents, and an intelligent orchestrator.

---

## Features

- **AI assistant** accessible via terminal, Telegram, and voice
- **File read / modify / write / delete** — the AI can work with any project file, not just skills and tasks
- **Self-repair** — run a broken task, capture the error, and ask the AI to fix it
- **Scheduled tasks** — Python scripts that run automatically without using AI credits
- **Skill templates** — markdown files that shape how the AI responds
- **Self-improvement** — corrections, errors, and discoveries are logged to `.learnings/` and reviewed before major tasks; broadly applicable learnings can be promoted to `RULES.MD`
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
wget https://raw.githubusercontent.com/skyl4rk/pincer/main/install.sh
chmod +x install.sh && ./install.sh
```

The installer clones the repo, creates a virtual environment, and installs all dependencies.

For voice message support (optional):

```bash
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

# If Pincer is already running and you are using it via Telegram,
# you can also open a terminal session at the same time
python agent.py --terminal
```

---

## Running as a System Service

First, create the required directories if they don't already exist:

```bash
mkdir -p ~/.config/systemd/user
```

Then create `~/.config/systemd/user/pincer.service`:

```ini
[Unit]
Description=Pincer Agent
After=network.target

[Service]
WorkingDirectory=/home/YOUR_USERNAME/pincer
ExecStart=/home/YOUR_USERNAME/pincer/venv/bin/python agent.py --no-terminal
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
model: freeride      Show the top 10 ranked free models
model: freeride N    Switch to model N from that list (e.g. model: freeride 2)
run task: models     Show last 5 unique models used (most recent first)
models: <N>          Switch to model N from that list (e.g. models: 2)

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

## Grocery Ordering (Aldi + Instacart)

Warning: this task is untested, use with caution!
Pincer can manage your weekly grocery shopping — maintaining a staples list, generating orders, and sending an Instacart checkout link directly to Telegram. You click the link to review and pay; no payment details are ever stored.

### How it works

- A staples list in `data/grocery/staples.json` records everything you regularly buy, with frequency (weekly, biweekly, monthly) and category.
- On demand (or on a schedule), Pincer builds a cart from your staples and sends an Instacart checkout URL to Telegram. Weekly runs include weekly and due biweekly items; monthly runs (first 3 days of the month) include everything.
- The AI skill (`skills/grocery_ordering.md`) handles natural-language interactions — adding items, removing them, changing quantities, and parsing receipts — all through normal conversation.

### Setup

1. Register for an Instacart Developer API key at [instacart.com/developer](https://www.instacart.com/developer).
2. Browse to your local Aldi on instacart.com and note the numeric store ID from the URL.
3. Add both to `.env`:
   ```env
   INSTACART_API_KEY=your_key_here
   ALDI_INSTACART_STORE_ID=your_store_id
   ```
4. Enable the task:
   ```
   enable task: grocery
   ```

### Conversation examples

Just talk to Pincer naturally via Telegram or terminal:

```
"add oat milk to my staples"
"remove yogurt from my list"
"change bread to biweekly"
"show my staples"
"order groceries"             ← shows the list, then sends the cart link on confirmation
"run task: grocery"           ← triggers immediately without confirmation
```

Paste or forward an Instacart receipt and Pincer will detect the items and ask which to add to your staples.

### Learning over time

Pincer builds up your staples list through four methods:

| Method | How it works |
|--------|-------------|
| **Manual** | "add X to my staples" — added immediately |
| **Order history** | Paste a receipt — Pincer detects items and asks which to save |
| **Conversational** | 24 hours after an order, Pincer asks how it went and updates the list based on your reply |
| **Frequency tracking** | Items you request ad-hoc 3+ times in 30 days are automatically promoted to staples |

### Scheduling

To receive your shopping list automatically every week:
```
enable task: grocery
```
Then edit `tasks/grocery.py` and change the `SCHEDULE` header to (for example):
```python
# SCHEDULE: every monday at 08:00
```
Reload with `disable task: grocery` then `enable task: grocery`.

---

## Property Search

Pincer can run a daily Zillow search for land listings near a configured zip code, filtered by price and minimum acreage, and send the results to Telegram.

### Setup

Add your zip codes to `.env` (never committed to version control):

```env
PROPERTY_ZIP=40330
PROPERTY_NEARBY_ZIPS=40336,40337,40040
```

`PROPERTY_ZIP` is the primary search zip. `PROPERTY_NEARBY_ZIPS` is optional — add surrounding zip codes to widen the search area.

Then enable the task:

```
enable task: property
```

### Changing search parameters

Ask Pincer in Telegram:

```
change property max price to $30,000
set property minimum acres to 1
show 5 property results instead of 10
```

| Parameter | Variable | Default | Description |
|-----------|----------|---------|-------------|
| Zip code | `PROPERTY_ZIP` in `.env` | — | Primary zip code (required) |
| Nearby zips | `PROPERTY_NEARBY_ZIPS` in `.env` | — | Extra zip codes to search (comma-separated, optional) |
| Max price | `MAX_PRICE` in `tasks/property.py` | $20,000 | Maximum listing price |
| Min acreage | `MIN_ACRES` in `tasks/property.py` | 0.4 | Minimum lot size in acres |
| Max results | `MAX_RESULTS` in `tasks/property.py` | 10 | Number of listings to show |

---

## Built-in Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `freeride` | every 6 hours | Fetch and rank free models from OpenRouter; update the cache |
| `stoic` | daily at 05:00 | Send a Stoic quote to Telegram each morning |
| `costs` | daily at 05:30 | Send a 7-day token usage and cost summary |
| `weather` | daily at 05:45 | Send a 3-day NOAA weather forecast (requires `WEATHER_LOCATION` in `.env`) |
| `property` | daily at 05:45 | Search Zillow for land listings near a configured zip code (requires `PROPERTY_ZIP` in `.env` — see [Property Search](#property-search)) |
| `restart` | on demand | Restart the pincer systemd service |
| `reboot` | on demand | Reboot the device |
| `models` | on demand | Show the last 5 unique models used |
| `disk` | on demand | Report disk usage for the root filesystem |
| `grocery` | on demand | Generate an Aldi shopping cart via Instacart (see [Grocery Ordering](#grocery-ordering-aldi--instacart)) |

Scheduled tasks run automatically but default to `ENABLED: false`. Enable with `enable task: <name>`.

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

# Weather task (latitude, longitude)
WEATHER_LOCATION=40.7128, -74.0060

# Property task — zip codes are kept out of source code for privacy
PROPERTY_ZIP=40330
PROPERTY_NEARBY_ZIPS=40336,40337,40040

# Grocery task — Instacart Developer Platform
# Register at: https://www.instacart.com/developer
INSTACART_API_KEY=
ALDI_INSTACART_STORE_ID=

# Email gateway (optional — leave blank to disable)
EMAIL_IMAP_HOST=
EMAIL_SMTP_HOST=
```

Switch model at runtime without restarting:
```
model: anthropic/claude-3-5-haiku
```

View and switch between recently used models:
```
run task: models     # lists last 5 unique models with numbers
models: 2            # switches to the 2nd model in that list
```

Browse and select free models with **freeride**:
```
model: freeride        # show the top 10 ranked free models
model: freeride 2      # switch to model #2 from that list
run task: freeride     # re-fetch rankings from OpenRouter and update the cache
```

Freeride ranks free models by parameter count (primary) and context length (secondary), and refreshes the list every 6 hours in the background. You are only notified if the top-ranked model changes. When a free model is selected, the previous non-free model is saved as a fallback — if the free model fails, Pincer automatically retries with the fallback and notifies you via Telegram.

---

## Recommended Workflow

It is recommended to use [Claude Code](https://github.com/anthropics/claude-code) in parallel with Pincer to create, modify, and debug tasks and agents. Claude Code provides a powerful terminal-based interface for working directly with the project files.

### Using OpenClaw Skills with Pincer

[OpenClaw](https://github.com/openclaw/openclaw) has a large community skill ecosystem with over 13,000 skills available on the [ClawHub registry](https://clawhub.ai). OpenClaw skills are markdown files that instruct the AI how to behave in a specific domain — the same concept as Pincer skills.

You can adapt any OpenClaw skill for Pincer by downloading the `SKILL.md` file and asking Claude Code to convert it into a Pincer skill (stripping the OpenClaw-specific frontmatter and saving it to `skills/`).

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
