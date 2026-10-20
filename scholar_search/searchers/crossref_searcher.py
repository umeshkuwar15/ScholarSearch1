
from typing import Optional
from urllib.parse import quote

import requests

from ..config import CROSSREF_BASE_URL, REQUEST_TIMEOUT, USER_AGENT
from ..models import Article, SearchResult
from .base_searcher import BaseSearcher, get_with_retry

class CrossrefSearcher(BaseSearcher):

    def __init__(self):
        super().__init__()
        self.base_url = CROSSREF_BASE_URL
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

    def search(self, query: str, max_results: int = 10, page: int = 1) -> SearchResult:
        params = {
            "query": query,
            "rows": min(max_results, 50),
            "offset": (page - 1) * max_results,
            "sort": "relevance",
            "order": "desc",
        }

        try:
            resp = get_with_retry(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return SearchResult(
                query=query,
                error=f"CrossRef API request failed: {str(e)}",
                source="CrossRef",
                page=page,
                page_size=max_results,
            )
        except ValueError as e:
            return SearchResult(
                query=query,
                error=f"Invalid JSON from CrossRef: {str(e)}",
                source="CrossRef",
            )

        return self._parse_response(data, query, max_results, page)

    def search_by_author(self, author: str, max_results: int = 10) -> SearchResult:
        params = {
            "query.author": author,
            "rows": min(max_results, 50),
            "sort": "published",
            "order": "desc",
        }

        try:
            resp = get_with_retry(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return SearchResult(
                query=author,
                error=f"CrossRef author search failed: {str(e)}",
                source="CrossRef",
            )

        return self._parse_response(data, author, max_results)

    def _parse_response(
        self, data: dict, query: str, max_results: int, page: int = 1
    ) -> SearchResult:
        message = data.get("message", {})
        items = message.get("items", [])
        total_results = message.get("total-results", 0)

        articles = []
        for item in items:
            try:
                article = self._parse_item(item)
                if article:
                    articles.append(article)
            except Exception:
                continue

        return SearchResult(
            query=query,
            total_results=total_results,
            articles=articles,
            source="CrossRef",
            page=page,
            page_size=max_results,
        )

    def _parse_item(self, item: dict) -> Optional[Article]:
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""

        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)

        published = item.get("published-print") or item.get("published-online") or item.get("published")
        year = None
        if published:
            date_parts = published.get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]

        abstract = item.get("abstract", "")
        if abstract:
            import re
            abstract = re.sub(r"<[^>]+>", "", abstract)

        doi = item.get("DOI", "")

        url = f"https://doi.org/{doi}" if doi else ""

        container = item.get("container-title", [])
        journal = container[0] if container else ""

        citation_count = item.get("is-referenced-by-count", 0)

        keywords = item.get("subject", [])

        if not title:
            return None

        return Article(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            source="CrossRef",
            source_id=doi,
            doi=doi,
            url=url,
            journal=journal,
            citation_count=citation_count,
            keywords=keywords,
        )
