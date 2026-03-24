# Tasks

Python scripts in this directory are discovered automatically by the scheduler.

## Naming tasks

Use short, single-word names for task files (e.g. `weather.py`, `costs.py`). Avoid underscores and multi-word names — task names are typed directly into Telegram commands on a phone, and shorter names are much easier to type.

## Metadata header

Each task file should start with a header block:

```python
# TASK: Human-readable name
# SCHEDULE: every day at 08:00
# ENABLED: false
# DESCRIPTION: What this task does
```

## Supported schedule values

- `every day at HH:MM` — daily at a fixed time
- `every hour` — every hour
- `every N minutes` — every N minutes
- `every N seconds` — for testing
- `on demand` — manual only, triggered with `run task: <name>`

## Enabling a task

Tasks default to `ENABLED: false`. Enable via the agent:
```
enable task: disk
```
Or edit the file header and restart.

## Writing a new task

Ask Pincer to write a task for you:
```
Write a task that checks the CPU temperature every 30 minutes
```

Pincer will generate the task code, show a preview, and ask for confirmation before saving.

---

## Task: property

Daily property search that finds land for sale near a configured zip code and sends the results to Telegram.

**Schedule:** Every day at 05:45
**Source:** Zillow (scrapes live listings)

### Setup

Set your zip codes in `.env` (never committed to version control):

```
PROPERTY_ZIP=40330
PROPERTY_NEARBY_ZIPS=40336,40337,40040
```

`PROPERTY_ZIP` is required. `PROPERTY_NEARBY_ZIPS` is optional — add any surrounding zip codes you want included in the search.

### What it reports

Up to 10 listings matching all of:
- Price under the configured maximum
- Lot size at or above the configured minimum acreage
- Located near the configured zip code

Each result includes the address, price, lot size, and a direct link to the individual Zillow listing page.

### Changing the search parameters

Just ask Pincer in Telegram:

```
change property max price to $30,000
set property minimum acres to 1
show 5 property results instead of 10
```

Pincer will update the task and offer to run it immediately to test.

The parameters and their defaults:

| Parameter | Variable | Default | Description |
|-----------|----------|---------|-------------|
| Zip code | `PROPERTY_ZIP` in `.env` | — | Primary zip code (required) |
| Nearby zips | `PROPERTY_NEARBY_ZIPS` in `.env` | — | Extra zip codes to search (comma-separated, optional) |
| Max price | `MAX_PRICE` | $20,000 | Maximum listing price |
| Min acreage | `MIN_ACRES` | 0.4 | Minimum lot size in acres |
| Max results | `MAX_RESULTS` | 10 | Number of listings to show |

### Running manually

```
run task: property
```
