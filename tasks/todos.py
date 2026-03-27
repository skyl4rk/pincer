# TASK: todos
# SCHEDULE: every day at 06:00
# ENABLED: true
# DESCRIPTION: Sends open to-do items to Telegram each morning.

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import memory
from notify import send


def run():
    notes = memory.get_notes("todo")
    open_notes = [n for n in notes if n["content"].strip().startswith("[ ]")]

    if not open_notes:
        send("No open to-do items.")
        return

    lines = [f"To-do  [{len(open_notes)} item{'s' if len(open_notes) != 1 else ''}]",
             "─" * 44]
    for i, n in enumerate(open_notes, 1):
        ts = (n.get("timestamp") or "")[:16]
        lines.append(f"\n[{i}] {ts}")
        lines.append(n["content"])

    send("\n".join(lines))


if __name__ == "__main__":
    run()
