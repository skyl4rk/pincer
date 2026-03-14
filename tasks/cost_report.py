# TASK: Daily Cost Report
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: Reads data/usage.log and sends a daily token usage summary via Telegram

from pathlib import Path
from datetime import datetime, timedelta
import re

import config
from notify import send


def run():
    log_path = Path(__file__).parent.parent / "data" / "usage.log"

    if not log_path.exists():
        send("Cost Report: no usage.log found yet.")
        return

    # Read yesterday's entries
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    lines = log_path.read_text().splitlines()

    totals = {}
    total_tokens = 0

    for line in lines:
        if not line.startswith(yesterday):
            continue
        m = re.search(r'model=(\S+).*total=(\d+)', line)
        if m:
            model  = m.group(1)
            tokens = int(m.group(2))
            totals[model] = totals.get(model, 0) + tokens
            total_tokens += tokens

    if not totals:
        send(f"Cost Report ({yesterday}): no usage recorded.")
        return

    lines_out = [f"Cost Report — {yesterday}", f"Total tokens: {total_tokens:,}"]
    for model, tokens in sorted(totals.items(), key=lambda x: -x[1]):
        lines_out.append(f"  {model}: {tokens:,}")

    send("\n".join(lines_out))
