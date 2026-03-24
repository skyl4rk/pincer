# TASK: Grocery Order Manager
# SCHEDULE: on demand
# ENABLED: false
# DESCRIPTION: Manages Aldi grocery staples and generates Instacart checkout URLs.
#              Sends a weekly or monthly shopping cart link to Telegram.
#              Learning: tracks ad-hoc requests and auto-promotes frequently ordered items.
#              Run manually: run task: grocery
#              The AI skill (skills/grocery_ordering.md) handles conversational interactions.

import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config
from notify import send

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BASE        = Path(__file__).parent.parent
_STAPLES     = _BASE / "data" / "grocery" / "staples.json"
_HISTORY     = _BASE / "data" / "grocery" / "history.json"
_GROCERY_DIR = _BASE / "data" / "grocery"

# Instacart Developer Platform API
_IC_BASE = "https://connect.instacart.com"

# Category display order for formatted messages
_CATEGORY_ORDER = [
    "produce", "dairy", "meat", "bakery",
    "pantry", "frozen", "beverages", "snacks",
    "household", "personal_care", "other",
]


# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------

def _default_staples() -> dict:
    return {
        "version": 1,
        "store_preference": "aldi",
        "auto_promote_threshold": 3,
        "staples": [],
    }


def _default_history() -> dict:
    return {
        "version": 1,
        "orders": [],
        "ad_hoc_requests": [],
    }


def load_staples() -> dict:
    """Read staples.json; create with defaults if missing."""
    _GROCERY_DIR.mkdir(parents=True, exist_ok=True)
    if _STAPLES.exists():
        try:
            return json.loads(_STAPLES.read_text())
        except Exception as e:
            print(f"[grocery] staples.json parse error: {e}")
    data = _default_staples()
    _STAPLES.write_text(json.dumps(data, indent=2))
    return data


def save_staples(data: dict) -> None:
    """Atomic write of staples.json."""
    _GROCERY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _STAPLES.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(_STAPLES)


def load_history() -> dict:
    """Read history.json; create with defaults if missing."""
    _GROCERY_DIR.mkdir(parents=True, exist_ok=True)
    if _HISTORY.exists():
        try:
            return json.loads(_HISTORY.read_text())
        except Exception as e:
            print(f"[grocery] history.json parse error: {e}")
    data = _default_history()
    _HISTORY.write_text(json.dumps(data, indent=2))
    return data


def save_history(data: dict) -> None:
    """Atomic write of history.json."""
    _GROCERY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _HISTORY.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(_HISTORY)


def normalize_item_name(name: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


# ---------------------------------------------------------------------------
# Staples management
# ---------------------------------------------------------------------------

def add_staple(
    name: str,
    quantity: int = 1,
    unit: str = "",
    frequency: str = "weekly",
    category: str = "other",
    notes: str = "",
    source: str = "manual",
) -> dict:
    """
    Add a new staple. Deduplicates by normalized name.
    Returns the created (or existing) staple dict.
    """
    data = load_staples()
    key  = normalize_item_name(name)

    # Check for existing entry (active or inactive)
    for item in data["staples"]:
        if normalize_item_name(item["name"]) == key:
            if not item["active"]:
                item["active"] = True
                item["frequency"] = frequency
                item["source"] = source
                save_staples(data)
            return item

    entry = {
        "id":                  str(uuid.uuid4()),
        "name":                name.strip(),
        "category":            category,
        "quantity":            quantity,
        "unit":                unit,
        "frequency":           frequency,
        "last_ordered":        None,
        "order_count":         0,
        "promoted_at":         datetime.now(timezone.utc).isoformat(),
        "source":              source,
        "active":              True,
        "notes":               notes,
        "instacart_product_id": None,
    }
    data["staples"].append(entry)
    save_staples(data)
    return entry


def remove_staple(name: str) -> bool:
    """Set active=False on a staple. Returns True if found."""
    data = load_staples()
    key  = normalize_item_name(name)
    for item in data["staples"]:
        if normalize_item_name(item["name"]) == key and item["active"]:
            item["active"] = False
            save_staples(data)
            return True
    return False


def update_staple(name: str, **kwargs) -> bool:
    """Update fields on a staple by name. Returns True if found."""
    data      = load_staples()
    key       = normalize_item_name(name)
    allowed   = {"quantity", "unit", "frequency", "category", "notes", "active"}
    for item in data["staples"]:
        if normalize_item_name(item["name"]) == key:
            for k, v in kwargs.items():
                if k in allowed:
                    item[k] = v
            save_staples(data)
            return True
    return False


def get_active_staples(frequency_filter: str = None) -> list:
    """Return active staples, optionally filtered by frequency."""
    data = load_staples()
    items = [s for s in data["staples"] if s.get("active", True)]
    if frequency_filter:
        items = [s for s in items if s.get("frequency") == frequency_filter]
    return items


# ---------------------------------------------------------------------------
# List generation
# ---------------------------------------------------------------------------

def determine_list_type() -> str:
    """Days 1-3 of the month -> 'monthly', otherwise 'weekly'."""
    return "monthly" if datetime.now().day <= 3 else "weekly"


def is_biweekly_due(staple: dict) -> bool:
    """True if a biweekly staple hasn't been ordered in the last 12+ days."""
    last = staple.get("last_ordered")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last_dt).days >= 12
    except Exception:
        return True


def generate_weekly_list() -> list:
    """Weekly + due biweekly items."""
    items = []
    for s in get_active_staples():
        freq = s.get("frequency", "weekly")
        if freq == "weekly":
            items.append(s)
        elif freq == "biweekly" and is_biweekly_due(s):
            items.append(s)
    return items


def generate_monthly_list() -> list:
    """All active staples (weekly + biweekly + monthly)."""
    return [s for s in get_active_staples()
            if s.get("frequency") in ("weekly", "biweekly", "monthly")]


# ---------------------------------------------------------------------------
# Instacart API
# ---------------------------------------------------------------------------

def _ic_headers() -> dict:
    key = getattr(config, "INSTACART_API_KEY", "") or os.getenv("INSTACART_API_KEY", "")
    return {
        "Instacart-Connect-Api-Key": key,
        "Content-Type": "application/json",
    }


def _ic_key_set() -> bool:
    key = getattr(config, "INSTACART_API_KEY", "") or os.getenv("INSTACART_API_KEY", "")
    return bool(key and key.strip())


def search_product(item_name: str, store_id: str) -> dict | None:
    """
    Search Instacart for a product. Caches the product ID back into staples.json.
    Returns the top result dict or None.
    """
    try:
        import requests
        resp = requests.get(
            f"{_IC_BASE}/idp/v1/products/search",
            headers=_ic_headers(),
            params={"query": item_name, "store_id": store_id},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("products", [])
        if not results:
            return None
        product = results[0]
        # Cache product ID back into staples
        _cache_product_id(item_name, product.get("id"))
        return product
    except Exception as e:
        print(f"[grocery] search_product error for '{item_name}': {e}")
        return None


def _cache_product_id(item_name: str, product_id: str) -> None:
    """Write the Instacart product ID back to the matching staple."""
    if not product_id:
        return
    data = load_staples()
    key  = normalize_item_name(item_name)
    for item in data["staples"]:
        if normalize_item_name(item["name"]) == key:
            item["instacart_product_id"] = product_id
            save_staples(data)
            return


def build_cart_payload(items: list, store_id: str) -> dict:
    """
    Build the POST body for /idp/v1/products/products_link.
    Resolves product IDs via search for items that don't have a cached ID.
    """
    line_items = []
    for item in items:
        product_id = item.get("instacart_product_id")
        if not product_id:
            result = search_product(item["name"], store_id)
            product_id = result.get("id") if result else None

        entry = {
            "name":     item["name"],
            "quantity": item.get("quantity", 1),
        }
        if product_id:
            entry["product_id"] = product_id
        line_items.append(entry)

    return {
        "store_id": store_id,
        "line_items": line_items,
    }


def create_checkout_url(items: list, store_id: str) -> str | None:
    """
    POST to Instacart products_link and return the checkout URL.
    Returns None on failure (degrades gracefully).
    """
    try:
        import requests
        payload = build_cart_payload(items, store_id)
        resp = requests.post(
            f"{_IC_BASE}/idp/v1/products/products_link",
            headers=_ic_headers(),
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("url")
    except Exception as e:
        print(f"[grocery] create_checkout_url error: {e}")
        return None


# ---------------------------------------------------------------------------
# Learning methods
# ---------------------------------------------------------------------------

def record_ad_hoc_request(name: str) -> None:
    """
    Track an item requested outside of the staples list.
    Auto-promotes to staples after reaching the threshold.
    """
    data = load_history()
    key  = normalize_item_name(name)
    now  = datetime.now(timezone.utc).isoformat()

    existing = None
    for req in data["ad_hoc_requests"]:
        if normalize_item_name(req["name"]) == key:
            existing = req
            break

    if existing:
        existing["request_count"] += 1
        existing["last_requested"] = now
    else:
        data["ad_hoc_requests"].append({
            "name":            name.strip(),
            "request_count":   1,
            "first_requested": now,
            "last_requested":  now,
        })

    save_history(data)
    check_auto_promote(name)


def check_auto_promote(name: str) -> bool:
    """
    Count requests in the last 30 days. If >= threshold, add to staples and notify.
    Returns True if promoted.
    """
    data      = load_history()
    staples   = load_staples()
    threshold = staples.get("auto_promote_threshold", 3)
    key       = normalize_item_name(name)
    cutoff    = datetime.now(timezone.utc) - timedelta(days=30)

    count = 0
    for req in data["ad_hoc_requests"]:
        if normalize_item_name(req["name"]) == key:
            try:
                last = datetime.fromisoformat(req["last_requested"])
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                if last >= cutoff:
                    count = req["request_count"]
            except Exception:
                pass
            break

    if count >= threshold:
        # Check not already a staple
        for item in staples["staples"]:
            if normalize_item_name(item["name"]) == key and item["active"]:
                return False
        add_staple(name, source="auto_promoted")
        send(
            f"I've added '{name}' to your weekly Aldi staples — "
            f"you've requested it {count} times recently. "
            f"Reply 'update staple: {name} biweekly' if you'd prefer a different frequency."
        )
        return True

    return False


def log_order(items: list, checkout_url: str, list_type: str) -> str:
    """Save an order to history.json. Returns the order ID."""
    data     = load_history()
    order_id = str(uuid.uuid4())
    now      = datetime.now(timezone.utc).isoformat()

    order = {
        "id":           order_id,
        "ordered_at":   now,
        "checkout_url": checkout_url,
        "items":        [{"name": i["name"], "quantity": i.get("quantity", 1)} for i in items],
        "list_type":    list_type,
        "follow_up_done": False,
    }
    data["orders"].append(order)
    # Keep only the last 50 orders
    data["orders"] = data["orders"][-50:]
    save_history(data)
    return order_id


def update_staple_after_order(item_name: str) -> None:
    """Update last_ordered and order_count after a successful order."""
    data = load_staples()
    key  = normalize_item_name(item_name)
    now  = datetime.now(timezone.utc).isoformat()
    for item in data["staples"]:
        if normalize_item_name(item["name"]) == key and item["active"]:
            item["last_ordered"] = now
            item["order_count"]  = item.get("order_count", 0) + 1
            break
    save_staples(data)


def parse_email_receipt(text: str) -> list:
    """
    Extract item names from a pasted Instacart/Aldi receipt.
    Returns a list of name strings (best-effort heuristic).
    """
    items   = []
    seen    = set()

    # Work line by line; stop at subtotal/total markers
    for line in text.splitlines():
        stripped = line.strip()
        lower    = stripped.lower()

        # Stop when we hit the financial summary section
        if any(tok in lower for tok in ["subtotal", "total", "delivery fee", "service fee", "tip"]):
            break

        # Skip short lines, prices-only lines, and blank lines
        if len(stripped) < 4:
            continue
        if re.fullmatch(r"[\$\d\.,\s]+", stripped):
            continue

        # Remove leading quantity (e.g. "2x", "2 x", "x2")
        cleaned = re.sub(r"^\d+\s*[xX]\s*", "", stripped)
        cleaned = re.sub(r"^[xX]\s*\d+\s*", "", cleaned)
        # Remove trailing price (e.g. "$3.99", "3.99")
        cleaned = re.sub(r"\s+\$?\d+\.\d{2}\s*$", "", cleaned).strip()
        # Remove weight notations (e.g. "/ lb", "/ oz")
        cleaned = re.sub(r"\s*/\s*(lb|oz|kg|g)\b.*", "", cleaned, flags=re.IGNORECASE).strip()

        if len(cleaned) < 3:
            continue

        key = normalize_item_name(cleaned)
        if key and key not in seen:
            seen.add(key)
            items.append(cleaned)

    return items


def send_follow_up_question() -> None:
    """
    Check for orders where follow_up_done=False and ordered_at >20h ago.
    Send a follow-up message and mark as done.
    """
    data    = load_history()
    cutoff  = datetime.now(timezone.utc) - timedelta(hours=20)
    changed = False

    for order in data["orders"]:
        if order.get("follow_up_done"):
            continue
        try:
            ordered_at = datetime.fromisoformat(order["ordered_at"])
            if ordered_at.tzinfo is None:
                ordered_at = ordered_at.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if ordered_at <= cutoff:
            order["follow_up_done"] = True
            changed = True
            send(
                "How did your Aldi order go? "
                "Anything missing from the list, or anything you'd rather skip next time? "
                "Just reply and I'll update your staples."
            )
            # Only send one follow-up per run to avoid flooding
            break

    if changed:
        save_history(data)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_staples_message(staples: list) -> str:
    """Format staples grouped by category for Telegram."""
    if not staples:
        return "Your staples list is empty. Tell me what you regularly buy and I'll add them."

    grouped: dict = {}
    for item in staples:
        cat = item.get("category", "other")
        grouped.setdefault(cat, []).append(item)

    lines = ["Your Aldi staples:\n"]
    for cat in _CATEGORY_ORDER:
        if cat not in grouped:
            continue
        lines.append(f"{cat.capitalize()}:")
        for item in grouped[cat]:
            qty  = item.get("quantity", 1)
            unit = item.get("unit", "")
            freq = item.get("frequency", "weekly")
            freq_tag = "" if freq == "weekly" else f" [{freq}]"
            qty_str  = f" ({qty} {unit})" if unit else (f" x{qty}" if qty != 1 else "")
            lines.append(f"  • {item['name']}{qty_str}{freq_tag}")
        lines.append("")

    # Any categories not in the order list
    for cat, items in grouped.items():
        if cat in _CATEGORY_ORDER:
            continue
        lines.append(f"{cat.capitalize()}:")
        for item in items:
            lines.append(f"  • {item['name']}")
        lines.append("")

    lines.append(f"Total: {len(staples)} item(s)")
    return "\n".join(lines)


def format_order_message(items: list, checkout_url: str | None, list_type: str) -> str:
    """Build the order confirmation message with cart link."""
    label = "Monthly restock" if list_type == "monthly" else "Weekly order"
    count = len(items)

    # Build a compact item list
    by_cat: dict = {}
    for item in items:
        cat = item.get("category", "other")
        by_cat.setdefault(cat, []).append(item["name"])

    lines = [f"{label} — {count} item(s):\n"]
    for cat in _CATEGORY_ORDER:
        if cat not in by_cat:
            continue
        names = ", ".join(by_cat[cat])
        lines.append(f"  {cat.capitalize()}: {names}")
    for cat, names_list in by_cat.items():
        if cat not in _CATEGORY_ORDER:
            lines.append(f"  {cat.capitalize()}: {', '.join(names_list)}")

    lines.append("")
    if checkout_url:
        lines.append(f"Checkout on Instacart (Aldi):\n{checkout_url}")
        lines.append("\nTap the link to review and place your order.")
    else:
        lines.append("(Instacart API unavailable — here's your list for manual shopping.)")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run() -> None:
    """
    Entry point called by the Pincer scheduler or 'run task: grocery'.

    Behaviour:
    1. Check for pending follow-up questions from previous orders.
    2. Auto-determine weekly or monthly list.
    3. Generate the item list.
    4. Attempt to create an Instacart checkout URL.
    5. Send the list + URL (or list only on API failure) via Telegram.
    6. Log the order and update last_ordered on each staple.
    """
    # Step 1 — follow-up questions
    send_follow_up_question()

    # Step 2 — determine list type
    list_type = determine_list_type()

    # Step 3 — generate list
    items = generate_monthly_list() if list_type == "monthly" else generate_weekly_list()

    if not items:
        send(
            "Your Aldi staples list is empty — nothing to order. "
            "Tell me what you buy regularly and I'll add them."
        )
        return

    # Step 4 — Instacart cart
    checkout_url = None
    if _ic_key_set():
        staples_data = load_staples()
        store_pref   = staples_data.get("store_preference", "aldi")
        # store_id lookup: user should set ALDI_INSTACART_STORE_ID in .env
        store_id = (
            getattr(config, "ALDI_INSTACART_STORE_ID", "")
            or os.getenv("ALDI_INSTACART_STORE_ID", "")
        )
        if store_id:
            checkout_url = create_checkout_url(items, store_id)
        else:
            print("[grocery] ALDI_INSTACART_STORE_ID not set — skipping cart creation.")
    else:
        print("[grocery] INSTACART_API_KEY not set — skipping cart creation.")

    # Step 5 — send message
    msg = format_order_message(items, checkout_url, list_type)
    send(msg)

    # Step 6 — log order and update staples
    if checkout_url:
        order_id = log_order(items, checkout_url, list_type)
        for item in items:
            update_staple_after_order(item["name"])


# ---------------------------------------------------------------------------
# CLI — for direct invocation and [RUN_FILE:] testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run()
