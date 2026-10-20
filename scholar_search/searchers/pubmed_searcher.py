
import re
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import quote

import requests

from ..config import REQUEST_TIMEOUT, USER_AGENT
from ..models import Article, SearchResult
from .base_searcher import BaseSearcher, get_with_retry

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

class PubmedSearcher(BaseSearcher):

    def __init__(self, api_key: str = ""):
        super().__init__()
        self.api_key = api_key

    def search(self, query: str, max_results: int = 10, page: int = 1) -> SearchResult:
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retstart": (page - 1) * max_results,
            "retmode": "json",
            "sort": "relevance",
        }
        if self.api_key:
            params["api_key"] = self.api_key

        try:
            resp = get_with_retry(
                PUBMED_SEARCH_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            return SearchResult(
                query=query,
                error=f"PubMed search failed: {str(e)}",
                source="PubMed",
                page=page,
                page_size=max_results,
            )

        esearch = data.get("esearchresult", {})
        id_list = esearch.get("idlist", [])
        total_results = int(esearch.get("count", 0))

        if not id_list:
            return SearchResult(
                query=query,
                total_results=0,
                articles=[],
                source="PubMed",
                page=page,
                page_size=max_results,
            )

        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "retmode": "xml",
            "rettype": "abstract",
        }
        if self.api_key:
            fetch_params["api_key"] = self.api_key

        try:
            fetch_resp = get_with_retry(
                PUBMED_FETCH_URL,
                params=fetch_params,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            fetch_resp.raise_for_status()
        except requests.RequestException as e:
            return SearchResult(
                query=query,
                error=f"PubMed fetch failed: {str(e)}",
                source="PubMed",
                total_results=total_results,
                page=page,
                page_size=max_results,
            )

        articles = self._parse_articles(fetch_resp.text, id_list)

        return SearchResult(
            query=query,
            total_results=total_results,
            articles=articles,
            source="PubMed",
            page=page,
            page_size=max_results,
        )

    def search_by_author(self, author: str, max_results: int = 10) -> SearchResult:
        return self.search(f'{author}[Author]', max_results)

    def _parse_articles(self, xml_text: str, id_list: list) -> list:
        articles = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return articles

        for pubmed_article in root.findall(".//PubmedArticle"):
            try:
                article = self._parse_article(pubmed_article)
                if article:
                    articles.append(article)
            except Exception:
                continue

        return articles

    def _parse_article(self, pubmed_article) -> Optional[Article]:
        medline = pubmed_article.find(".//MedlineCitation")
        if medline is None:
            return None

        article_elem = medline.find(".//Article")
        if article_elem is None:
            return None

        title_el = article_elem.find("ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""

        authors = []
        author_list = article_elem.find(".//AuthorList")
        if author_list is not None:
            for author_el in author_list.findall("Author"):
                last = author_el.findtext("LastName", "")
                fore = author_el.findtext("ForeName", "")
                if last and fore:
                    authors.append(f"{fore} {last}")
                elif last:
                    authors.append(last)

        pub_date = article_elem.find(".//Journal/JournalIssue/PubDate")
        year = None
        if pub_date is not None:
            year_str = pub_date.findtext("Year", "")
            if year_str:
                try:
                    year = int(year_str)
                except ValueError:
                    pass

        abstract_parts = []
        abs_elem = article_elem.find("Abstract")
        if abs_elem is not None:
            for part in abs_elem.findall("AbstractText"):
                label = part.get("Label", "")
                text = "".join(part.itertext())
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
        abstract = " ".join(abstract_parts)

        pmid = medline.findtext("PMID", "")

        doi = ""
        for el in article_elem.findall(".//ELocationID"):
            if el.get("EIdType") == "doi":
                doi = el.text or ""
                break
        if not doi:
            doi = medline.findtext(".//ArticleId[@IdType='doi']", "")

        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

        journal = article_elem.findtext(".//Journal/Title", "")

        keywords = []
        kw_list = medline.find("KeywordList")
        if kw_list is not None:
            for kw in kw_list.findall("Keyword"):
                text = kw.text
                if text:
                    keywords.append(text)

        if not title:
            return None

        return Article(
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            source="PubMed",
            source_id=pmid,
            doi=doi,
            url=url,
            journal=journal,
            keywords=keywords,
        )
