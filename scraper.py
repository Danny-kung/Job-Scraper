import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from jobspy import scrape_jobs

import config

logger = logging.getLogger(__name__)


def fetch_jobs_for_title(job_title: str) -> pd.DataFrame:
    """Scrape all configured sites for a single job title."""
    try:
        logger.info(f"Scraping: '{job_title}' on {config.SITES}")
        df = scrape_jobs(
            site_name=config.SITES,
            search_term=job_title,
            location=config.LOCATION,
            results_wanted=config.RESULTS_PER_SITE,
            hours_old=config.HOURS_OLD,
            is_remote=config.REMOTE_ONLY,
            country_indeed=config.COUNTRY_INDEED,
            verbose=0,
        )
        logger.info(f"  Got {len(df)} results for '{job_title}'")
        return df
    except Exception as e:
        logger.error(f"  Failed scraping '{job_title}': {e}")
        return pd.DataFrame()


def fetch_all_jobs() -> pd.DataFrame:
    """
    Iterate through all configured job titles and combine results.
    Drops duplicate job_url entries that appear across multiple search terms.
    """
    all_frames = []
    for title in config.JOB_TITLES:
        df = fetch_jobs_for_title(title)
        if not df.empty:
            all_frames.append(df)

    if not all_frames:
        logger.warning("No results returned from any job title search.")
        return pd.DataFrame()

    combined = pd.concat(all_frames, ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["job_url"])
    logger.info(f"Combined: {before} results → {len(combined)} after dedup within batch")
    return combined


def filter_recent(df: pd.DataFrame) -> pd.DataFrame:
    """
    Secondary date filter as a safety net against stale postings.
    Keeps rows where date_posted is within the last 48 hours (wider than 24h
    to accommodate job boards like ZipRecruiter that round dates to day-level),
    OR where date_posted is null/NaT (unknown date — include by default).
    """
    if df.empty or "date_posted" not in df.columns:
        return df

    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    def is_recent(d):
        if pd.isna(d):
            return True  # unknown date: include rather than discard
        if isinstance(d, datetime):
            dt = d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        else:
            dt = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        return dt >= cutoff

    mask = df["date_posted"].apply(is_recent)
    filtered = df[mask]
    dropped = len(df) - len(filtered)
    if dropped > 0:
        logger.info(f"Date filter dropped {dropped} postings older than 48 hours.")
    return filtered


def filter_relevant(df: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only postings whose title contains at least one keyword from
    REQUIRED_TITLE_KEYWORDS. Drops unrelated roles that job boards return
    due to fuzzy search (e.g. bartender, paramedic, construction worker).
    """
    if df.empty or "title" not in df.columns:
        return df

    required = [kw.lower() for kw in config.REQUIRED_TITLE_KEYWORDS]

    def is_relevant(title):
        if pd.isna(title):
            return False
        t = str(title).lower()
        return any(kw in t for kw in required)

    filtered = df[df["title"].apply(is_relevant)]
    dropped = len(df) - len(filtered)
    if dropped > 0:
        logger.info(f"Relevance filter dropped {dropped} unrelated posting(s).")
    return filtered


def filter_seniority(df: pd.DataFrame) -> pd.DataFrame:
    """Drop postings whose title contains a senior/non-entry-level keyword."""
    if df.empty or "title" not in df.columns:
        return df

    exclude = [kw.lower() for kw in config.EXCLUDE_TITLE_KEYWORDS]

    def is_junior(title):
        if pd.isna(title):
            return True
        t = str(title).lower()
        return not any(kw in t for kw in exclude)

    filtered = df[df["title"].apply(is_junior)]
    dropped = len(df) - len(filtered)
    if dropped > 0:
        logger.info(f"Seniority filter dropped {dropped} non-entry-level posting(s).")
    return filtered


def deduplicate_against_sheet(df: pd.DataFrame, existing_urls: set) -> pd.DataFrame:
    """Remove any rows whose job_url already exists in the Google Sheet."""
    if df.empty:
        return df
    new_df = df[~df["job_url"].isin(existing_urls)]
    skipped = len(df) - len(new_df)
    if skipped > 0:
        logger.info(f"Deduplication: skipped {skipped} already-tracked job(s).")
    return new_df
