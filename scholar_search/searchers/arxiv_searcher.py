
import re
import xml.etree.ElementTree as ET
from typing import Optional, List

import requests

from ..config import ARXIV_BASE_URL, REQUEST_TIMEOUT, USER_AGENT
from ..models import Article, SearchResult
from .base_searcher import BaseSearcher, get_with_retry

class ArxivSearcher(BaseSearcher):

    def __init__(self):
        super().__init__()
        self.base_url = ARXIV_BASE_URL
        self.headers = {"User-Agent": USER_AGENT}

    def search(self, query: str, max_results: int = 10, page: int = 1) -> SearchResult:
        start = (page - 1) * max_results
        params = {
            "search_query": f"all:{query}",
            "start": start,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            resp = get_with_retry(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            return SearchResult(
                query=query,
                error=f"arXiv API request failed: {str(e)}",
                source="arXiv",
                page=page,
                page_size=max_results,
            )

        return self._parse_response(resp.text, query, max_results, page)

    def search_by_author(self, author: str, max_results: int = 10) -> SearchResult:
        params = {
            "search_query": f'au:"{author}"',
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            resp = get_with_retry(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            return SearchResult(
                query=author,
                error=f"arXiv author search failed: {str(e)}",
                source="arXiv",
            )

        return self._parse_response(resp.text, author, max_results)

    def _parse_response(
        self, xml_text: str, query: str, max_results: int, page: int = 1
    ) -> SearchResult:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return SearchResult(
                query=query,
                error=f"Failed to parse arXiv response: {str(e)}",
                source="arXiv",
            )

        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        articles = []
        total_results = 0

        total_el = root.find("atom:totalResults", ns)
        if total_el is not None:
            try:
                total_results = int(total_el.text)
            except (ValueError, TypeError):
                pass

        for entry in root.findall("atom:entry", ns):
            try:
                article = self._parse_entry(entry, ns)
                if article:
                    articles.append(article)
            except Exception:
                continue

        return SearchResult(
            query=query,
            total_results=total_results,
            articles=articles,
            source="arXiv",
            page=page,
            page_size=max_results,
        )

    def _parse_entry(self, entry, ns) -> Optional[Article]:
        title_el = entry.find("atom:title", ns)
        title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""

        authors = []
        for author_el in entry.findall("atom:author/atom:name", ns):
            if author_el.text:
                authors.append(author_el.text.strip())

        abstract_el = entry.find("atom:summary", ns)
        abstract = abstract_el.text.strip().replace("\n", " ") if abstract_el is not None else ""

        published_el = entry.find("atom:published", ns)
        year = None
        if published_el is not None and published_el.text:
            year_match = re.search(r"(\d{4})", published_el.text)
            if year_match:
                year = int(year_match.group(1))

        id_el = entry.find("atom:id", ns)
        url = id_el.text.strip() if id_el is not None else ""
        source_id = url.split("/")[-1] if url else ""

        doi = ""
        for link in entry.findall("atom:link", ns):
            if link.get("title") == "doi":
                doi = link.get("href", "").replace("https://doi.org/", "")
                break

        keywords = []
        for cat in entry.findall("atom:category", ns):
            term = cat.get("term", "")
            if term:
                keywords.append(term)

        if not title:
            return None

        return Article(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            source="arXiv",
            source_id=source_id,
            doi=doi,
            url=url,
            keywords=keywords,
        )
