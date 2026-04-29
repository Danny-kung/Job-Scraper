"""
Scraper for Canada's Job Bank via its public Atom RSS feed.
Uses exponential back-off retry logic for resilience against network hiccups.
"""
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote

import pandas as pd
import requests

import config
from .base import BaseScraper

logger = logging.getLogger(__name__)

_JOBBANK_BASE = "https://www.jobbank.gc.ca"
_JOBBANK_FEED = (
    _JOBBANK_BASE
    + "/jobsearch/feed/jobSearchRSSfeed"
    "?fage=2&sort=D&rows=25&term={term}"
)
_NS = {"atom": "http://www.w3.org/2005/Atom"}

_MAX_RETRIES = 3
_BACKOFF_BASE = 1  # seconds; delays will be 1s, 2s, 4s


def _get_with_retry(url: str, **kwargs) -> requests.Response:
    """
    GET the URL with up to _MAX_RETRIES attempts and exponential back-off.
    Raises requests.RequestException if all attempts fail.
    """
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(_MAX_RETRIES):
        try:
            response = requests.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                delay = _BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{_MAX_RETRIES}): {exc}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
    raise last_exc


def _parse_summary(html: str) -> tuple[str, str]:
    """Extract (employer, location) from a Job Bank summary HTML block."""
    employer = ""
    location = ""

    m = re.search(r"Employer:</strong>\s*([^<]+)", html)
    if m:
        employer = m.group(1).strip()

    m = re.search(r"Location:</strong>\s*([^<]+)", html)
    if m:
        location = m.group(1).strip()

    return employer, location


class JobBankScraper(BaseScraper):
    """
    Scrapes Canada's Job Bank for all configured job titles.
    Each title is fetched from the public Atom RSS feed with retry logic.
    """

    def _fetch_for_title(self, title: str) -> list[dict]:
        url = _JOBBANK_FEED.format(term=quote(title))
        try:
            resp = _get_with_retry(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        except requests.RequestException as e:
            logger.error(f"Job Bank fetch failed for '{title}' after {_MAX_RETRIES} attempts: {e}")
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

    def fetch(self) -> pd.DataFrame:
        all_entries = []
        for title in config.JOB_TITLES:
            all_entries.extend(self._fetch_for_title(title))

        if not all_entries:
            return pd.DataFrame()

        df = pd.DataFrame(all_entries)
        before = len(df)
        df = df.drop_duplicates(subset=["job_url"])
        logger.info(
            f"Job Bank combined: {before} results → {len(df)} after dedup within batch"
        )
        return df
