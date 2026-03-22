# Tasks

Python scripts in this directory are discovered automatically by the scheduler.

## Naming tasks

Use short, single-word names for task files (e.g. `weather.py`, `costs.py`). Avoid underscores and multi-word names — task names are typed directly into Telegram commands on a phone, and shorter names are much easier to type.

## Metadata header

Each task file should start with a header block:

```python
# TASK: Human-readable name
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: What this task does
```

## Supported schedule values

- `every day at HH:MM` — daily at a fixed time
- `every hour` — every hour
- `every N minutes` — every N minutes
- `every N seconds` — for testing
- `on demand` — manual only, triggered with `run task: <name>`

## Enabling a task

Tasks default to `ENABLED: false`. Enable via the agent:
```
enable task: disk
```
Or edit the file header and restart.

## Writing a new task

Ask Pincer to write a task for you:
```
Write a task that checks the CPU temperature every 30 minutes
```

Pincer will generate the task code, show a preview, and ask for confirmation before saving.
