
from typing import Optional
from urllib.parse import quote

import requests

from ..config import REQUEST_TIMEOUT, USER_AGENT
from ..models import Article, SearchResult
from .base_searcher import BaseSearcher, get_with_retry

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
SEMANTIC_SCHOLAR_AUTHOR_URL = "https://api.semanticscholar.org/graph/v1/author/search"
SEMANTIC_SCHOLAR_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"

class SemanticScholarSearcher(BaseSearcher):

    def __init__(self):
        super().__init__()
        self.fields = "title,authors,year,abstract,externalIds,url,venue,citationCount,publicationTypes,openAccessPdf"

    def search(self, query: str, max_results: int = 10, page: int = 1) -> SearchResult:
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "offset": (page - 1) * max_results,
            "fields": self.fields,
        }

        try:
            resp = get_with_retry(
                SEMANTIC_SCHOLAR_SEARCH_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return SearchResult(
                query=query,
                error=f"Semantic Scholar search failed: {str(e)}",
                source="SemanticScholar",
                page=page,
                page_size=max_results,
            )

        return self._parse_response(data, query, max_results, page)

    def search_by_author(self, author: str, max_results: int = 10) -> SearchResult:
        params = {
            "query": author,
            "limit": 5,
            "fields": "name,paperCount,citationCount,hIndex",
        }

        try:
            resp = get_with_retry(
                SEMANTIC_SCHOLAR_AUTHOR_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return SearchResult(
                query=author,
                error=f"Semantic Scholar author search failed: {str(e)}",
                source="SemanticScholar",
            )

        authors = data.get("data", [])
        all_articles = []

        for author_entry in authors[:3]:
            author_id = author_entry.get("authorId", "")
            if not author_id:
                continue

            papers_url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers"
            try:
                papers_resp = get_with_retry(
                    papers_url,
                    params={"limit": max_results, "fields": self.fields},
                    headers={"User-Agent": USER_AGENT},
                    timeout=REQUEST_TIMEOUT,
                )
                papers_resp.raise_for_status()
                papers_data = papers_resp.json()
                papers = papers_data.get("data", [])
                for paper in papers:
                    article = self._parse_item(paper)
                    if article:
                        all_articles.append(article)
            except requests.RequestException:
                continue

        return SearchResult(
            query=author,
            total_results=len(all_articles),
            articles=all_articles[:max_results],
            source="SemanticScholar",
        )

    def _parse_response(self, data: dict, query: str, max_results: int, page: int) -> SearchResult:
        papers = data.get("data", [])
        total_results = data.get("total", len(papers))

        articles = []
        for paper in papers:
            try:
                article = self._parse_item(paper)
                if article:
                    articles.append(article)
            except Exception:
                continue

        return SearchResult(
            query=query,
            total_results=total_results,
            articles=articles,
            source="SemanticScholar",
            page=page,
            page_size=max_results,
        )

    def _parse_item(self, paper: dict) -> Optional[Article]:
        title = paper.get("title", "")

        authors = []
        for author_entry in paper.get("authors", []):
            name = author_entry.get("name", "")
            if name:
                authors.append(name)

        year = paper.get("year")

        abstract = paper.get("abstract", "") or ""

        ext_ids = paper.get("externalIds", {}) or {}
        doi = ext_ids.get("DOI", "")
        arxiv_id = ext_ids.get("ArXiv", "")
        pmid = ext_ids.get("PubMed", "")

        url = paper.get("url", "")
        if not url and doi:
            url = f"https://doi.org/{doi}"
        elif not url and arxiv_id:
            url = f"https://arxiv.org/abs/{arxiv_id}"

        venue = paper.get("venue", "") or ""
        journal = venue

        citation_count = paper.get("citationCount", 0) or 0

        pub_types = paper.get("publicationTypes", []) or []
        keywords = list(pub_types)

        if not title:
            return None

        source_id = arxiv_id or doi or paper.get("paperId", "")

        return Article(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            source="SemanticScholar",
            source_id=source_id,
            doi=doi,
            url=url,
            journal=journal,
            citation_count=citation_count,
            keywords=keywords,
        )
