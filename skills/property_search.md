# Property Search Settings

The daily property report is in `tasks/property.py`. The user can ask you to change any of these parameters at the top of the file:

| Parameter | Variable | Default | Description |
|-----------|----------|---------|-------------|
| Max price | `MAX_PRICE` | 20_000 | Maximum listing price in dollars |
| Min acreage | `MIN_ACRES` | 0.4 | Minimum lot size in acres |
| Max results | `MAX_RESULTS` | 10 | Number of listings to show |

## Changing a parameter

When the user says things like:
- "change property max price to $30,000"
- "set property minimum acres to 1"
- "show 5 property results instead of 10"

Read the file, update the relevant variable, and use [MODIFY_FILE:] to save it. Then offer to run the task immediately to test:

[RUN_FILE: tasks/property.py]

## Search area

The search covers ~30 miles around zip code 49090 (South Haven, MI) by checking these Zillow URLs (the `_ZILLOW_SEARCHES` list in the file). To add or remove areas, edit that list.
