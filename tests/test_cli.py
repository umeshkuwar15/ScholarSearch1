
from unittest.mock import MagicMock

from scholar_search.cli import create_parser, search_source
from scholar_search.models import SearchResult

class TestCLIParser:

    def test_parser_creation(self):
        parser = create_parser()
        assert parser.prog == "scholarsearch"

    def test_parse_query(self):
        parser = create_parser()
        args = parser.parse_args(["machine learning"])
        assert args.query == "machine learning"
        assert args.source == "all"
        assert args.num_results == 10
        assert args.output is None

    def test_parse_author(self):
        parser = create_parser()
        args = parser.parse_args(["-a", "Einstein"])
        assert args.author == "Einstein"

    def test_parse_source_arxiv(self):
        parser = create_parser()
        args = parser.parse_args(["test", "-s", "arxiv"])
        assert args.source == "arxiv"

    def test_parse_source_openalex(self):
        parser = create_parser()
        args = parser.parse_args(["test", "-s", "openalex"])
        assert args.source == "openalex"

    def test_parse_num_results(self):
        parser = create_parser()
        args = parser.parse_args(["test", "-n", "25"])
        assert args.num_results == 25

    def test_parse_output(self):
        parser = create_parser()
        args = parser.parse_args(["test", "-o", "results.json"])
        assert args.output == "results.json"

    def test_parse_export_format(self):
        parser = create_parser()
        args = parser.parse_args(["test", "--export", "csv"])
        assert args.export == "csv"

    def test_parse_page(self):
        parser = create_parser()
        args = parser.parse_args(["test", "-p", "3"])
        assert args.page == 3

class TestSearchSource:

    def test_search_source_with_query(self):
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = "result_obj"
        result = search_source(mock_searcher, query="test", max_results=10)
        mock_searcher.search.assert_called_once_with("test", 10, 1)
        assert result == "result_obj"

    def test_search_source_with_author(self):
        mock_searcher = MagicMock()
        mock_searcher.search_by_author.return_value = "result_obj"
        result = search_source(mock_searcher, author="Doe", max_results=5)
        mock_searcher.search_by_author.assert_called_once_with("Doe", 5)
        assert result == "result_obj"

    def test_search_source_query_preferred_over_author(self):
        mock_searcher = MagicMock()
        mock_searcher.search.return_value = SearchResult(query="ml", source="test")
        result = search_source(mock_searcher, query="ml", author="Doe")
        mock_searcher.search.assert_called_once_with("ml", 10, 1)
        mock_searcher.search_by_author.assert_not_called()
        assert result.query == "ml"
