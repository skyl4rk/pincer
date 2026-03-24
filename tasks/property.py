# TASK: property
# SCHEDULE: every day at 05:45
# ENABLED: true
# DESCRIPTION: Daily property search — finds land for sale near the configured zip code
#              under the configured price with minimum acreage. Zip is read from .env
#              (PROPERTY_ZIP) so it is never committed to version control.
#              Scrapes Zillow using a session with cookie priming. Sends top 10 to Telegram.

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).parent.parent))
import config  # loads .env via dotenv
from notify import send

MAX_PRICE   = 20_000
MIN_ACRES   = 0.4
MAX_RESULTS = 10

# Zip codes are stored in .env — never hardcoded here.
# PROPERTY_ZIP      — primary zip code (required)
# PROPERTY_NEARBY_ZIPS — comma-separated additional zips to search (optional)
ZIP_CODE     = os.getenv("PROPERTY_ZIP", "").strip()
_nearby_raw  = os.getenv("PROPERTY_NEARBY_ZIPS", "")
NEARBY_ZIPS  = [z.strip() for z in _nearby_raw.split(",") if z.strip()]

def _zillow_searches():
    """Build Zillow search URLs from the configured zip codes."""
    if not ZIP_CODE:
        return []
    zips = [ZIP_CODE] + NEARBY_ZIPS
    return [f"https://www.zillow.com/{z}/land/" for z in zips]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session():
    """Create a requests session primed with Zillow cookies."""
    s = requests.Session()
    s.headers.update(_HEADERS)
    try:
        s.get("https://www.zillow.com/", timeout=10)
    except Exception:
        pass
    return s


def _parse_acres(value, unit):
    """Convert lot area to acres. Returns float or None."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    unit = (unit or "").lower()
    if "sqft" in unit or "sq ft" in unit or "square" in unit:
        return v / 43_560
    # assume acres if unit is "acres" or unrecognised
    return v


def _extract_listings(html):
    """Parse __NEXT_DATA__ JSON from a Zillow page and return raw listing dicts."""
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html, re.DOTALL
    )
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
        return (
            data["props"]["pageProps"]["searchPageState"]
                ["cat1"]["searchResults"]["listResults"]
        )
    except (KeyError, json.JSONDecodeError) as e:
        print(f"[property] JSON parse: {e}")
        return []


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _search_zillow(session):
    results = []
    seen    = set()

    for search_url in _zillow_searches():
        if len(results) >= MAX_RESULTS:
            break
        try:
            resp = session.get(search_url, timeout=15)
            if resp.status_code != 200:
                print(f"[property] {search_url} → HTTP {resp.status_code}")
                continue
        except Exception as e:
            print(f"[property] fetch {search_url}: {e}")
            continue

        listings = _extract_listings(resp.text)
        print(f"[property] {search_url.split('zillow.com')[1]} → {len(listings)} listings")

        for item in listings:
            zpid = item.get("zpid")
            if zpid in seen:
                continue

            price_num = item.get("unformattedPrice")
            if price_num is None or price_num > MAX_PRICE:
                continue

            home_info = item.get("hdpData", {}).get("homeInfo", {})
            acres_num = _parse_acres(
                home_info.get("lotAreaValue"),
                home_info.get("lotAreaUnit"),
            )
            if acres_num is None or acres_num < MIN_ACRES:
                continue

            detail_url = item.get("detailUrl", "")
            if not detail_url.startswith("http"):
                detail_url = f"https://www.zillow.com{detail_url}"

            address     = item.get("address", "Unknown address")
            lot_str     = item.get("lotAreaString") or f"{acres_num:.2f} acres"
            status      = item.get("statusText", "")
            desc_parts  = [s for s in [lot_str, status] if s]

            seen.add(zpid)
            results.append({
                "address":     address,
                "price":       f"${price_num:,}",
                "description": " | ".join(desc_parts),
                "url":         detail_url,
            })

            if len(results) >= MAX_RESULTS:
                break

    return results


# ---------------------------------------------------------------------------
# Format & send
# ---------------------------------------------------------------------------

def format_report(results):
    today = datetime.now().strftime("%B %d, %Y")
    lines = [
        f"Property Report — {today}",
        f"Under ${MAX_PRICE:,}  |  {MIN_ACRES}+ acres  |  zip {ZIP_CODE}\n",
    ]

    if not results:
        lines.append("No matching listings found today.")
        lines.append(
            f"\nSearch manually on Zillow:\n"
            f"https://www.zillow.com/{ZIP_CODE}/land/"
        )
        return "\n".join(lines)

    lines.append(f"Top {len(results)} listing(s):\n")
    for i, p in enumerate(results, 1):
        lines.append(f"{i}. {p['address']}")
        lines.append(f"   {p['price']}  |  {p['description']}")
        lines.append(f"   {p['url']}")
        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    if not ZIP_CODE:
        send("[property] PROPERTY_ZIP not set in .env — skipping search.")
        return
    session = _make_session()
    results = _search_zillow(session)
    send(format_report(results))


if __name__ == "__main__":
    run()
