
from unittest.mock import patch, MagicMock

import pytest
import requests

from scholar_search.models import SearchResult
from scholar_search.searchers import (
    ArxivSearcher,
    CrossrefSearcher,
    OpenAlexSearcher,
)
from scholar_search.searchers.base_searcher import get_with_retry, RETRIABLE_STATUS_CODES

class TestGetWithRetry:

    def test_success_first_try(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = get_with_retry("http://example.com", max_retries=3)
            assert result == mock_response
            assert mock_get.call_count == 1

    def test_429_then_success(self):
        responses = [MagicMock(status_code=429), MagicMock(status_code=200)]
        with patch("requests.get", side_effect=responses) as mock_get:
            with patch("time.sleep"):
                result = get_with_retry("http://example.com", max_retries=3)
            assert result.status_code == 200
            assert mock_get.call_count == 2

    def test_5xx_then_success(self):
        responses = [MagicMock(status_code=503), MagicMock(status_code=200)]
        with patch("requests.get", side_effect=responses) as mock_get:
            with patch("time.sleep"):
                result = get_with_retry("http://example.com", max_retries=3)
            assert result.status_code == 200
            assert mock_get.call_count == 2

    def test_exhausts_retries(self):
        responses = [MagicMock(status_code=429) for _ in range(5)]
        with patch("requests.get", side_effect=responses) as mock_get:
            with patch("time.sleep"):
                result = get_with_retry("http://example.com", max_retries=3)
            assert result.status_code == 429

    def test_non_retriable_status_no_retry(self):
        mock_response = MagicMock(status_code=404)
        with patch("requests.get", return_value=mock_response) as mock_get:
            result = get_with_retry("http://example.com", max_retries=3)
            assert result.status_code == 404
            assert mock_get.call_count == 1

    def test_retriable_status_codes(self):
        assert 429 in RETRIABLE_STATUS_CODES
        assert 500 in RETRIABLE_STATUS_CODES
        assert 502 in RETRIABLE_STATUS_CODES
        assert 503 in RETRIABLE_STATUS_CODES
        assert 504 in RETRIABLE_STATUS_CODES

    def test_retry_after_header_honored(self):
        responses = [MagicMock(status_code=429), MagicMock(status_code=200)]
        responses[0].headers = {"Retry-After": "2"}
        with patch("requests.get", side_effect=responses) as mock_get:
            with patch("time.sleep") as mock_sleep:
                result = get_with_retry("http://example.com", max_retries=3)
            assert result.status_code == 200
            assert mock_get.call_count == 2
            assert mock_sleep.call_args[0][0] == 2.0

    def test_retry_after_missing_uses_rate_limit_backoff(self):
        responses = [MagicMock(status_code=429), MagicMock(status_code=200)]
        responses[0].headers = {}
        with patch("requests.get", side_effect=responses) as mock_get:
            with patch("time.sleep") as mock_sleep:
                result = get_with_retry("http://example.com", max_retries=3)
            assert result.status_code == 200
            assert mock_get.call_count == 2
            assert mock_sleep.call_args[0][0] == 5.0

class TestArxivSearcher:

    @pytest.fixture
    def searcher(self):
        return ArxivSearcher()

    def test_search_handles_network_error(self, searcher):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Connection error")
            result = searcher.search("machine learning", max_results=5)
            assert isinstance(result, SearchResult)
            assert result.error is not None
            assert result.articles == []

    def test_search_handles_http_error(self, searcher):
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = requests.RequestException("HTTP 429")
            mock_get.return_value = mock_response
            result = searcher.search("test", max_results=5)
            assert result.error is not None

    def test_search_by_author_formats_query(self, searcher):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("No network")
            result = searcher.search_by_author("Einstein", max_results=5)
            assert isinstance(result, SearchResult)
            assert result.error is not None

class TestCrossrefSearcher:

    @pytest.fixture
    def searcher(self):
        return CrossrefSearcher()

    def test_search_handles_network_error(self, searcher):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Timeout")
            result = searcher.search("machine learning", max_results=5)
            assert isinstance(result, SearchResult)
            assert result.error is not None
            assert result.articles == []

    def test_search_handles_invalid_json(self, searcher):
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_get.return_value = mock_response
            result = searcher.search("test", max_results=5)
            assert result.error is not None

    def test_parse_item_with_valid_data(self, searcher):
        item = {
            "title": ["Test Paper"],
            "author": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ],
            "published-print": {"date-parts": [[2024]]},
            "abstract": "This is a test abstract.",
            "DOI": "10.1234/test",
            "container-title": ["Test Journal"],
            "is-referenced-by-count": 10,
            "subject": ["Computer Science", "AI"],
        }
        article = searcher._parse_item(item)
        assert article is not None
        assert article.title == "Test Paper"
        assert len(article.authors) == 2
        assert article.year == 2024
        assert article.doi == "10.1234/test"
        assert article.citation_count == 10

    def test_parse_item_empty_title(self, searcher):
        item = {"title": []}
        article = searcher._parse_item(item)
        assert article is None

class TestOpenAlexSearcher:

    @pytest.fixture
    def searcher(self):
        return OpenAlexSearcher()

    def test_search_handles_network_error(self, searcher):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")
            result = searcher.search("machine learning", max_results=5)
            assert isinstance(result, SearchResult)
            assert result.error is not None

    def test_reconstruct_abstract(self, searcher):
        inverted = {
            "the": [0, 4],
            "test": [1],
            "abstract": [2],
            "is": [3],
            "here": [5],
        }
        abstract = searcher._reconstruct_abstract(inverted)
        assert abstract == "the test abstract is the here"

    def test_reconstruct_abstract_empty(self, searcher):
        abstract = searcher._reconstruct_abstract({})
        assert abstract == ""

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
