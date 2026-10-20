
import time

import requests

from abc import ABC, abstractmethod
from typing import Optional
from ..models import SearchResult

RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.0
RATE_LIMIT_BACKOFF_SECONDS = 5.0

def _sleep_before_retry(response, attempt):
    retry_after = response.headers.get("Retry-After")
    if retry_after is not None:
        try:
            delay = float(retry_after)
            delay = max(0.0, min(delay, 30.0))
        except (TypeError, ValueError):
            delay = None
        if delay is not None:
            time.sleep(delay)
            return

    if response.status_code == 429:
        delay = RATE_LIMIT_BACKOFF_SECONDS * (2 ** attempt)
    else:
        delay = BACKOFF_BASE_SECONDS * (2 ** attempt)

    delay = min(delay, 30.0)
    time.sleep(delay)

def get_with_retry(url, params=None, headers=None, timeout=30, max_retries=None):
    if max_retries is None:
        max_retries = MAX_RETRIES

    response = None
    for attempt in range(max_retries + 1):
        response = requests.get(url, params=params, headers=headers, timeout=timeout)

        status = response.status_code
        is_retriable = isinstance(status, int) and status in RETRIABLE_STATUS_CODES
        if is_retriable and attempt < max_retries:
            _sleep_before_retry(response, attempt)
            continue
        break

    return response

class BaseSearcher(ABC):

    def __init__(self):
        self.name = self.__class__.__name__.replace("Searcher", "")

    @abstractmethod
    def search(self, query: str, max_results: int = 10, page: int = 1) -> SearchResult:
        pass

    @abstractmethod
    def search_by_author(self, author: str, max_results: int = 10) -> SearchResult:
        pass
