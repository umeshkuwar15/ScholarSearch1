
import csv
import json
import os
from typing import List, TextIO
from datetime import datetime

from .models import Article

class BaseExporter:

    def export(self, articles: List[Article], filepath: str) -> str:
        raise NotImplementedError

class JsonExporter(BaseExporter):

    def export(self, articles: List[Article], filepath: str) -> str:
        data = {
            "exported_at": datetime.now().isoformat(),
            "count": len(articles),
            "articles": [article.to_dict() for article in articles],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filepath

class CsvExporter(BaseExporter):

    def export(self, articles: List[Article], filepath: str) -> str:
        fieldnames = [
            "title", "authors", "year", "abstract", "source",
            "source_id", "doi", "url", "journal", "citation_count", "keywords",
        ]

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for article in articles:
                row = article.to_dict()
                row["authors"] = "; ".join(article.authors)
                row["keywords"] = "; ".join(article.keywords)
                writer.writerow(row)

        return filepath

class TextExporter(BaseExporter):

    def export(self, articles: List[Article], filepath: str) -> str:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"SCHOLAR SEARCH RESULTS\n")
            f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Articles: {len(articles)}\n")
            f.write("=" * 80 + "\n\n")

            for i, article in enumerate(articles, 1):
                f.write(f"[{i}] {article.title}\n")
                f.write(f"{'=' * 60}\n")
                f.write(f"Authors: {article.short_authors}\n")
                if article.year:
                    f.write(f"Year: {article.year}\n")
                if article.journal:
                    f.write(f"Journal: {article.journal}\n")
                if article.doi:
                    f.write(f"DOI: {article.doi}\n")
                if article.url:
                    f.write(f"URL: {article.url}\n")
                if article.citation_count:
                    f.write(f"Citations: {article.citation_count}\n")
                if article.keywords:
                    f.write(f"Keywords: {', '.join(article.keywords)}\n")
                if article.abstract:
                    abstract_short = article.abstract[:300]
                    if len(article.abstract) > 300:
                        abstract_short += "..."
                    f.write(f"\nAbstract: {abstract_short}\n")
                f.write(f"Source: {article.source}\n")
                f.write("-" * 60 + "\n\n")

        return filepath

def get_exporter(format: str = "json") -> BaseExporter:
    exporters = {
        "json": JsonExporter(),
        "csv": CsvExporter(),
        "text": TextExporter(),
    }
    exporter = exporters.get(format.lower())
    if not exporter:
        raise ValueError(f"Unsupported export format: '{format}'. Use 'json', 'csv', or 'text'.")
    return exporter
