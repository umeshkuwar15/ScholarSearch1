
from typing import Optional
from urllib.parse import quote

import requests

from ..config import OPENALEX_BASE_URL, REQUEST_TIMEOUT, USER_AGENT
from ..models import Article, SearchResult
from .base_searcher import BaseSearcher, get_with_retry

class OpenAlexSearcher(BaseSearcher):

    def __init__(self):
        super().__init__()
        self.base_url = OPENALEX_BASE_URL
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

    def search(self, query: str, max_results: int = 10, page: int = 1) -> SearchResult:
        params = {
            "search": query,
            "per-page": min(max_results, 200),
            "page": page,
            "sort": "relevance_score:desc",
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
                error=f"OpenAlex API request failed: {str(e)}",
                source="OpenAlex",
                page=page,
                page_size=max_results,
            )
        except ValueError as e:
            return SearchResult(
                query=query,
                error=f"Invalid JSON from OpenAlex: {str(e)}",
                source="OpenAlex",
            )

        return self._parse_response(data, query, max_results, page)

    def search_by_author(self, author: str, max_results: int = 10) -> SearchResult:
        params = {
            "filter": f"author.search:{quote(author)}",
            "per-page": min(max_results, 200),
            "sort": "publication_year:desc",
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
                error=f"OpenAlex author search failed: {str(e)}",
                source="OpenAlex",
            )

        return self._parse_response(data, author, max_results)

    def _parse_response(
        self, data: dict, query: str, max_results: int, page: int = 1
    ) -> SearchResult:
        results = data.get("results", [])
        meta = data.get("meta", {})
        total_results = meta.get("count", 0)

        articles = []
        for item in results:
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
            source="OpenAlex",
            page=page,
            page_size=max_results,
        )

    def _parse_item(self, item: dict) -> Optional[Article]:
        title = item.get("title", "")

        authors = []
        for authorship in item.get("authorships", []):
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)

        year = item.get("publication_year")

        abstract_inverted = item.get("abstract_inverted_index", {})
        abstract = self._reconstruct_abstract(abstract_inverted)

        doi = item.get("doi", "")
        if doi:
            doi = doi.replace("https://doi.org/", "")

        url = item.get("doi") or item.get("open_access", {}).get("oa_url", "")

        primary_location = item.get("primary_location", {})
        source = primary_location.get("source", {}) if primary_location else {}
        journal = source.get("display_name", "") if source else ""

        citation_count = item.get("cited_by_count", 0)

        keywords = []
        for concept in item.get("concepts", []):
            name = concept.get("display_name", "")
            if name:
                keywords.append(name)

        if not title:
            return None

        return Article(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            source="OpenAlex",
            source_id=item.get("id", ""),
            doi=doi,
            url=url,
            journal=journal,
            citation_count=citation_count,
            keywords=keywords,
        )

    def _reconstruct_abstract(self, inverted_index: dict) -> str:
        if not inverted_index:
            return ""

        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))

        word_positions.sort()
        return " ".join(word for _, word in word_positions)
