# TASK: models
# SCHEDULE: on demand
# ENABLED: true
# DESCRIPTION: Show the last 5 unique models used, with copy-paste model: commands

import re
from pathlib import Path

import config
from notify import send


def recent_models(n: int = 5) -> list[str]:
    """Return up to n unique model IDs, most recently used first."""
    log_path = Path(__file__).parent.parent / "data" / "usage.log"
    if not log_path.exists():
        return []

    seen: list[str] = []
    for line in reversed(log_path.read_text().splitlines()):
        m = re.search(r'model=(\S+)', line)
        if m:
            model = m.group(1)
            if model not in seen:
                seen.append(model)
            if len(seen) == n:
                break

    return seen


def run() -> None:
    models = recent_models()
    if not models:
        send("No model usage recorded yet.")
        return

    current = config.OPENROUTER_MODEL
    lines = ["Recent models (most recent first):", ""]

    for i, model in enumerate(models, 1):
        marker = " ← current" if model == current else ""
        lines.append(f"  [{i}] {model}{marker}")

    lines += [
        "",
        "To switch, send:",
        "  model: <model-id>",
        "  — or —",
        "  models: <number>  (e.g. 'models: 2')",
    ]

    send("\n".join(lines))
