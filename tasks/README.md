# Tasks

Python scripts in this directory are discovered automatically by the scheduler.

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
enable task: df_report
```
Or edit the file header and restart.

## Writing a new task

Ask Pincer to write a task for you:
```
Write a task that checks the CPU temperature every 30 minutes
```

Pincer will generate the task code, show a preview, and ask for confirmation before saving.
