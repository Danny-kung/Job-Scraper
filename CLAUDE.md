# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the scraper

```bash
# Activate the virtualenv (always required)
source "/Users/kenkung/Job Scraper/venv/bin/activate"

# Run the daily scrape manually
python main.py

# One-time sheet setup (run once after configuring credentials.json)
python setup_sheet.py
```

## Scheduler (macOS launchd)

```bash
# Install / start the 9am daily agent
cp com.kenkung.jobscraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.kenkung.jobscraper.plist

# Trigger on demand without waiting for 9am
launchctl start com.kenkung.jobscraper

# Check last exit code (third column; 0 = success)
launchctl list | grep jobscraper

# View logs
cat logs/scraper.log
cat logs/scraper_error.log

# Unload (pause the schedule)
launchctl unload ~/Library/LaunchAgents/com.kenkung.jobscraper.plist
```

After editing the plist, unload then reload for changes to take effect.

## Architecture

`main.py` is the entry point and orchestrates the full pipeline in order:

1. **Fetch** — `scraper.fetch_all_jobs()` calls `python-jobspy` across all sites in `config.SITES`. `custom_scrapers.fetch_jobbank()` fetches Canada's Job Bank via its public Atom RSS feed independently.
2. **Merge** — both DataFrames are concatenated and deduped by `job_url`.
3. **Filter** — `scraper.filter_relevant()` (whitelist: title must contain "engineer"/"engineering"), then `scraper.filter_seniority()` (blacklist: drop senior/lead/manager titles), then `scraper.filter_recent()` (48h window).
4. **Sort** — `_prioritize_gta()` in `main.py` sorts Toronto/GTA postings to the top.
5. **Deduplicate against sheet** — `sheets.get_existing_urls()` reads the "Link to Job Posting" column into a set; `scraper.deduplicate_against_sheet()` removes already-tracked URLs.
6. **Append** — `sheets.append_jobs()` writes new rows (Company, Title, blank Date Applied, URL, blank Status, blank Notes).

## Key config (config.py)

All user-facing settings live in `config.py`:
- `JOB_TITLES` — search terms sent to each job board
- `REQUIRED_TITLE_KEYWORDS` — whitelist; at least one must match the fetched title
- `EXCLUDE_TITLE_KEYWORDS` — blacklist for senior roles
- `GTA_CITIES` — cities used for GTA prioritization sort
- `SITES` — jobspy-supported boards: `linkedin`, `indeed`, `zip_recruiter`, `google`
- `LOCATION`, `COUNTRY_INDEED` — both set to `"Canada"`

## Custom scrapers (custom_scrapers.py)

Job Bank uses a public Atom feed (`/jobsearch/feed/jobSearchRSSfeed`). Company name and location are parsed from the HTML `<summary>` field using `re`. The `fage=2` parameter filters to postings from the last 2 days. No extra dependencies — uses stdlib `xml.etree.ElementTree` and `requests` (already a jobspy dependency).

## Google Sheets auth

Uses a Google Service Account (`credentials.json`). The sheet must be shared with the service account's `client_email` as Editor. `setup_sheet.py` creates headers, freezes row 1, sets column widths, and adds the Status dropdown (`E2:E1000`). The sheet is the deduplication source of truth — job URLs already present are never re-added.

## Notes on unsupported boards

- **Workopolis** — acquired by Indeed in 2018; its listings are covered by `"indeed"` in `SITES`
- **CareerBeacon** — returns 403 on all requests, no public feed
- **ASME / SME** — block direct scraping; covered indirectly via `"google"` in `SITES`
