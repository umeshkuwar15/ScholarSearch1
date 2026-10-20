
import json
import csv
import tempfile
import os
from pathlib import Path

import pytest
from scholar_search.models import Article
from scholar_search.exporters import JsonExporter, CsvExporter, TextExporter, get_exporter

@pytest.fixture
def sample_articles():
    return [
        Article(
            title="Deep Learning Advances",
            authors=["Yann LeCun", "Yoshua Bengio", "Geoffrey Hinton"],
            year=2015,
            abstract="A comprehensive review of deep learning techniques.",
            source="arXiv",
            source_id="1501.00001",
            doi="10.1000/deep-learning",
            url="https://arxiv.org/abs/1501.00001",
            journal="",
            citation_count=50000,
            keywords=["deep learning", "neural networks"],
        ),
        Article(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
            year=2017,
            abstract="Introduces the Transformer architecture.",
            source="arXiv",
            source_id="1706.03762",
            doi="10.48550/arXiv.1706.03762",
            url="https://arxiv.org/abs/1706.03762",
            journal="",
            citation_count=80000,
            keywords=["transformer", "attention", "NLP"],
        ),
    ]

class TestJsonExporter:

    def test_export_creates_file(self, sample_articles, tmp_path):
        filepath = str(tmp_path / "results.json")
        exporter = JsonExporter()
        result = exporter.export(sample_articles, filepath)

        assert result == filepath
        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["count"] == 2
        assert len(data["articles"]) == 2
        assert data["articles"][0]["title"] == "Deep Learning Advances"
        assert data["articles"][0]["authors"] == ["Yann LeCun", "Yoshua Bengio", "Geoffrey Hinton"]
        assert data["articles"][1]["doi"] == "10.48550/arXiv.1706.03762"

    def test_export_empty_list(self, tmp_path):
        filepath = str(tmp_path / "empty.json")
        exporter = JsonExporter()
        exporter.export([], filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["count"] == 0
        assert data["articles"] == []

class TestCsvExporter:

    def test_export_creates_file_with_header(self, sample_articles, tmp_path):
        filepath = str(tmp_path / "results.csv")
        exporter = CsvExporter()
        result = exporter.export(sample_articles, filepath)

        assert result == filepath
        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert set(reader.fieldnames) >= {
            "title", "authors", "year", "abstract", "source",
            "doi", "url", "journal", "citation_count", "keywords",
        }
        assert rows[0]["title"] == "Deep Learning Advances"
        assert "Yann LeCun" in rows[0]["authors"]
        assert rows[1]["year"] == "2017"

    def test_export_empty_list(self, tmp_path):
        filepath = str(tmp_path / "empty.csv")
        exporter = CsvExporter()
        exporter.export([], filepath)

        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert rows == []

class TestTextExporter:

    def test_export_creates_readable_text(self, sample_articles, tmp_path):
        filepath = str(tmp_path / "results.txt")
        exporter = TextExporter()
        result = exporter.export(sample_articles, filepath)

        assert result == filepath
        assert os.path.exists(filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "SCHOLAR SEARCH RESULTS" in content
        assert "Total Articles: 2" in content
        assert "Deep Learning Advances" in content
        assert "Attention Is All You Need" in content
        assert "Yann LeCun" in content

    def test_export_empty_list(self, tmp_path):
        filepath = str(tmp_path / "empty.txt")
        exporter = TextExporter()
        exporter.export([], filepath)

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Total Articles: 0" in content

class TestGetExporter:

    def test_get_json_exporter(self):
        exporter = get_exporter("json")
        assert isinstance(exporter, JsonExporter)

    def test_get_csv_exporter(self):
        exporter = get_exporter("csv")
        assert isinstance(exporter, CsvExporter)

    def test_get_text_exporter(self):
        exporter = get_exporter("text")
        assert isinstance(exporter, TextExporter)

    def test_get_exporter_case_insensitive(self):
        exporter = get_exporter("JSON")
        assert isinstance(exporter, JsonExporter)

    def test_get_exporter_invalid_format(self):
        with pytest.raises(ValueError):
            get_exporter("xml")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
