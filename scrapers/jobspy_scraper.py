import logging

import pandas as pd
from jobspy import scrape_jobs

import config
from .base import BaseScraper

logger = logging.getLogger(__name__)


class JobSpyScraper(BaseScraper):
    """
    Scrapes LinkedIn, Indeed, ZipRecruiter, and Google Jobs via python-jobspy.
    Iterates over all configured job titles and deduplicates by job_url.
    """

    def _fetch_for_title(self, job_title: str) -> pd.DataFrame:
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

    def fetch(self) -> pd.DataFrame:
        all_frames = []
        for title in config.JOB_TITLES:
            df = self._fetch_for_title(title)
            if not df.empty:
                all_frames.append(df)

        if not all_frames:
            logger.warning("No results returned from any job title search.")
            return pd.DataFrame()

        combined = pd.concat(all_frames, ignore_index=True)
        before = len(combined)
        combined = combined.drop_duplicates(subset=["job_url"])
        logger.info(
            f"JobSpy combined: {before} results → {len(combined)} after dedup within batch"
        )
        return combined
