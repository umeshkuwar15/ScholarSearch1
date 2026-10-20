from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime

@dataclass
class Article:
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: str = ""
    source: str = ""
    source_id: str = ""
    doi: str = ""
    url: str = ""
    journal: str = ""
    citation_count: int = 0
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items()}

    @property
    def short_authors(self) -> str:
        if not self.authors:
            return "Unknown"
        if len(self.authors) <= 3:
            return ", ".join(self.authors)
        return f"{self.authors[0]}, {self.authors[1]}, ... ({len(self.authors)} authors)"

    @property
    def citation_str(self) -> str:
        authors_str = ", ".join(self.authors[:3])
        if len(self.authors) > 3:
            authors_str += " et al."
        year_str = f" ({self.year})" if self.year else ""
        title_str = self.title
        return f"{authors_str}{year_str}. {title_str}."

@dataclass
class SearchResult:
    query: str
    total_results: int = 0
    articles: List[Article] = field(default_factory=list)
    source: str = ""
    page: int = 1
    page_size: int = 10
    error: Optional[str] = None
