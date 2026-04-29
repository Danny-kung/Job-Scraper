from abc import ABC, abstractmethod

import pandas as pd


class BaseScraper(ABC):
    """
    Base class for all job board scrapers.

    Each subclass must implement fetch(), which returns a DataFrame with at
    minimum the columns: title, company, job_url, location, date_posted, site.
    """

    @abstractmethod
    def fetch(self) -> pd.DataFrame:
        """Fetch jobs and return a deduplicated DataFrame."""
        ...
