import logging
import sys
from pathlib import Path

# Ensure logs/ directory exists at runtime
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("main")

import pandas as pd

import custom_scrapers
import scraper
import sheets
import config


def _prioritize_gta(df: pd.DataFrame) -> pd.DataFrame:
    """Sort so that Toronto/GTA jobs appear first. Non-GTA jobs follow."""
    if df.empty or "location" not in df.columns:
        return df

    gta_lower = [c.lower() for c in config.GTA_CITIES]

    def is_gta(loc):
        if pd.isna(loc):
            return False
        return any(city in str(loc).lower() for city in gta_lower)

    df = df.copy()
    df["_gta"] = df["location"].apply(is_gta)
    df = df.sort_values("_gta", ascending=False).drop(columns=["_gta"])
    return df.reset_index(drop=True)


def run():
    logger.info("=== Job Scraper Starting ===")

    # Step 1: Fetch from jobspy sites (LinkedIn, Indeed, ZipRecruiter, Google)
    jobspy_df = scraper.fetch_all_jobs()

    # Step 2: Fetch from Canada's Job Bank RSS feed
    logger.info("Fetching from Job Bank...")
    jobbank_df = custom_scrapers.fetch_jobbank()

    # Combine both sources
    frames = [df for df in [jobspy_df, jobbank_df] if not df.empty]
    if not frames:
        logger.info("No jobs fetched from any source. Exiting.")
        return
    jobs_df = pd.concat(frames, ignore_index=True)
    jobs_df = jobs_df.drop_duplicates(subset=["job_url"])
    logger.info(f"Total unique jobs across all sources: {len(jobs_df)}")

    # Step 3: Drop anything that isn't an engineering role
    jobs_df = scraper.filter_relevant(jobs_df)
    if jobs_df.empty:
        logger.info("No engineering roles found after relevance filter. Exiting.")
        return

    # Step 4: Drop senior/non-entry-level postings
    jobs_df = scraper.filter_seniority(jobs_df)
    if jobs_df.empty:
        logger.info("All fetched jobs were filtered as senior roles. Exiting.")
        return

    # Step 5: Secondary recency filter (guards against stale date data from some boards)
    jobs_df = scraper.filter_recent(jobs_df)
    if jobs_df.empty:
        logger.info("All fetched jobs were filtered as too old. Exiting.")
        return

    # Step 6: Sort — Toronto/GTA jobs first
    jobs_df = _prioritize_gta(jobs_df)
    gta_count = sum(
        any(c.lower() in str(loc).lower() for c in config.GTA_CITIES)
        for loc in jobs_df.get("location", [])
        if not pd.isna(loc)
    )
    logger.info(f"GTA prioritization: {gta_count} GTA job(s) sorted to top.")

    # Step 7: Connect to Google Sheets and load existing URLs for deduplication
    try:
        ws = sheets.get_worksheet()
        existing_urls = sheets.get_existing_urls(ws)
        logger.info(f"Sheet has {len(existing_urls)} existing job URL(s).")
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        sys.exit(1)

    # Step 8: Deduplicate — skip anything already in the sheet
    new_jobs = scraper.deduplicate_against_sheet(jobs_df, existing_urls)
    if new_jobs.empty:
        logger.info("All fetched jobs are already in the sheet. Nothing to add.")
        return

    # Step 9: Append new jobs (GTA jobs land at the top of the new batch)
    count = sheets.append_jobs(ws, new_jobs)
    logger.info(f"=== Done. Added {count} new job(s) to '{ws.title}'. ===")


if __name__ == "__main__":
    run()
