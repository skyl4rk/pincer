# TASK: craigslist
# SCHEDULE: every day at 04:45
# ENABLED: true
# DESCRIPTION: Daily Craigslist search for folding bicycles under $200 within 200 miles
#              of the configured zip code. Zip and regions stored in .env.
#              Sends top 10 results with individual listing URLs to Telegram.

import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).parent.parent))
import config  # loads .env via dotenv
from notify import send

# ---------------------------------------------------------------------------
# Config — all location data stored in .env, never hardcoded here
# ---------------------------------------------------------------------------

ZIP_CODE    = os.getenv("CRAIGSLIST_ZIP", "").strip()
_regions_raw = os.getenv("CRAIGSLIST_REGIONS", "").strip()
REGIONS     = [r.strip() for r in _regions_raw.split(",") if r.strip()]

MAX_PRICE   = 200
RADIUS_MI   = 30
MAX_RESULTS = 10
QUERY       = "folding bicycle"
KEYWORDS    = ["fold", "foldable", "collapsible"]

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

def _get_zip_coords(zip_code):
    """Return (lat, lon) for a zip code via zippopotam.us (free, no key)."""
    try:
        r = requests.get(f"https://api.zippopotam.us/us/{zip_code}", timeout=10)
        if r.status_code == 200:
            place = r.json()["places"][0]
            return float(place["latitude"]), float(place["longitude"])
    except Exception as e:
        print(f"[craigslist] zip lookup failed: {e}")
    return None, None


def _haversine(lat1, lon1, lat2, lon2):
    """Distance in miles between two lat/lon points."""
    R = 3958.8
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    a = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _make_session():
    s = requests.Session()
    s.headers.update(_HEADERS)
    return s


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def _fetch_region(session, region):
    """
    Fetch search results for one Craigslist region.
    Returns (items, urls) where items is JSON-LD list and urls is listing URL list.
    Both lists are aligned by index.
    """
    base = f"https://{region}.craigslist.org"
    try:
        session.get(f"{base}/", timeout=8)  # prime cookies
    except Exception:
        pass

    url = f"{base}/search/bia?query={QUERY.replace(' ', '+')}&sort=date"
    try:
        r = session.get(url, timeout=15)
    except Exception as e:
        print(f"[craigslist] {region}: {e}")
        return [], []

    if r.status_code != 200:
        print(f"[craigslist] {region}: HTTP {r.status_code}")
        return [], []

    # JSON-LD structured data (name, price, geo coords)
    m = re.search(
        r'id="ld_searchpage_results"[^>]*>(.*?)</script>',
        r.text, re.DOTALL
    )
    items = json.loads(m.group(1)).get("itemListElement", []) if m else []

    # Individual listing URLs — aligned with items by page order
    urls = re.findall(
        r'href="(https://\w+\.craigslist\.org/\w+/d/[^"]+\.html)"',
        r.text
    )

    print(f"[craigslist] {region}: {len(items)} items, {len(urls)} URLs")
    return items, urls


def _qualify(item_entry, url, target_lat, target_lon):
    """
    Check whether a listing meets all criteria.
    Returns a result dict or None.
    """
    item   = item_entry.get("item", {})
    name   = item.get("name", "")

    # Must contain a folding-related keyword
    name_lower = name.lower()
    if not any(kw in name_lower for kw in KEYWORDS):
        return None

    # Price must be under MAX_PRICE
    offers = item.get("offers", {})
    try:
        price = float(offers.get("price") or MAX_PRICE + 1)
    except (TypeError, ValueError):
        return None
    if price > MAX_PRICE:
        return None

    # Distance filter (skip if coords unavailable)
    geo      = offers.get("availableAtOrFrom", {}).get("geo", {})
    item_lat = geo.get("latitude")
    item_lon = geo.get("longitude")
    distance = None
    if item_lat and item_lon and target_lat and target_lon:
        distance = _haversine(target_lat, target_lon, item_lat, item_lon)
        if distance > RADIUS_MI:
            return None

    city = (
        offers.get("availableAtOrFrom", {})
              .get("address", {})
              .get("addressLocality", "")
    )

    return {
        "name":     name,
        "price":    f"${price:.0f}",
        "city":     city,
        "distance": f"{distance:.0f}mi" if distance is not None else "",
        "url":      url,
    }


def _gather(target_lat, target_lon):
    session  = _make_session()
    results  = []
    seen_urls = set()

    for region in REGIONS:
        if len(results) >= MAX_RESULTS:
            break
        items, urls = _fetch_region(session, region)
        for item_entry, url in zip(items, urls):
            if url in seen_urls:
                continue
            result = _qualify(item_entry, url, target_lat, target_lon)
            if result:
                seen_urls.add(url)
                results.append(result)

    return results[:MAX_RESULTS]


# ---------------------------------------------------------------------------
# Format & send
# ---------------------------------------------------------------------------

def format_report(results):
    today = datetime.now().strftime("%B %d, %Y")
    lines = [
        f"Craigslist — Folding Bicycles — {today}",
        f"Under ${MAX_PRICE}  |  within {RADIUS_MI}mi of {ZIP_CODE}\n",
    ]

    if not results:
        lines.append("No matching listings found today.")
        return "\n".join(lines)

    for i, r in enumerate(results, 1):
        detail_parts = [r["price"]]
        if r["city"]:
            detail_parts.append(r["city"])
        if r["distance"]:
            detail_parts.append(f"({r['distance']})")
        lines.append(f"{i}. {r['name']}")
        lines.append(f"   {'  |  '.join(detail_parts)}")
        lines.append(f"   {r['url']}")
        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run():
    if not ZIP_CODE:
        send("[craigslist] CRAIGSLIST_ZIP not set in .env — skipping.")
        return
    if not REGIONS:
        send("[craigslist] CRAIGSLIST_REGIONS not set in .env — skipping.")
        return

    target_lat, target_lon = _get_zip_coords(ZIP_CODE)
    results = _gather(target_lat, target_lon)
    send(format_report(results))


if __name__ == "__main__":
    run()
