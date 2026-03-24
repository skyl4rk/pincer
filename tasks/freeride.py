# TASK: freeride
# SCHEDULE: every 6 hours
# ENABLED: true
# DESCRIPTION: Fetch and rank free models from OpenRouter; update data/freeride.json

import json
from datetime import datetime
from pathlib import Path

import llm
from notify import send

DATA_FILE = Path(__file__).parent.parent / "data" / "freeride.json"


def load_cached() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception:
            pass
    return {}


def format_ranking(models: list, n: int = 10) -> str:
    """Return a formatted top-N ranking string for display."""
    lines = [f"Top {min(n, len(models))} free models (ranked by size + context):"]
    for i, m in enumerate(models[:n], 1):
        ctx_k = m["context_length"] // 1000 if m["context_length"] else "?"
        params = f"{m['params_b']}b" if m["params_b"] else "?"
        lines.append(f"  [{i}] {m['id']}  ({params}, {ctx_k}k ctx)")
    lines.append(f"\nTo select: model: freeride <number>")
    return "\n".join(lines)


def run() -> None:
    previous = load_cached()
    prev_top = (previous.get("models") or [{}])[0].get("id")

    try:
        models = llm.get_free_models()
    except Exception as e:
        send(f"[freeride] Failed to fetch free models: {e}")
        return

    if not models:
        send("[freeride] No free models found.")
        return

    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps({
        "updated": datetime.now().isoformat(timespec="seconds"),
        "models": models,
    }, indent=2))

    top = models[0]
    if top["id"] != prev_top:
        if prev_top:
            send(f"[freeride] New top free model: {top['id']}\nPrevious: {prev_top}")
        else:
            send(f"[freeride] Top free model: {top['id']} ({top['params_b']}b params, {top['context_length']//1000}k ctx)")
