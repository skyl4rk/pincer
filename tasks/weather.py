# TASK: weather
# SCHEDULE: every day at 05:45
# ENABLED: false
# DESCRIPTION: Sends a 3-day weather forecast from NOAA to Telegram.
#              Requires WEATHER_LOCATION=lat,lon in .env (e.g. 40.7128,-74.0060)

import sys
import requests
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
import config
from notify import send


def f_to_c(f):
    return round((f - 32) * 5 / 9, 1)


def get_noaa_forecast(lat, lon):
    """Fetch 3-day forecast from NOAA API. Returns list of daily dicts or None."""
    headers = {"User-Agent": "Pincer Weather Report (pincer@local)"}

    try:
        # Step 1: resolve grid point for coordinates
        points_resp = requests.get(
            f"https://api.weather.gov/points/{lat},{lon}",
            headers=headers,
            timeout=10,
        )
        points_resp.raise_for_status()
        forecast_url = points_resp.json()["properties"]["forecast"]

        # Step 2: fetch the forecast
        forecast_resp = requests.get(forecast_url, headers=headers, timeout=10)
        forecast_resp.raise_for_status()
        periods = forecast_resp.json()["properties"]["periods"]

        # Pair daytime and nighttime periods into daily summaries.
        # NOAA alternates: daytime (isDaytime=true) then overnight per date.
        daily = {}
        for period in periods:
            date_str = period["startTime"][:10]
            if date_str not in daily:
                daily[date_str] = {}
            day = daily[date_str]

            if period["isDaytime"]:
                day["date_str"] = date_str
                day["high_f"] = period["temperature"]
                day["description"] = period["shortForecast"]
                day["wind_speed"] = period["windSpeed"]
                day["wind_dir"] = period["windDirection"]
            else:
                day.setdefault("date_str", date_str)
                day["low_f"] = period["temperature"]
                day.setdefault("description", period["shortForecast"])
                day.setdefault("wind_speed", period["windSpeed"])
                day.setdefault("wind_dir", period["windDirection"])

        # Only return days with enough data; take first 3 complete dates
        result = []
        for date_str in sorted(daily)[:3]:
            day = daily[date_str]
            if "date_str" not in day:
                continue
            result.append({
                "date_str": day["date_str"],
                "high_f":   day.get("high_f"),
                "low_f":    day.get("low_f"),
                "description": day.get("description", ""),
                "wind_speed":  day.get("wind_speed", ""),
                "wind_dir":    day.get("wind_dir", ""),
            })

        return result or None

    except requests.RequestException as e:
        print(f"[weather] NOAA API error: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"[weather] Parse error: {e}")
        return None


def format_report(forecasts):
    if not forecasts:
        return "Unable to retrieve NOAA weather forecast."

    day_labels = ["Today", "Tomorrow", "Day 3"]
    lines = ["3-Day Weather Forecast (NOAA)\n"]

    for i, f in enumerate(forecasts):
        date_obj = datetime.strptime(f["date_str"], "%Y-%m-%d")

        high = f"{f['high_f']}F / {f_to_c(f['high_f'])}C" if f["high_f"] is not None else "n/a"
        low  = f"{f['low_f']}F / {f_to_c(f['low_f'])}C"   if f["low_f"]  is not None else "n/a"

        lines.append(
            f"{day_labels[i]} - {date_obj.strftime('%A, %b %d')}\n"
            f"  High: {high}  Low: {low}\n"
            f"  Wind: {f['wind_dir']} {f['wind_speed']}\n"
            f"  {f['description']}\n"
        )

    return "\n".join(lines)


def run():
    location = config.WEATHER_LOCATION.strip()
    if not location:
        send("[weather] WEATHER_LOCATION not set in .env — skipping forecast.")
        return

    try:
        lat, lon = [part.strip() for part in location.split(",", 1)]
    except ValueError:
        send(f"[weather] WEATHER_LOCATION must be 'lat,lon' — got: {location!r}")
        return

    forecasts = get_noaa_forecast(lat, lon)
    send(format_report(forecasts))
