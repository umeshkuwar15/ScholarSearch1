
import pytest
from scholar_search.models import Article, SearchResult

class TestArticle:

    def test_article_creation(self):
        article = Article(
            title="Test Paper",
            authors=["John Doe", "Jane Smith"],
            year=2024,
            abstract="This is a test abstract.",
            source="arXiv",
            doi="10.1234/test",
            url="https://arxiv.org/abs/2401.00001",
        )
        assert article.title == "Test Paper"
        assert len(article.authors) == 2
        assert article.year == 2024
        assert article.source == "arXiv"

    def test_article_to_dict(self):
        article = Article(
            title="Test",
            authors=["Alice"],
            year=2023,
            abstract="Abstract here",
            source="CrossRef",
            citation_count=5,
            keywords=["ML", "AI"],
        )
        data = article.to_dict()
        assert data["title"] == "Test"
        assert data["authors"] == ["Alice"]
        assert data["citation_count"] == 5
        assert data["keywords"] == ["ML", "AI"]

    def test_short_authors_three_or_less(self):
        article = Article(
            title="Title",
            authors=["Alice", "Bob", "Charlie"],
        )
        assert article.short_authors == "Alice, Bob, Charlie"

    def test_short_authors_more_than_three(self):
        article = Article(
            title="Title",
            authors=["Alice", "Bob", "Charlie", "Diana"],
        )
        assert "..." in article.short_authors
        assert "Alice" in article.short_authors
        assert "(4 authors)" in article.short_authors

    def test_short_authors_empty(self):
        article = Article(title="No Authors")
        assert article.short_authors == "Unknown"

    def test_citation_str(self):
        article = Article(
            title="Important Paper",
            authors=["Einstein"],
            year=2024,
        )
        assert "Einstein" in article.citation_str
        assert "2024" in article.citation_str
        assert "Important Paper" in article.citation_str

class TestSearchResult:

    def test_search_result_creation(self):
        result = SearchResult(
            query="machine learning",
            total_results=100,
            articles=[Article(title="Paper 1"), Article(title="Paper 2")],
            source="arXiv",
            page=1,
            page_size=10,
        )
        assert result.query == "machine learning"
        assert result.total_results == 100
        assert len(result.articles) == 2
        assert result.source == "arXiv"

    def test_search_result_error(self):
        result = SearchResult(
            query="test",
            error="API timeout",
            source="CrossRef",
        )
        assert result.error == "API timeout"
        assert result.total_results == 0
        assert len(result.articles) == 0

    def test_empty_articles_default(self):
        result = SearchResult(query="test")
        assert result.articles == []
