"""
Custom scrapers for job boards not supported by python-jobspy.

Currently implements:
  - Canada's Job Bank (jobbank.gc.ca) via its public Atom RSS feed
"""
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

import pandas as pd
import requests

import config

logger = logging.getLogger(__name__)

_JOBBANK_BASE = "https://www.jobbank.gc.ca"
_JOBBANK_FEED = (
    _JOBBANK_BASE
    + "/jobsearch/feed/jobSearchRSSfeed"
    "?fage=2&sort=D&rows=25&term={term}"
)

# Atom namespace
_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_summary(html: str) -> tuple[str, str]:
    """
    Extract (employer, location) from a Job Bank summary HTML block.

    Expected format:
        <strong>Job number:</strong> 123<br />
        <strong>Location:</strong> Toronto (ON)  <br />
        <strong>Employer:</strong> Acme Corp<br />
        <strong>Salary:</strong> $30.00 hourly
    """
    employer = ""
    location = ""

    m = re.search(r"Employer:</strong>\s*([^<]+)", html)
    if m:
        employer = m.group(1).strip()

    m = re.search(r"Location:</strong>\s*([^<]+)", html)
    if m:
        location = m.group(1).strip()

    return employer, location


def _fetch_for_title(title: str) -> list[dict]:
    url = _JOBBANK_FEED.format(term=quote(title))
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Job Bank fetch failed for '{title}': {e}")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        logger.error(f"Job Bank XML parse error for '{title}': {e}")
        return []

    entries = []
    for entry in root.findall("atom:entry", _NS):
        job_title_el = entry.find("atom:title", _NS)
        link_el = entry.find("atom:link", _NS)
        updated_el = entry.find("atom:updated", _NS)
        summary_el = entry.find("atom:summary", _NS)

        job_title = job_title_el.text.strip() if job_title_el is not None else ""
        href = link_el.get("href", "") if link_el is not None else ""
        # href may be relative (jobposting/12345) or absolute
        job_url = href if href.startswith("http") else f"{_JOBBANK_BASE}/{href.lstrip('/')}"

        updated_str = updated_el.text.strip() if updated_el is not None else ""
        try:
            date_posted = datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
        except ValueError:
            date_posted = None

        summary_html = summary_el.text or "" if summary_el is not None else ""
        company, location = _parse_summary(summary_html)

        entries.append({
            "title": job_title,
            "company": company,
            "job_url": job_url,
            "location": location,
            "date_posted": date_posted,
            "site": "jobbank",
        })

    logger.info(f"  Job Bank: {len(entries)} results for '{title}'")
    return entries


def fetch_jobbank() -> pd.DataFrame:
    """
    Scrape Canada's Job Bank for all configured job titles.
    Returns a DataFrame with columns matching the jobspy output shape.
    """
    all_entries = []
    for title in config.JOB_TITLES:
        all_entries.extend(_fetch_for_title(title))

    if not all_entries:
        return pd.DataFrame()

    df = pd.DataFrame(all_entries)
    before = len(df)
    df = df.drop_duplicates(subset=["job_url"])
    logger.info(
        f"Job Bank combined: {before} results → {len(df)} after dedup within batch"
    )
    return df
