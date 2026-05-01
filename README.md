# Job Scraper

An automated job scraping pipeline that searches multiple Canadian job boards daily, filters results to entry-level engineering roles, and logs new postings directly into a Google Sheet — no duplicates, no manual effort.

## Features

- Scrapes **LinkedIn, Indeed, ZipRecruiter, Google Jobs, and Canada's Job Bank** daily
- Filters to **entry-level / junior engineering** roles and drops senior/lead/manager titles
- **Deduplicates** against your Google Sheet — jobs already tracked are never re-added
- **Prioritizes GTA postings** to the top of each day's batch
- **Exponential back-off retry** on every HTTP request — resilient against network hiccups
- **Extensible scraper architecture** — adding a new job board is a single subclass
- Runs automatically at **9:00 AM daily** via macOS launchd (no cloud required)

## How it works

```
Fetch (jobspy + Job Bank RSS)
  → Merge & dedup by URL
  → Filter: engineering titles only
  → Filter: drop senior/lead/manager
  → Filter: posted within 48 hours
  → Sort: GTA cities first
  → Dedup against Google Sheet
  → Append new rows to sheet
```

## Project structure

```
Job Scraper/
├── main.py                      # Entry point — orchestrates the full pipeline
├── config.py                    # All user-facing settings (titles, sites, filters)
├── scraper.py                   # Filter + dedup helpers
├── sheets.py                    # Google Sheets read/write
├── setup_sheet.py               # One-time sheet setup script
├── custom_scrapers.py           # Legacy Job Bank scraper (superseded by scrapers/)
├── scrapers/
│   ├── base.py                  # BaseScraper abstract class
│   ├── jobspy_scraper.py        # LinkedIn, Indeed, ZipRecruiter, Google Jobs
│   └── jobbank_scraper.py       # Canada's Job Bank (Atom RSS + retry logic)
├── com.kenkung.jobscraper.plist # macOS launchd schedule (9am daily)
└── requirements.txt
```

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/Danny-kung/Job-Scraper.git
cd Job-Scraper
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Google Sheets credentials

1. Create a **Google Cloud project** and enable the **Google Sheets API** and **Google Drive API**
2. Create a **Service Account** and download the key as `credentials.json` into the project root
3. Run the one-time setup script:

```bash
python setup_sheet.py
```

4. Open the printed spreadsheet URL, click **Share**, and grant **Editor** access to the service account email shown in `credentials.json` under `client_email`

### 3. Customize search settings

Edit `config.py` to adjust:

| Setting | Description |
|---|---|
| `JOB_TITLES` | Search terms sent to each job board |
| `REQUIRED_TITLE_KEYWORDS` | Whitelist — fetched title must contain at least one |
| `EXCLUDE_TITLE_KEYWORDS` | Blacklist — drops senior/lead/manager titles |
| `SITES` | Job boards to scrape (`linkedin`, `indeed`, `zip_recruiter`, `google`) |
| `LOCATION` | Search location (default: `"Canada"`) |
| `HOURS_OLD` | Recency window in hours (default: `25`) |
| `RESULTS_PER_SITE` | Max results per job title per site (default: `20`) |
| `GTA_CITIES` | Cities sorted to the top of each daily batch |

### 4. Run manually

```bash
source venv/bin/activate
python main.py
```

## Automated daily schedule (macOS)

The included `com.kenkung.jobscraper.plist` runs the scraper at **9:00 AM every day** using macOS launchd — no cloud services or cron required.

```bash
# Install and activate
cp com.kenkung.jobscraper.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.kenkung.jobscraper.plist

# Trigger immediately (without waiting for 9am)
launchctl start com.kenkung.jobscraper

# Check last exit code (0 = success)
launchctl list | grep jobscraper

# View logs
cat logs/scraper.log
cat logs/scraper_error.log

# Unload (pause the schedule)
launchctl unload ~/Library/LaunchAgents/com.kenkung.jobscraper.plist
```

> If your Mac is asleep at 9am, launchd will fire the job automatically the moment it wakes up.

## Google Sheet columns

| Column | Filled by |
|---|---|
| Company Name | Scraper |
| Position Title | Scraper |
| Date Applied | You |
| Link to Job Posting | Scraper |
| Status | You (`Applied`, `Rejected`, `Interview`, `Offer`) |
| Notes | You |

## Adding a new job board

1. Create `scrapers/myboard_scraper.py` subclassing `BaseScraper`:

```python
from .base import BaseScraper

class MyBoardScraper(BaseScraper):
    def fetch(self) -> pd.DataFrame:
        # your scraping logic here
        ...
```

2. Add it to `scrapers/__init__.py` and instantiate it in `main.py` alongside the existing scrapers.

## Notes

- **Workopolis** — acquired by Indeed in 2018; its listings are covered by `"indeed"` in `SITES`
- **CareerBeacon** — blocks all automated requests, no public RSS feed
- **ASME / SME** — block direct scraping; captured indirectly via `"google"` in `SITES`
- `credentials.json` is gitignored — never commit it

## Requirements

- Python 3.10+
- macOS (for launchd scheduler)
- Google Cloud service account with Sheets + Drive APIs enabled
