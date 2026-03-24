# llm.py — OpenRouter API integration
#
# Provides two functions:
#   chat()       — Send a conversation to the LLM and return the reply
#   get_models() — Fetch the list of available models from OpenRouter
#
# Every chat() call appends token usage to data/usage.log for cost tracking.
# The 'middle-out' transform is included on all requests so that OpenRouter
# gracefully trims context if it ever exceeds the model's context window.

from datetime import datetime
from pathlib import Path

import requests

import config

OPENROUTER_BASE = "https://openrouter.ai/api/v1"
USAGE_LOG = Path(__file__).parent / "data" / "usage.log"


def _chat_with_model(model: str, messages: list, system_prompt: str) -> str:
    """Send a conversation to OpenRouter using a specific model ID."""
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/pincer",
        "X-Title": "Pincer",
    }

    body = {
        "model": model,
        # Prepend the system prompt as the first message
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        # middle-out: if context exceeds the model's window, OpenRouter trims
        # the middle of the conversation (keeps start and end) rather than
        # returning an error. This is a safety net, not the primary strategy.
        "transforms": ["middle-out"],
    }

    response = requests.post(
        f"{OPENROUTER_BASE}/chat/completions",
        headers=headers,
        json=body,
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    reply = data["choices"][0]["message"]["content"]

    # Log token usage for the daily cost report task
    _log_usage(data.get("usage", {}))

    return reply


def chat(messages: list, system_prompt: str) -> str:
    """
    Send a conversation to OpenRouter and return the assistant's reply text.

    messages:      List of {"role": "user"/"assistant"/"system", "content": "..."}
                   These form the conversation history passed to the model.
    system_prompt: The system prompt string (identity + skills). Sent as the
                   first message with role 'system'.

    If the active model is a free model and it fails, automatically falls back
    to config.OPENROUTER_FALLBACK_MODEL and notifies via Telegram.
    """
    model = config.OPENROUTER_MODEL
    try:
        return _chat_with_model(model, messages, system_prompt)
    except Exception as e:
        fallback = config.OPENROUTER_FALLBACK_MODEL
        if model.endswith(":free") and fallback and fallback != model:
            from notify import send
            send(f"[llm] Free model {model} failed ({e}). Falling back to {fallback}.")
            return _chat_with_model(fallback, messages, system_prompt)
        raise


def get_models() -> list:
    """
    Fetch the list of available models from OpenRouter.
    Returns a sorted list of model ID strings.
    Falls back to config.POPULAR_MODELS if the request fails.
    """
    try:
        headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}
        response = requests.get(
            f"{OPENROUTER_BASE}/models",
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return sorted(m["id"] for m in data.get("data", []))
    except Exception as e:
        print(f"[llm] Could not fetch models: {e}. Using default list.")
        return config.POPULAR_MODELS


def get_free_models() -> list:
    """
    Fetch all free models from OpenRouter and return them ranked by quality.

    A model is considered free if both pricing.prompt and pricing.completion
    are "0", or if the model ID ends in ':free'.

    Ranking score = (param_billions * 1000) + (context_length / 1000)
    Parameter count is extracted from the model ID/name (e.g. '70b' -> 70).

    Returns a list of dicts sorted by score descending:
      [{"id": ..., "score": ..., "params_b": ..., "context_length": ...}, ...]
    """
    import re

    headers = {"Authorization": f"Bearer {config.OPENROUTER_API_KEY}"}
    response = requests.get(
        f"{OPENROUTER_BASE}/models",
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    ranked = []
    for m in data.get("data", []):
        model_id = m.get("id", "")
        pricing = m.get("pricing", {})
        is_free = (
            (str(pricing.get("prompt", "1")) == "0" and str(pricing.get("completion", "1")) == "0")
            or model_id.endswith(":free")
        )
        if not is_free:
            continue

        context_length = m.get("context_length", 0) or 0

        # Extract parameter count in billions from model ID or name
        search_str = model_id + " " + m.get("name", "")
        param_match = re.search(r'(\d+(?:\.\d+)?)b', search_str, re.IGNORECASE)
        params_b = float(param_match.group(1)) if param_match else 0.0

        score = (params_b * 1000) + (context_length / 1000)
        ranked.append({
            "id": model_id,
            "score": round(score, 1),
            "params_b": params_b,
            "context_length": context_length,
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def _log_usage(usage: dict) -> None:
    """Append a usage line to data/usage.log."""
    USAGE_LOG.parent.mkdir(exist_ok=True)
    prompt_tokens     = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    total_tokens      = usage.get("total_tokens", prompt_tokens + completion_tokens)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    line = (
        f"{timestamp} | model={config.OPENROUTER_MODEL} | "
        f"prompt={prompt_tokens} completion={completion_tokens} total={total_tokens}\n"
    )
    with open(USAGE_LOG, "a") as f:
        f.write(line)
