# TASK: costs
# SCHEDULE: every day at 05:30
# ENABLED: false
# DESCRIPTION: Reads data/usage.log and sends a 7-day token usage and cost summary via Telegram

from pathlib import Path
from datetime import datetime, timedelta
import re

import config
from notify import send


# Cost per million tokens (input, output) in USD
MODEL_PRICING = {
    "anthropic/claude-3-5-haiku":              (0.80,  4.00),
    "anthropic/claude-sonnet-4-5":             (3.00, 15.00),
    "anthropic/claude-sonnet-4.6":             (3.00, 15.00),
    "anthropic/claude-opus-4-6":              (15.00, 75.00),
}
DEFAULT_PRICING = (0.0, 0.0)  # free / unknown models


def estimate_cost(model, prompt_tokens, completion_tokens):
    input_rate, output_rate = MODEL_PRICING.get(model, DEFAULT_PRICING)
    return (prompt_tokens * input_rate + completion_tokens * output_rate) / 1_000_000


def run():
    log_path = Path(__file__).parent.parent / "data" / "usage.log"

    if not log_path.exists():
        send("Cost Report: no usage.log found yet.")
        return

    today = datetime.now().date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]  # oldest to newest

    all_lines = log_path.read_text().splitlines()

    report_days = []
    week_cost = 0.0
    week_tokens = 0

    for day in days:
        date_str = day.strftime("%Y-%m-%d")
        day_tokens = 0
        day_cost = 0.0
        model_data = {}

        for line in all_lines:
            if not line.startswith(date_str):
                continue
            m = re.search(r'model=(\S+).*prompt=(\d+)\s+completion=(\d+)', line)
            if m:
                model = m.group(1)
                prompt = int(m.group(2))
                completion = int(m.group(3))
                total = prompt + completion
                cost = estimate_cost(model, prompt, completion)
                if model not in model_data:
                    model_data[model] = {"prompt": 0, "completion": 0, "cost": 0.0}
                model_data[model]["prompt"] += prompt
                model_data[model]["completion"] += completion
                model_data[model]["cost"] += cost
                day_tokens += total
                day_cost += cost

        report_days.append((date_str, day_tokens, day_cost, model_data))
        week_cost += day_cost
        week_tokens += day_tokens

    # Build message
    lines_out = [f"Cost Report — last 7 days", ""]

    for date_str, day_tokens, day_cost, model_data in report_days:
        if day_tokens == 0:
            lines_out.append(f"{date_str}: no usage")
        else:
            lines_out.append(f"{date_str}: {day_tokens:,} tokens — ${day_cost:.4f}")
            for model, data in sorted(model_data.items(), key=lambda x: -x[1]["cost"]):
                total = data["prompt"] + data["completion"]
                lines_out.append(f"  {model}: {total:,} tokens — ${data['cost']:.4f}")

    lines_out.append("")
    lines_out.append(f"7-day total: {week_tokens:,} tokens — ${week_cost:.4f}")

    send("\n".join(lines_out))
