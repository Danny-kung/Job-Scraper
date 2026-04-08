# ── Search Configuration ─────────────────────────────────────────────────────

# Job titles to search for. Each entry becomes a separate scrape call.
JOB_TITLES = [
    "Entry Level Mechanical Engineer",
    "Junior Mechanical Engineer",
    "Entry Level Manufacturing Engineer",
    "Entry Level Process Engineer",
    "Entry Level Project Engineer",
    "New Grad Mechanical Engineer",
    "Associate Mechanical Engineer",
    "Junior Project Engineer",
    "Junior Process Engineer",
    "Junior Manufacturing Engineer",
    "New Grad Engineer",
    "Engineer in Training"
]

# At least one of these must appear in a fetched job title for the posting to
# be kept. This prevents job boards' fuzzy search from returning unrelated
# roles (bartender, paramedic, etc.) when searching "entry level engineer".
REQUIRED_TITLE_KEYWORDS = [
    "engineer",
    "engineering",
]

# Title keywords that indicate a senior role — matched case-insensitively
# against the fetched job title. Matching postings are filtered out.
EXCLUDE_TITLE_KEYWORDS = [
    "senior",
    "sr.",
    " sr ",
    "lead",
    "principal",
    "staff",
    "manager",
    "director",
    "head of",
    "vp ",
    "vice president",
    "ii",   # e.g. "Engineer II" — typically not entry level
    "iii",
    "iv",
]

# Geographic location for all searches
LOCATION = "Canada"

# Recency filter in hours. Slightly above 24 to handle timing drift.
HOURS_OLD = 25

# Max results to fetch per job title, per site
RESULTS_PER_SITE = 20

# Which job boards to scrape.
# Options: "linkedin", "indeed", "glassdoor", "zip_recruiter", "google"
# "google" is included to capture postings from specialized boards (ASME, SME,
# etc.) that block direct scraping but are indexed by Google Jobs.
# Note: Workopolis was acquired by Indeed in 2018 — its listings are already
# covered by the "indeed" site above.
# Note: CareerBeacon blocks automated requests and has no public RSS feed.
SITES = ["indeed", "linkedin", "zip_recruiter", "google"]

# Country for Indeed (required by python-jobspy)
COUNTRY_INDEED = "Canada"

# Set to True to filter for remote-only positions
# Note: enabling this disables the hours_old filter on Indeed
REMOTE_ONLY = False

# ── Toronto / GTA Prioritization ─────────────────────────────────────────────

# Jobs whose location contains any of these strings (case-insensitive) will be
# sorted to the top of the sheet when new rows are appended each day.
GTA_CITIES = [
    "toronto",
    "mississauga",
    "brampton",
    "scarborough",
    "north york",
    "etobicoke",
    "markham",
    "vaughan",
    "richmond hill",
    "oakville",
    "burlington",
    "ajax",
    "whitby",
    "oshawa",
    "pickering",
    "aurora",
    "newmarket",
    "hamilton",
]

# ── Google Sheets Configuration ──────────────────────────────────────────────

# The exact name of your Google Sheet
SPREADSHEET_NAME = "Job Applications"

# The worksheet (tab) name within the spreadsheet
WORKSHEET_NAME = "Applications"

# Path to your Google Service Account credentials JSON file
CREDENTIALS_FILE = "credentials.json"

# ── Sheet Column Order ────────────────────────────────────────────────────────
# Must match the header row created by setup_sheet.py
COLUMNS = [
    "Company Name",
    "Position Title",
    "Date Applied",
    "Link to Job Posting",
    "Status",
    "Notes",
]

STATUS_OPTIONS = ["Applied", "Rejected", "Interview", "Offer"]
